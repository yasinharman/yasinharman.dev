from .db import pool


async def log_blocked(session_id: str, user_message: str, reason: str, latency_ms: int) -> None:
    async with pool().acquire() as conn:
        await conn.execute(
            """
            INSERT INTO chat_logs (session_id, status, reason, user_message, ai_response, latency_ms)
            VALUES ($1, 'blocked', $2, $3, NULL, $4)
            """,
            session_id, reason, user_message, latency_ms,
        )


async def log_allowed(
    session_id: str,
    user_message: str,
    ai_response: str,
    latency_ms: int,
    reason: str | None = None,
) -> None:
    async with pool().acquire() as conn:
        await conn.execute(
            """
            INSERT INTO chat_logs (session_id, status, reason, user_message, ai_response, latency_ms)
            VALUES ($1, 'allowed', $2, $3, $4, $5)
            """,
            session_id, reason, user_message, ai_response, latency_ms,
        )
