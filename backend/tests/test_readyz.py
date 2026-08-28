"""/readyz birim testleri — ağ yok, Supabase ve DB sahtelenir.

Endpoint'in varlık sebebi: /healthz koşulsuz "ok" döndüğü için yanlış bir
anahtarla ya da yanlış modelle deploy edilmiş bir konteyner de sağlıklı görünüyor.
Buradaki vakalar tam olarak o "sessizce yanlış" durumları kilitliyor.
"""
import asyncio

import pytest

from app import readyz


@pytest.fixture(autouse=True)
def _temiz_onbellek():
    """İki ayrı önbellek: readyz'ninki ve Settings'inki. Settings'i test içinde
    temizlemek yetmez — test yarıda kalırsa sonraki testlere sızar."""
    from app.config import get_settings
    readyz._cache_temizle()
    get_settings.cache_clear()
    yield
    readyz._cache_temizle()
    get_settings.cache_clear()


def _kur(monkeypatch, *, adet=18, metadata=None, patlat=None, db_var=False):
    def sahte_probe():
        if patlat:
            raise patlat
        return adet, metadata if metadata is not None else {}
    monkeypatch.setattr(readyz, "_corpus_probe", sahte_probe)
    monkeypatch.setattr(readyz, "persistence_enabled", lambda: db_var)


def _kos():
    return asyncio.run(readyz.readiness())


def test_her_sey_yolundaysa_hazir(monkeypatch):
    _kur(monkeypatch, metadata={"embed_model": "text-embedding-3-small"})
    monkeypatch.setenv("OPENAI_EMBED_MODEL", "text-embedding-3-small")

    govde, hazir = _kos()
    assert hazir and govde["status"] == "ok"
    assert govde["corpus"] == {"chunks": 18, "embed_model": "text-embedding-3-small"}


def test_store_ile_kodun_modeli_farkliysa_degraded(monkeypatch):
    """2026-08-27 olayının regresyon testi: kod 3-large'a geçmişti, store
    3-small'da kalmıştı. Canlı cevaplar doğru görünüyordu (18 chunk'ın 12'si
    zaten rerank'e gidiyor), fark ancak eval koşarak görüldü."""
    _kur(monkeypatch, metadata={"embed_model": "text-embedding-3-small"})
    monkeypatch.setenv("OPENAI_EMBED_MODEL", "text-embedding-3-large")

    govde, hazir = _kos()
    assert not hazir and govde["status"] == "degraded"
    assert "embed_model_mismatch" in govde["checks"]["supabase"]
    assert "text-embedding-3-small" in govde["checks"]["supabase"], "hangi model olduğu yazmalı"


def test_isaretsiz_eski_chunklar_hazir_sayilir_ama_gorunur(monkeypatch):
    """Alan eklenmeden önce yazılmış satırlar: karar verilemiyor, servis
    durdurulmaz ama /readyz bunu saklamaz."""
    _kur(monkeypatch, metadata={"source": "projeler.md"})
    govde, hazir = _kos()
    assert hazir
    assert govde["corpus"]["embed_model"].startswith("unknown")


def test_bos_korpus_hazir_degildir(monkeypatch):
    """RPC ayakta ama her soru 'bilgim yok' döner — bu 'çalışıyor' değildir."""
    _kur(monkeypatch, adet=0)
    govde, hazir = _kos()
    assert not hazir
    assert govde["checks"]["supabase"] == "error: empty_corpus"


def test_supabase_patlarsa_yalnizca_istisna_tipi_disari_cikar(monkeypatch):
    """Hata metni anahtar/DSN taşıyabilir; endpoint auth'suz ve halka açık."""
    _kur(monkeypatch, patlat=RuntimeError("apikey=super-secret-abc123"))
    govde, hazir = _kos()
    assert not hazir
    assert govde["checks"]["supabase"] == "error: RuntimeError"
    assert "super-secret" not in str(govde)


def test_db_hatasi_hazirligi_dusurur(monkeypatch):
    _kur(monkeypatch, db_var=True)

    class _Pool:
        def acquire(self):
            raise ConnectionError("pool kapali")
    monkeypatch.setattr(readyz, "pool", lambda: _Pool())

    govde, hazir = _kos()
    assert not hazir
    assert govde["checks"]["db"] == "error: ConnectionError"


def test_local_modda_db_atlanir(monkeypatch):
    _kur(monkeypatch, db_var=False)
    govde, hazir = _kos()
    assert hazir and govde["checks"]["db"].startswith("skip")


def test_onbellek_ikinci_istekte_supabaseye_gitmez(monkeypatch):
    """Endpoint auth'suz: art arda çağrı Supabase'e yük bindirmemeli."""
    sayac = {"n": 0}

    def sahte_probe():
        sayac["n"] += 1
        return 18, {"embed_model": "text-embedding-3-small"}
    monkeypatch.setattr(readyz, "_corpus_probe", sahte_probe)
    monkeypatch.setattr(readyz, "persistence_enabled", lambda: False)

    for _ in range(3):
        _kos()
    assert sayac["n"] == 1, "onbellek çalışmıyor"
