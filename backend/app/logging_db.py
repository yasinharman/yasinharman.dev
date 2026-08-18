import json

import asyncpg

from .db import persistence_enabled, pool


async def log_blocked(session_id: str, user_message: str, reason: str, latency_ms: int) -> None:
    if not persistence_enabled():
        return
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
    retrieval: list[dict] | None = None,
) -> None:
    if not persistence_enabled():
        return
    async with pool().acquire() as conn:
        try:
            await conn.execute(
                """
                INSERT INTO chat_logs
                  (session_id, status, reason, user_message, ai_response, latency_ms, retrieval)
                VALUES ($1, 'allowed', $2, $3, $4, $5, $6::jsonb)
                """,
                session_id, reason, user_message, ai_response, latency_ms,
                json.dumps(retrieval) if retrieval is not None else None,
            )
        except asyncpg.exceptions.UndefinedColumnError:
            # 003_chat_logs_retrieval.sql henüz uygulanmamışsa loglama kırılmasın.
            await conn.execute(
                """
                INSERT INTO chat_logs (session_id, status, reason, user_message, ai_response, latency_ms)
                VALUES ($1, 'allowed', $2, $3, $4, $5)
                """,
                session_id, reason, user_message, ai_response, latency_ms,
            )
