import time
import structlog
from fastapi import APIRouter
from ..schemas import ChatRequest, ChatResponse
from ..config import get_settings
from ..memory import get_history, append_message
from ..guards import input_guard, output_guard, BLOCKED_USER_MESSAGE, BLOCKED_OUTPUT_REPLACEMENT
from ..agent import agent_executor
from ..logging_db import log_blocked, log_allowed

log = structlog.get_logger()
router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest) -> ChatResponse:
    settings = get_settings()
    t0 = time.monotonic()

    in_verdict = await input_guard(req.message)
    if not in_verdict.allowed:
        latency = int((time.monotonic() - t0) * 1000)
        await log_blocked(req.session_id, req.message, in_verdict.reason or in_verdict.category, latency)
        return ChatResponse(response=BLOCKED_USER_MESSAGE, blocked=True)

    history = await get_history(req.session_id, limit=settings.HISTORY_LIMIT)
    result = await agent_executor().ainvoke({"input": req.message, "history": history})
    answer = (result.get("output") or "").strip() or "Üzgünüm, şu anda yanıt üretemedim."

    out_verdict = await output_guard(answer)
    final_answer = answer if out_verdict.allowed else BLOCKED_OUTPUT_REPLACEMENT

    await append_message(req.session_id, "user", req.message)
    await append_message(req.session_id, "assistant", final_answer)

    latency = int((time.monotonic() - t0) * 1000)
    await log_allowed(
        req.session_id,
        req.message,
        final_answer,
        latency,
        reason=None if out_verdict.allowed else out_verdict.reason or out_verdict.category,
    )

    log.info("chat", session_id=req.session_id, latency_ms=latency, blocked_out=not out_verdict.allowed)
    return ChatResponse(response=final_answer, blocked=not out_verdict.allowed)
