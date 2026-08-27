import time

import structlog
from fastapi import APIRouter, HTTPException, Request

from ..agent import agent_executor, initial_context
from ..config import get_settings
from ..guards import blocked_user_message, error_user_message, input_guard, output_guard
from ..logging_db import log_allowed, log_blocked, log_error
from ..memory import append_message, get_history
from ..ratelimit import client_ip, get_limiter
from ..retriever import retrieval_trace
from ..router import classify, courtesy_reply, scope_reply
from ..schemas import ChatRequest, ChatResponse

log = structlog.get_logger()
router = APIRouter()


def _ms(t0: float) -> int:
    return int((time.monotonic() - t0) * 1000)


def _timings(toplam: int, router_ms: int | None = None,
             trace: list[dict] | None = None, agent_ms: int | None = None) -> dict:
    """Asama bazinda sure. chat_logs tek bir latency_ms tutuyordu; yavasligin
    nereden geldigi DB'den okunamiyordu.

    retrieval_ms trace'teki cagrilarin TOPLAMI: agent tool'u birden fazla kez
    cagirabiliyor, tek bir baslangic/bitis olcumu yanlis sonuc verirdi.
    llm_ms de cikarma ile bulunuyor cunku LangChain'in ainvoke'u icinde LLM
    cagrilari ile tool cagrilari ic ice geciyor; olculebilen sey ikisinin toplami.
    """
    t: dict = {"toplam_ms": toplam}
    if router_ms is not None:
        t["router_ms"] = router_ms
    if agent_ms is not None:
        retrieval_ms = sum(k.get("duration_ms", 0) for k in (trace or []))
        t["retrieval_ms"] = retrieval_ms
        t["llm_ms"] = max(agent_ms - retrieval_ms, 0)
        t["kb_calls"] = len(trace or [])
    return t


@router.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest, request: Request) -> ChatResponse:
    settings = get_settings()
    t0 = time.monotonic()

    # ADIM 3.5: Rate limit — en ucuz kontrol, en basta. Guard'lardan da once calisir
    # ki bir flood, input_guard'i bile mesgul etmeden geri cevrilsin.
    rate = get_limiter().check(client_ip(request), req.session_id)
    if not rate.allowed:
        latency = _ms(t0)
        log.warning("rate_limited", session_id=req.session_id, reason=rate.reason,
                    retry_after=rate.retry_after)
        if rate.should_log:
            await log_blocked(req.session_id, req.message, rate.reason, latency)
        raise HTTPException(
            status_code=429,
            detail="too many requests",
            headers={"Retry-After": str(rate.retry_after)},
        )

    # ADIM 4: Input guard — mesajı agent'a/DB'ye geçirmeden önce kötü niyetli/yasaklı içerik için tara; bloklanırsa ayrı log'a yaz ve sabit cevap dön.
    in_verdict = await input_guard(req.message)
    if not in_verdict.allowed:
        latency = _ms(t0)
        await log_blocked(req.session_id, req.message, in_verdict.reason or in_verdict.category, latency)
        return ChatResponse(response=blocked_user_message(req.lang), blocked=True)

    history = await get_history(req.session_id, limit=settings.HISTORY_LIMIT)

    # ADIM 5.5: Selamlama/teşekkür — LLM'e hiç gitmeden hazır cevap.
    # Sabit bir kelime kümesi için model çağırmak hem para hem gecikme, üstelik
    # güvenilir de değildi: temiz bir oturumda "merhaba" yazan ziyaretçi
    # "sadece Yasin hakkındaki soruları cevaplamak için eğitildim" alıyordu.
    # Mesaj geçmişe yine yazılır ki sonraki soru bağlamı kaybetmesin.
    if (nazik := courtesy_reply(req.message, req.lang)) is not None:
        await append_message(req.session_id, "user", req.message)
        await append_message(req.session_id, "assistant", nazik)
        latency = _ms(t0)
        await log_allowed(req.session_id, req.message, nazik, latency, reason="courtesy",
                          route={"category": "courtesy", "resolved_query": req.message,
                                 "kb_query": ""})
        log.info("chat", session_id=req.session_id, lang=req.lang, latency_ms=latency,
                 sanitize="courtesy", kb_calls=0)
        return ChatResponse(response=nazik, blocked=False)

    # ADIM 5.7: Router — kapsam kararı ve bağlam çözümlemesi. Eskiden ikisi de
    # 250 satırlık SYSTEM_PROMPT'un içinde örtük veriliyordu; artık üç açık değer:
    # category / resolved_query / kb_query. Loglanabiliyor, ölçülebiliyor.
    t_router = time.monotonic()
    route = await classify(req.message, history)
    router_ms = _ms(t_router)
    route_log = route.model_dump()

    # career DIŞINDA retrieval de ana LLM çağrısı da HİÇ yapılmaz. Eskiden reddedilen
    # her soru, 250 satırlık prompt + tool tanımı yükleyen tam bir agent turu harcıyordu.
    if route.category != "career":
        metin = scope_reply(route.category, req.lang)
        await append_message(req.session_id, "user", req.message)
        await append_message(req.session_id, "assistant", metin)
        latency = _ms(t0)
        await log_allowed(req.session_id, req.message, metin, latency,
                          reason=f"scope:{route.category}", route=route_log,
                          timings=_timings(latency, router_ms))
        log.info("chat", session_id=req.session_id, lang=req.lang, latency_ms=latency,
                 category=route.category, kb_calls=0)
        return ChatResponse(response=metin, blocked=False)

    # ADIM 6: Agent'ı çağır. Girdi ham mesaj değil router'ın çözdüğü TAM soru:
    # "peki ya eğitimi" gibi eksik takip soruları buraya tamamlanmış olarak gelir.
    trace: list[dict] = []
    retrieval_trace.set(trace)
    # ADIM 6b: Agent patlarsa (OpenAI 429/500, Cohere timeout, Supabase kopması) istek
    # 500 ile bitip chat_logs'a HİÇBİR satır yazılmıyordu — yani yalnızca başarılı
    # istekleri logluyorduk, prod hata oranı tamamen görünmezdi. Artık hata satır
    # olarak düşüyor ve kullanıcı ham stack trace yerine nazik bir metin görüyor.
    t_agent = time.monotonic()
    try:
        # Ilk retrieval KOD tarafinda: agent'in tool'u cagiracagina guvenmiyoruz
        # (bkz. agent.initial_context — uydurma iletisim bilgisi vakasi).
        context = await initial_context(route.kb_query)
        result = await agent_executor(req.lang).ainvoke(
            {"input": route.resolved_query, "history": history, "context": context})
    except Exception as exc:
        latency = _ms(t0)
        await log_error(req.session_id, req.message, exc, latency,
                        retrieval=trace or None, route=route_log,
                        timings=_timings(latency, router_ms, trace, _ms(t_agent)))
        log.exception("chat_failed", session_id=req.session_id, lang=req.lang,
                      latency_ms=latency, kb_calls=len(trace))
        # append_message bilerek çağrılmıyor: yarım kalan tur geçmişe yazılırsa bir
        # sonraki soruda model cevapsız bir kullanıcı mesajı görür.
        return ChatResponse(response=error_user_message(req.lang), blocked=False)

    agent_ms = _ms(t_agent)
    raw_answer = result.get("output") or ""

    # ADIM 7: Output guard — agent cevabını üç kurala karşı tara (system prompt sızıntısı / >3000 char / boş); gerekirse yerine sabit metin koy. reason audit log için.
    final_answer, sanitize_reason = output_guard(raw_answer, req.lang)

    await append_message(req.session_id, "user", req.message)
    await append_message(req.session_id, "assistant", final_answer)

    latency = _ms(t0)
    timings = _timings(latency, router_ms, trace, agent_ms)
    await log_allowed(
        req.session_id, req.message, final_answer, latency,
        reason=sanitize_reason, retrieval=trace or None, route=route_log,
        timings=timings,
    )

    log.info("chat", session_id=req.session_id, lang=req.lang,
             category="career", sanitize=sanitize_reason, **timings)
    return ChatResponse(response=final_answer, blocked=False)
