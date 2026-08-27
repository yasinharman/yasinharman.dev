"""Korpusun kendi sağlığı — canlı Supabase + Cohere gerektirir.

Neden var: 2026-08-27'de "Teknolojiler ve Araçlar" chunk'ı Cohere rerank'te
0.0055 alıp her cevaptan eleniyordu, ama 30 vakalık golden set 30/30 diyordu.
Bug'ı yakalayan şey testler değil, elle yazılmış tek seferlik bir probe'du.
Bu dosya o probe'un kalıcı hali.

Çalıştırma: pytest -m integration
"""
import asyncio

import pytest

from app.config import ENV_FILE, get_settings

_HAS_KEYS = bool(__import__("os").getenv("OPENAI_API_KEY")) or ENV_FILE.exists()

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(not _HAS_KEYS, reason="gerçek API anahtarları yok"),
]


def _chunklari_getir() -> list[dict]:
    """Ağ çağrısı test GÖVDESİNDE yapılır, collection'da değil: parametrize etseydik
    `pytest -m "not integration"` bile Supabase'e gitmek zorunda kalırdı."""
    from app.deps import supabase_client

    resp = supabase_client().table("documents").select("content,metadata").execute()
    return resp.data or []


def _breadcrumb(icerik: str) -> str:
    return icerik.split("\n", 1)[0].strip()


async def test_her_chunk_kendi_konusundaki_soruda_rerank_esigini_geciyor():
    """Bir chunk, KENDİ başlığından üretilen soruda eşiğin altında kalıyorsa sorun
    sıralama değil biçimdir: metin öznesiz/fiilsiz bir liste olduğunda cross-encoder
    onu soruyla ilişkilendiremiyor. Bulgu B tam olarak buydu."""
    from app.retriever import _cohere

    s = get_settings()
    chunklar = await asyncio.to_thread(_chunklari_getir)
    assert chunklar, "vektör store boş — ingest edilmiş mi?"

    cc = _cohere()

    def _skor(icerik: str) -> float:
        baslik = _breadcrumb(icerik).split(">")[-1].strip()
        soru = f"Yasin'in {baslik} hakkında bilgi verir misin?"
        r = cc.rerank(model=s.COHERE_RERANK_MODEL, query=soru, documents=[icerik], top_n=1)
        return r.results[0].relevance_score

    skorlar = await asyncio.gather(
        *(asyncio.to_thread(_skor, c["content"]) for c in chunklar)
    )
    dusuk = [
        (skor, c["metadata"].get("source", "?"), _breadcrumb(c["content"]))
        for skor, c in zip(skorlar, chunklar, strict=True)
        if skor < s.RERANK_SCORE_THRESHOLD
    ]
    assert not dusuk, "kendi konusundaki soruda eşiği geçemeyen chunk'lar:\n" + "\n".join(
        f"  {skor:.4f}  {kaynak}  {bc}" for skor, kaynak, bc in sorted(dusuk)
    )


async def test_expected_all_beklentileri_tam_olarak_bir_chunki_sabitliyor():
    """expected_all'ın tek işi belirli bir chunk'ın hayatta kaldığını doğrulamak.
    Korpus değişip beklenti iki chunk'a birden uyar hale gelirse sessizce gevşer;
    hiçbirine uymaz hale gelirse vaka yanlış sebepten kırmızıya döner. İkisi de
    yaşandı, bu yüzden ölçülüyor."""
    from eval.run_eval import load_golden

    chunklar = await asyncio.to_thread(_chunklari_getir)
    metinler = [(c["content"].lower(), _breadcrumb(c["content"])) for c in chunklar]

    hatalar = []
    for entry in load_golden():
        gerekli = entry.get("expected_all")
        if not gerekli:
            continue
        eslesen = [bc for metin, bc in metinler if all(p.lower() in metin for p in gerekli)]
        if len(eslesen) != 1:
            hatalar.append(f"  {entry['id']}: {len(eslesen)} chunk eşleşti {eslesen or ''}")
    assert not hatalar, "expected_all beklentileri tek chunk sabitlemiyor:\n" + "\n".join(hatalar)
