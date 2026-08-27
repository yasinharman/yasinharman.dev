"""chat_logs yazımı — allowed / blocked / error.

Loglama hiçbir koşulda isteği patlatmaz: log yazamamak, kullanıcıya elindeki
cevabı vermemek için yeterli bir sebep değil.

Burada eskiden üç kademeli bir gerileme merdiveni vardı (UndefinedColumnError →
kolonsuz yaz, CheckViolationError → status'ü 'blocked'a düşür). Sebebi
migration'ların canlıya elle uygulanmasıydı: push otomatik deploy tetiklediği
için kod, şemasından önce canlıya çıkabiliyordu. `app/migrate.py` bunu startup'ta
kapattığından merdiven ölü koda dönüştü ve kaldırıldı — semptomu tedavi ediyordu,
sebep artık yok.
"""
import json

import structlog

from .db import persistence_enabled, pool

log = structlog.get_logger()

_INSERT = """
    INSERT INTO chat_logs
      (session_id, status, reason, user_message, ai_response, latency_ms,
       retrieval, route, timings)
    VALUES ($1, $2, $3, $4, $5, $6, $7::jsonb, $8::jsonb, $9::jsonb)
"""

_REASON_MAX_LEN = 300


def _js(deger) -> str | None:
    return json.dumps(deger) if deger is not None else None


async def _write(status: str, session_id: str, reason: str | None, user_message: str,
                 ai_response: str | None, latency_ms: int,
                 retrieval: list[dict] | None = None,
                 route: dict | None = None,
                 timings: dict | None = None) -> None:
    if not persistence_enabled():
        return
    try:
        async with pool().acquire() as conn:
            await conn.execute(_INSERT, session_id, status, reason, user_message,
                               ai_response, latency_ms, _js(retrieval), _js(route),
                               _js(timings))
    except Exception:
        # Log yazamamak cevabı iptal etmek için yeterli bir sebep değil: kullanıcı
        # elindeki cevabı almalı. Sessiz kalmıyoruz, structlog'a düşüyor.
        log.exception("chat_log_write_failed", session_id=session_id, status=status)


async def log_blocked(session_id: str, user_message: str, reason: str, latency_ms: int,
                      route: dict | None = None, timings: dict | None = None) -> None:
    await _write("blocked", session_id, reason, user_message, None, latency_ms,
                 route=route, timings=timings)


async def log_allowed(
    session_id: str,
    user_message: str,
    ai_response: str,
    latency_ms: int,
    reason: str | None = None,
    retrieval: list[dict] | None = None,
    route: dict | None = None,
    timings: dict | None = None,
) -> None:
    await _write("allowed", session_id, reason, user_message, ai_response, latency_ms,
                 retrieval, route, timings)


async def log_error(
    session_id: str,
    user_message: str,
    exc: BaseException,
    latency_ms: int,
    retrieval: list[dict] | None = None,
    route: dict | None = None,
    timings: dict | None = None,
) -> None:
    """Agent/retrieval patladığında satır yazar — aksi halde prod hata oranı görünmez.

    retrieval trace'i de yazılır: patlamadan ÖNCE neyi getirdiğimiz, hatayı sonradan
    okurken en değerli bilgi.
    """
    reason = f"{type(exc).__name__}: {exc}"[:_REASON_MAX_LEN]
    await _write("error", session_id, reason, user_message, None, latency_ms,
                 retrieval, route, timings)
