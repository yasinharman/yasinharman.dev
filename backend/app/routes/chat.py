import time
import structlog
from fastapi import APIRouter
from ..schemas import ChatRequest, ChatResponse
from ..config import get_settings
from ..memory import get_history, append_message
from ..guards import input_guard, output_guard, BLOCKED_USER_MESSAGE
from ..agent import agent_executor
from ..logging_db import log_blocked, log_allowed
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
        return ChatResponse(response=BLOCKED_USER_MESSAGE, blocked=True)

    # ADIM 6: History ile birlikte agent'ı çağır — agent system prompt + history + input ile LLM'i çalıştırır, gerektikçe portfolio_kb tool'unu kullanarak (max 4 iterasyon) final cevabı üretir.
    history = await get_history(req.session_id, limit=settings.HISTORY_LIMIT)
    trace: list[dict] = []
    retrieval_trace.set(trace)
    result = await agent_executor().ainvoke({"input": req.message, "history": history})
    raw_answer = result.get("output") or ""

    # ADIM 7: Output guard — agent cevabını üç kurala karşı tara (system prompt sızıntısı / >3000 char / boş); gerekirse yerine sabit metin koy. reason audit log için.
    final_answer, sanitize_reason = output_guard(raw_answer)

    await append_message(req.session_id, "user", req.message)
    await append_message(req.session_id, "assistant", final_answer)

    latency = int((time.monotonic() - t0) * 1000)
    await log_allowed(
        req.session_id, req.message, final_answer, latency,
        reason=sanitize_reason, retrieval=trace or None,
    )

    log.info("chat", session_id=req.session_id, latency_ms=latency,
             sanitize=sanitize_reason, kb_calls=len(trace))
    return ChatResponse(response=final_answer, blocked=False)
