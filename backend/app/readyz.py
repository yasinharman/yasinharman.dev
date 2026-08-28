"""/readyz — bagimliliklar gercekten calisiyor mu.

/healthz kosulsuz {"status": "ok"} donuyor: surec ayakta mi, o kadar. Yanlis bir
SUPABASE_SERVICE_KEY ile deploy edilen konteyner da "saglikli" gorunuyor ve
arizayi ilk ogrenen ziyaretci oluyor.

Olculdu (2026-08-28): bir PR'in canliya inip inmedigini anlamanin tek yolu /chat'e
istek atmakti — 24 istek, hepsi chat_logs'a coplenen satir. Ayrica 2026-08-27'de
kod 3-large'a gecmisken vektor store 3-small'da kalmisti ve bunu ancak eval
kosarak fark ettik. /readyz ikisini de tek istekte, bedavaya cevapliyor.

Docker HEALTHCHECK bilerek /healthz'de BIRAKILDI. /readyz'yi healthcheck yapmak
Supabase'in gecici bir kesintisini konteyner yeniden baslatmaya cevirir; kismi bir
arizayi tam arizaya buyutmek olurdu. Buradaki is teshis, restart tetigi degil.

Cikti bilerek sirsiz: model adlari zaten public repoda, prompt_version bir ozet.
Anahtar, DSN, hata metni DISARI VERILMEZ — hata durumunda yalnizca istisnanin
tipi yaziliyor.
"""
import asyncio
from time import monotonic

from .config import get_settings
from .db import persistence_enabled, pool
from .deps import supabase_client
from .version import prompt_version

# Endpoint auth'suz ve halka acik; her istek Supabase'e gitmesin diye kisa bir
# onbellek. 5 sn tekrarlanan istekleri emmeye yeter, teshis degerini bozmaz.
_TTL = 5.0
_cache: tuple[float, dict] | None = None
_ZAMAN_ASIMI = 5.0


async def _db_check() -> str:
    if not persistence_enabled():
        return "skip (MODE=local)"
    try:
        async with pool().acquire() as con:
            await asyncio.wait_for(con.fetchval("SELECT 1"), timeout=_ZAMAN_ASIMI)
        return "ok"
    except Exception as e:  # noqa: BLE001 — teshis endpoint'i hicbir arizada patlamamali
        return f"error: {type(e).__name__}"


def _corpus_probe() -> tuple[int, dict]:
    """(chunk sayisi, ornek bir chunk'in metadata'si). Tek sorgu."""
    s = get_settings()
    resp = (supabase_client().table(s.SUPABASE_TABLE)
            .select("metadata", count="exact")
            .limit(1)
            .execute())
    ornek = (resp.data or [{}])[0].get("metadata") or {}
    return resp.count or 0, ornek


async def _supabase_check() -> tuple[str, int | None, str]:
    """(durum, chunk sayisi, store'un embedding modeli) doner."""
    try:
        adet, ornek = await asyncio.wait_for(asyncio.to_thread(_corpus_probe),
                                             timeout=_ZAMAN_ASIMI)
    except Exception as e:  # noqa: BLE001
        return f"error: {type(e).__name__}", None, "unknown"

    # Bos korpus "calisiyor" degil: RPC ayakta ama her soru "bilgim yok" doner.
    if adet == 0:
        return "error: empty_corpus", 0, "unknown"

    # ASIL KONTROL: store hangi modelle yazildi, kod hangisiyle soruyor?
    # Uyusmazlik sessiz calisiyor — cevaplar makul gorunmeye devam ediyor ama
    # vektor siralamasi coper (2026-08-27 olcumu: recall@1 %78.6 -> %14.3).
    store_model = ornek.get("embed_model") or "unknown"
    kod_model = get_settings().OPENAI_EMBED_MODEL
    if store_model == "unknown":
        # Alan eklenmeden once yazilmis chunk'lar. Karar verilemiyor; hazir
        # sayiliyor ama gorunur kaliyor: re-ingest sonrasi kendiliginden duzelir.
        return "ok", adet, "unknown (re-ingest ile isaretlenir)"
    if store_model != kod_model:
        return f"error: embed_model_mismatch (store={store_model})", adet, store_model
    return "ok", adet, store_model


async def readiness() -> tuple[dict, bool]:
    """(govde, hazir_mi) doner. Hazir degilse cagiran 503 yazar."""
    global _cache
    simdi = monotonic()
    if _cache is not None and simdi - _cache[0] < _TTL:
        govde = _cache[1]
        return govde, govde["status"] == "ok"

    s = get_settings()
    db, (supa, adet, store_model) = await asyncio.gather(_db_check(), _supabase_check())
    hazir = db in ("ok", "skip (MODE=local)") and supa == "ok"
    govde = {
        "status": "ok" if hazir else "degraded",
        "mode": s.MODE,
        "checks": {"db": db, "supabase": supa},
        "corpus": {"chunks": adet, "embed_model": store_model},
        "config": {
            "embed_model": s.OPENAI_EMBED_MODEL,
            "embed_dim": s.OPENAI_EMBED_DIM,
            "chat_model": s.OPENAI_CHAT_MODEL,
            "router_model": s.OPENAI_ROUTER_MODEL,
            "prompt_version": prompt_version(),
        },
    }
    _cache = (simdi, govde)
    return govde, hazir


def _cache_temizle() -> None:
    """Testler icin: onbellek surec omru boyunca yasiyor."""
    global _cache
    _cache = None
