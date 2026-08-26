"""chat_logs yazımı — allowed / blocked / error.

Loglama hiçbir koşulda isteği patlatmaz. İki ayrı gerileme yolu var, ikisi de
migration'ların canlıya ELLE uygulanmasından kaynaklanıyor: main'e push otomatik
deploy tetiklediği için kod, migration'ından önce canlıda olabilir.

  - UndefinedColumnError → 003_chat_logs_retrieval.sql yok: retrieval kolonsuz yaz.
  - CheckViolationError  → 004_chat_logs_error_status.sql yok: status='error' CHECK
    kısıtına takılıyor; satırı kaybetmektense 'blocked' olarak, sebebi reason'da
    saklayarak yaz.
"""
import json

import asyncpg
import structlog

from .db import persistence_enabled, pool

log = structlog.get_logger()

_INSERT_WITH_RETRIEVAL = """
    INSERT INTO chat_logs
      (session_id, status, reason, user_message, ai_response, latency_ms, retrieval)
    VALUES ($1, $2, $3, $4, $5, $6, $7::jsonb)
"""

_INSERT_PLAIN = """
    INSERT INTO chat_logs (session_id, status, reason, user_message, ai_response, latency_ms)
    VALUES ($1, $2, $3, $4, $5, $6)
"""

_REASON_MAX_LEN = 300


async def _insert(conn, status, session_id, reason, user_message, ai_response,
                  latency_ms, retrieval) -> None:
    payload = json.dumps(retrieval) if retrieval is not None else None
    try:
        await conn.execute(_INSERT_WITH_RETRIEVAL, session_id, status, reason,
                           user_message, ai_response, latency_ms, payload)
    except asyncpg.exceptions.UndefinedColumnError:
        await conn.execute(_INSERT_PLAIN, session_id, status, reason,
                           user_message, ai_response, latency_ms)


async def _write(status: str, session_id: str, reason: str | None, user_message: str,
                 ai_response: str | None, latency_ms: int,
                 retrieval: list[dict] | None = None) -> None:
    if not persistence_enabled():
        return
    try:
        async with pool().acquire() as conn:
            try:
                await _insert(conn, status, session_id, reason, user_message,
                              ai_response, latency_ms, retrieval)
            except asyncpg.exceptions.CheckViolationError:
                if status != "error":
                    raise
                await _insert(conn, "blocked", session_id, f"error:{reason}",
                              user_message, ai_response, latency_ms, retrieval)
    except Exception:
        # Log yazamamak cevabı iptal etmek için yeterli bir sebep değil: kullanıcı
        # elindeki cevabı almalı. Sessiz kalmıyoruz, structlog'a düşüyor.
        log.exception("chat_log_write_failed", session_id=session_id, status=status)


async def log_blocked(session_id: str, user_message: str, reason: str, latency_ms: int) -> None:
    await _write("blocked", session_id, reason, user_message, None, latency_ms)


async def log_allowed(
    session_id: str,
    user_message: str,
    ai_response: str,
    latency_ms: int,
    reason: str | None = None,
    retrieval: list[dict] | None = None,
) -> None:
    await _write("allowed", session_id, reason, user_message, ai_response, latency_ms, retrieval)


async def log_error(
    session_id: str,
    user_message: str,
    exc: BaseException,
    latency_ms: int,
    retrieval: list[dict] | None = None,
) -> None:
    """Agent/retrieval patladığında satır yazar — aksi halde prod hata oranı görünmez.

    retrieval trace'i de yazılır: patlamadan ÖNCE neyi getirdiğimiz, hatayı sonradan
    okurken en değerli bilgi.
    """
    reason = f"{type(exc).__name__}: {exc}"[:_REASON_MAX_LEN]
    await _write("error", session_id, reason, user_message, None, latency_ms, retrieval)
