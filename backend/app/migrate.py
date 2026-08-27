"""Chat DB şemasını kodla aynı sürümde tutar.

Neden var: `main`'e push = Coolify'da canlı deploy, ama migration'lar elle
uygulanıyordu. Yani yeni bir kolona yazan kod, kolon açılmadan ÖNCE canlıya
çıkabiliyordu. `logging_db._insert` bu yüzden üç kademeli bir fallback
merdiveniyle yazılmıştı: CheckViolation → eski status kümesi, UndefinedColumn →
kolonsuz yaz. Merdiven semptomu tedavi ediyordu; sebep bu dosyayla kapanıyor.

İki ayrı veritabanı var ve karıştırılmaları pahalı olurdu:
  chat      → DATABASE_URL (Coolify Postgres): chat_messages, chat_logs.
  supabase  → vektör store; ayrı kimlik bilgileriyle, SQL editöründen uygulanır.
Hedef, dosyanın ilk satırındaki `-- target:` yönergesinden okunur. Yönergesi
olmayan dosya SESSİZCE ATLANMAZ, hata verir: sessiz atlama, migration'ın
uygulandığını sanıp uygulanmamış olmasıyla aynı sonucu doğururdu.

Çalıştırma:  cd backend && python -m app.migrate
"""
import asyncio
import re
from pathlib import Path

import structlog

from .db import close_pool, init_pool, persistence_enabled, pool

MIGRATIONS_DIR = Path(__file__).resolve().parents[1] / "migrations"

_HEDEF_RE = re.compile(r"^--\s*target:\s*(\S+)", re.MULTILINE)
_GECERLI_HEDEFLER = {"chat", "supabase"}

# Rolling deploy sirasinda eski ve yeni konteyner kisa sure birlikte yasar; ikisi
# de ayni anda migration kosarsa DDL yarisir. Advisory lock tek instance'ta da
# bedava, iki instance'ta gerekli.
_KILIT = 8_140_027


def _hedef(sql: str, ad: str) -> str:
    m = _HEDEF_RE.search(sql)
    if not m:
        raise ValueError(
            f"{ad}: ilk satirda '-- target: chat' veya '-- target: supabase' yok. "
            "Hedefsiz dosya calistirilmaz."
        )
    hedef = m.group(1)
    if hedef not in _GECERLI_HEDEFLER:
        raise ValueError(f"{ad}: bilinmeyen hedef {hedef!r}, {_GECERLI_HEDEFLER} bekleniyordu")
    return hedef


def chat_migrations() -> list[tuple[str, str]]:
    """(surum, sql) — yalnizca chat DB'ye ait olanlar, dosya adina gore sirali."""
    dosyalar = sorted(MIGRATIONS_DIR.glob("*.sql"))
    cikti = []
    for p in dosyalar:
        sql = p.read_text(encoding="utf-8")
        if _hedef(sql, p.name) == "chat":
            cikti.append((p.stem, sql))
    return cikti


async def run_migrations() -> list[str]:
    """Uygulanmamis chat migration'larini sirayla uygular, uygulananlarin listesini doner.

    Hata YUTULMAZ: bozuk bir migration'da exception yukari cikar ve (lifespan'den
    cagrildiginda) konteyner ayaga kalkmaz. Bilinen yanlis bir semayla servis
    vermek, hic servis vermemekten kotudur — config.py'daki MODE=prod fail-fast'i
    ile ayni tercih.

    Ilk kosuda schema_migrations bos oldugu icin canlida ZATEN uygulanmis olan
    001/003/004/005 yeniden calisir. Dordu de idempotent (IF NOT EXISTS /
    DROP CONSTRAINT IF EXISTS), bu yuzden guvenli ve bilincli.
    """
    log = structlog.get_logger()
    async with pool().acquire() as con:
        await con.execute(
            "CREATE TABLE IF NOT EXISTS schema_migrations ("
            "  version    text PRIMARY KEY,"
            "  applied_at timestamptz NOT NULL DEFAULT now())"
        )
        await con.execute("SELECT pg_advisory_lock($1)", _KILIT)
        try:
            uygulanan = {
                r["version"] for r in await con.fetch("SELECT version FROM schema_migrations")
            }
            yeni: list[str] = []
            for surum, sql in chat_migrations():
                if surum in uygulanan:
                    continue
                async with con.transaction():
                    await con.execute(sql)
                    await con.execute(
                        "INSERT INTO schema_migrations (version) VALUES ($1)", surum
                    )
                log.info("migration_applied", version=surum)
                yeni.append(surum)
            return yeni
        finally:
            await con.execute("SELECT pg_advisory_unlock($1)", _KILIT)


async def _cli() -> None:
    await init_pool()
    if not persistence_enabled():
        print("MODE=local — chat DB bağlantısı kurulmadı, uygulanacak bir şey yok.")
        return
    try:
        yeni = await run_migrations()
        print("\n".join(f"uygulandı: {v}" for v in yeni) if yeni else "güncel, yeni migration yok.")
    finally:
        await close_pool()


if __name__ == "__main__":
    asyncio.run(_cli())
