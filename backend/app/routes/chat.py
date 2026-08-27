"""/chat ve /chat/stream.

İkisi TEK bir üretici fonksiyondan besleniyor (`_akis`). Ayrı iki implementasyon
yazmak, guard/router/log sırasını iki yerde tutmak demekti; bu sıra bugüne kadar
üç ayrı canlı bug'ın kaynağı oldu (uydurma iletişim bilgisi, selamlamanın
reddedilmesi, hatanın hiç loglanmaması) ve tek kopya kalması önemli.

Streaming NEDEN gerekli: ölçüldü (2026-08-27, canlı) — kariyer sorusunda cevap
7.6-12.4 saniye sürüyor ve bunun %60-70'i LLM üretimi. Ama token akışı tek başına
yetmiyor: router ve ilk retrieval bitmeden ÜRETİM başlamıyor, yani ilk token 3-7
saniyede geliyor. Asıl kazanç AŞAMA olaylarında — ziyaretçi 8 saniye boş ekrana
bakmak yerine ilk yarım saniyede "aranıyor", ~3 saniyede "8 bölüm bulundu"
görüyor, sonra metin akıyor.
"""
import json
import time
from collections.abc import AsyncIterator

import structlog
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse

from ..agent import agent_executor, initial_context
from ..config import get_settings
from ..guards import (
    StreamingOutputGuard,
    blocked_user_message,
    error_user_message,
    input_guard,
)
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


def _rate_limit(req: ChatRequest, request: Request, t0: float):
    """Rate limit — en ucuz kontrol, en basta; bir flood input_guard'i bile
    mesgul etmeden geri cevrilsin. Akista da BURADA, stream baslamadan once
    calisiyor: govde akmaya basladiktan sonra 429 donulemez."""
    rate = get_limiter().check(client_ip(request), req.session_id)
    if rate.allowed:
        return None
    log.warning("rate_limited", session_id=req.session_id, reason=rate.reason,
                retry_after=rate.retry_after)
    return rate


async def _akis(req: ChatRequest, t0: float) -> AsyncIterator[dict]:
    """Tam /chat sirasini kosar ve olay olarak yayinlar.

    Olaylar: {"tip": "asama"|"token"|"bitti"}. "bitti" her zaman SON olay ve tam
    cevabi tasir — akisi izlemeyen istemci (POST /chat) yalnizca onu okur,
    izleyen istemci de guard cevabi degistirdiyse ekranini onunla duzeltir.
    """
    settings = get_settings()

    # ADIM 4: Input guard — mesaji agent'a/DB'ye gecirmeden once tara.
    in_verdict = await input_guard(req.message)
    if not in_verdict.allowed:
        latency = _ms(t0)
        await log_blocked(req.session_id, req.message,
                          in_verdict.reason or in_verdict.category, latency)
        yield {"tip": "bitti", "cevap": blocked_user_message(req.lang), "engellendi": True}
        return

    history = await get_history(req.session_id, limit=settings.HISTORY_LIMIT)

    # ADIM 5.5: Selamlama/tesekkur — LLM'e hic gitmeden hazir cevap.
    # Sabit bir kelime kumesi icin model cagirmak hem para hem gecikme, ustelik
    # guvenilir de degildi: temiz bir oturumda "merhaba" yazan ziyaretci
    # "sadece Yasin hakkindaki sorulari cevaplamak icin egitildim" aliyordu.
    if (nazik := courtesy_reply(req.message, req.lang)) is not None:
        await append_message(req.session_id, "user", req.message)
        await append_message(req.session_id, "assistant", nazik)
        latency = _ms(t0)
        await log_allowed(req.session_id, req.message, nazik, latency, reason="courtesy",
                          route={"category": "courtesy", "resolved_query": req.message,
                                 "kb_query": ""})
        log.info("chat", session_id=req.session_id, lang=req.lang, latency_ms=latency,
                 sanitize="courtesy", kb_calls=0)
        yield {"tip": "bitti", "cevap": nazik, "engellendi": False}
        return

    # ADIM 5.7: Router — kapsam karari ve baglam cozumlemesi. Uc acik deger:
    # category / resolved_query / kb_query. Loglanabiliyor, olculebiliyor.
    yield {"tip": "asama", "asama": "yonlendiriliyor"}
    t_router = time.monotonic()
    route = await classify(req.message, history)
    router_ms = _ms(t_router)
    route_log = route.model_dump()

    # career DISINDA retrieval de ana LLM cagrisi da HIC yapilmaz.
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
        yield {"tip": "bitti", "cevap": metin, "engellendi": False}
        return

    trace: list[dict] = []
    retrieval_trace.set(trace)
    guard = StreamingOutputGuard(req.lang)
    t_agent = time.monotonic()

    # ADIM 6b: Agent patlarsa (OpenAI 429/500, Cohere timeout, Supabase kopmasi)
    # istek 500 ile bitip chat_logs'a HICBIR satir yazilmiyordu — yani yalnizca
    # basarili istekleri logluyorduk, prod hata orani gorunmezdi.
    try:
        yield {"tip": "asama", "asama": "araniyor", "sorgu": route.kb_query}
        # Ilk retrieval KOD tarafinda: agent'in tool'u cagiracagina guvenmiyoruz
        # (bkz. agent.initial_context — uydurma iletisim bilgisi vakasi).
        context = await initial_context(route.kb_query)
        yield {"tip": "asama", "asama": "bulundu",
               "adet": sum(k.get("kept", 0) for k in trace)}

        # ADIM 6: Girdi ham mesaj degil router'in cozdugu TAM soru.
        async for olay in agent_executor(req.lang).astream_events(
            {"input": route.resolved_query, "history": history, "context": context},
            version="v2",
        ):
            if olay["event"] != "on_chat_model_stream":
                continue
            if metin := guard.push(olay["data"]["chunk"].content):
                yield {"tip": "token", "metin": metin}
            if guard.reason:
                break
    except Exception as exc:
        latency = _ms(t0)
        await log_error(req.session_id, req.message, exc, latency,
                        retrieval=trace or None, route=route_log,
                        timings=_timings(latency, router_ms, trace, _ms(t_agent)))
        log.exception("chat_failed", session_id=req.session_id, lang=req.lang,
                      latency_ms=latency, kb_calls=len(trace))
        # append_message bilerek cagrilmiyor: yarim kalan tur gecmise yazilirsa
        # bir sonraki soruda model cevapsiz bir kullanici mesaji gorur.
        yield {"tip": "bitti", "cevap": error_user_message(req.lang),
               "engellendi": False, "hata": True}
        return

    agent_ms = _ms(t_agent)
    # ADIM 7: Output guard — sizinti / >3000 char / bos.
    kalan, final_answer, sanitize_reason = guard.finish()
    if kalan:
        yield {"tip": "token", "metin": kalan}

    await append_message(req.session_id, "user", req.message)
    await append_message(req.session_id, "assistant", final_answer)

    latency = _ms(t0)
    timings = _timings(latency, router_ms, trace, agent_ms)
    await log_allowed(req.session_id, req.message, final_answer, latency,
                      reason=sanitize_reason, retrieval=trace or None,
                      route=route_log, timings=timings)
    log.info("chat", session_id=req.session_id, lang=req.lang,
             category="career", sanitize=sanitize_reason, **timings)
    yield {"tip": "bitti", "cevap": final_answer, "engellendi": False}


@router.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest, request: Request) -> ChatResponse:
    """Akissiz yol. Ayni uretici sonuna kadar tuketilir, yalnizca son olay okunur."""
    t0 = time.monotonic()
    if (rate := _rate_limit(req, request, t0)) is not None:
        if rate.should_log:
            await log_blocked(req.session_id, req.message, rate.reason, _ms(t0))
        raise HTTPException(status_code=429, detail="too many requests",
                            headers={"Retry-After": str(rate.retry_after)})

    son: dict = {}
    async for olay in _akis(req, t0):
        if olay["tip"] == "bitti":
            son = olay
    return ChatResponse(response=son.get("cevap", ""), blocked=son.get("engellendi", False))


@router.post("/chat/stream")
async def chat_stream(req: ChatRequest, request: Request) -> StreamingResponse:
    t0 = time.monotonic()
    # 429 stream BASLAMADAN once donulmeli: govde akmaya basladiktan sonra
    # HTTP durum kodu degistirilemez.
    if (rate := _rate_limit(req, request, t0)) is not None:
        if rate.should_log:
            await log_blocked(req.session_id, req.message, rate.reason, _ms(t0))
        raise HTTPException(status_code=429, detail="too many requests",
                            headers={"Retry-After": str(rate.retry_after)})

    async def sse() -> AsyncIterator[str]:
        async for olay in _akis(req, t0):
            yield f"data: {json.dumps(olay, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        sse(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            # nginx (frontend imaji) proxy cevaplarini varsayilan olarak
            # tamponluyor; tamponlanan bir SSE akisi streaming olmaktan cikip
            # tek parca cevaba doner ve bu isin tamami bosa gider.
            "X-Accel-Buffering": "no",
        },
    )
