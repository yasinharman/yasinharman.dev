import time
import structlog
from fastapi import APIRouter
from ..schemas import ChatRequest, ChatResponse
from ..config import get_settings
from ..memory import get_history, append_message
from ..guards import input_guard, output_guard, blocked_user_message, error_user_message
from ..agent import agent_executor
from ..logging_db import log_blocked, log_allowed, log_error
from ..retriever import retrieval_trace

log = structlog.get_logger()
router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest) -> ChatResponse:
    settings = get_settings()
    t0 = time.monotonic()

    # ADIM 4: Input guard — mesajı agent'a/DB'ye geçirmeden önce kötü niyetli/yasaklı içerik için tara; bloklanırsa ayrı log'a yaz ve sabit cevap dön.
    in_verdict = await input_guard(req.message)
    if not in_verdict.allowed:
        latency = int((time.monotonic() - t0) * 1000)
        await log_blocked(req.session_id, req.message, in_verdict.reason or in_verdict.category, latency)
        return ChatResponse(response=blocked_user_message(req.lang), blocked=True)

    # ADIM 6: History ile birlikte agent'ı çağır — agent system prompt + history + input ile LLM'i çalıştırır, gerektikçe portfolio_kb tool'unu kullanarak (max 4 iterasyon) final cevabı üretir.
    history = await get_history(req.session_id, limit=settings.HISTORY_LIMIT)
    trace: list[dict] = []
    retrieval_trace.set(trace)
    # ADIM 6b: Agent patlarsa (OpenAI 429/500, Cohere timeout, Supabase kopması) istek
    # 500 ile bitip chat_logs'a HİÇBİR satır yazılmıyordu — yani yalnızca başarılı
    # istekleri logluyorduk, prod hata oranı tamamen görünmezdi. Artık hata satır
    # olarak düşüyor ve kullanıcı ham stack trace yerine nazik bir metin görüyor.
    try:
        result = await agent_executor(req.lang).ainvoke({"input": req.message, "history": history})
    except Exception as exc:
        latency = int((time.monotonic() - t0) * 1000)
        await log_error(req.session_id, req.message, exc, latency, retrieval=trace or None)
        log.exception("chat_failed", session_id=req.session_id, lang=req.lang,
                      latency_ms=latency, kb_calls=len(trace))
        # append_message bilerek çağrılmıyor: yarım kalan tur geçmişe yazılırsa bir
        # sonraki soruda model cevapsız bir kullanıcı mesajı görür.
        return ChatResponse(response=error_user_message(req.lang), blocked=False)

    raw_answer = result.get("output") or ""

    # ADIM 7: Output guard — agent cevabını üç kurala karşı tara (system prompt sızıntısı / >3000 char / boş); gerekirse yerine sabit metin koy. reason audit log için.
    final_answer, sanitize_reason = output_guard(raw_answer, req.lang)

    await append_message(req.session_id, "user", req.message)
    await append_message(req.session_id, "assistant", final_answer)

    latency = int((time.monotonic() - t0) * 1000)
    await log_allowed(
        req.session_id, req.message, final_answer, latency,
        reason=sanitize_reason, retrieval=trace or None,
    )

    log.info("chat", session_id=req.session_id, lang=req.lang, latency_ms=latency,
             sanitize=sanitize_reason, kb_calls=len(trace))
    return ChatResponse(response=final_answer, blocked=False)
