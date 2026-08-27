"""Rerank eşiği birim testleri — ağ gerektirmez.

Eşiğin DEĞERİ burada test edilmez; o golden.yaml ile ölçüldü (0.40'ta 30/30, daha
düşük eşiklerde negatif vakalar sızıyor). Buradaki testler eleme davranışını ve
boş sonucun ize düşmesini koruyor.
"""
from langchain_core.documents import Document

from app.config import get_settings
from app.retriever import _apply_cutoff, _record_trace, retrieval_trace


def _docs(*skorlar: float) -> list[Document]:
    """Cohere sıralı döndürür; testler de öyle versin."""
    return [
        Document(page_content=f"chunk {i}", metadata={"rerank_score": s, "source": "x.md"})
        for i, s in enumerate(skorlar)
    ]


def _skorlar(docs: list[Document]) -> list[float]:
    return [d.metadata["rerank_score"] for d in docs]


def test_normal_dagilimda_alakasiz_kuyruk_elenir():
    s = get_settings()
    kept, cutoff = _apply_cutoff(_docs(0.99, 0.81, 0.44, 0.12, 0.03), s)

    assert cutoff == s.RERANK_SCORE_THRESHOLD
    assert _skorlar(kept) == [0.99, 0.81, 0.44]


def test_esigin_ustundekilerin_hepsi_kalir():
    kept, _ = _apply_cutoff(_docs(0.62, 0.58, 0.55, 0.51), get_settings())
    assert len(kept) == 4


def test_hepsi_dusukse_bos_doner():
    """Hiçbir chunk tabanı geçemezse BOŞ dönülür.

    Bir ara burada en iyi 3 chunk döndürülüyordu ("sessiz başarısızlık" korkusuyla).
    İki ölçüm bunun yanlış olduğunu gösterdi: canlıda 31 aramanın 0'ında tetiklendi,
    buna karşılık golden.yaml'daki dört negatif vakayı birden kırıyordu — kapsam dışı
    soruya alakasız chunk vermek halüsinasyon yüzeyi açıyor."""
    s = get_settings()
    kept, cutoff = _apply_cutoff(_docs(0.09, 0.07, 0.05, 0.02), s)

    assert kept == []
    assert cutoff == s.RERANK_SCORE_THRESHOLD, "top1 zaten tabanın altında"


def test_top1_dusukse_de_esik_dusmez():
    """Eşik bir ara top1'e göre hesaplanıyordu; o tasarımda her sorgu en az bir
    chunk döndürüyor, kapsam dışı sorulara alakasız context sızıyordu."""
    s = get_settings()
    kept, cutoff = _apply_cutoff(_docs(0.20, 0.19), s)
    assert cutoff == s.RERANK_SCORE_THRESHOLD
    assert kept == []


def test_bos_liste_patlatmaz():
    assert _apply_cutoff([], get_settings()) == ([], 0.0)


def test_trace_esigi_ve_bos_sonucu_kaydeder():
    """Kaç aramada 0 chunk döndü — bunu hiçbir yerde ölçmüyorduk. kept=0 bu sinyal."""
    trace: list[dict] = []
    retrieval_trace.set(trace)
    try:
        reranked = _docs(0.09, 0.07)
        kept, cutoff = _apply_cutoff(reranked, get_settings())
        _record_trace("hobiler", reranked, kept, cutoff, 42)
    finally:
        retrieval_trace.set(None)

    kayit, = trace
    assert kayit["query"] == "hobiler"
    assert kayit["cutoff"] == get_settings().RERANK_SCORE_THRESHOLD
    assert kayit["kept"] == 0
    assert kayit["context"] == [], "modele hiçbir chunk gitmedi, iz de öyle demeli"
    assert len(kayit["elenen"]) == 2, "elenenler ayrı anahtarda kalmalı, debug için"
    assert kayit["duration_ms"] == 42, "arama süresi çağrı başına kaydedilmeli"


async def test_iz_modele_giden_listeyi_yazar():
    """Regresyon: iz `reranked`i yazıyordu, yani genişletmeyle eklenen chunk'lar
    hiç loglanmıyordu. Ölçüldü — 41 aramanın 25'inde genişletme çalışmış ve 50
    chunk kayıt dışı modele gitmişti. Retrieval'ı debug ederken elimizdeki kayıt
    modelin gördüğünü yansıtmıyordu."""
    from langchain_core.documents import Document

    trace: list[dict] = []
    retrieval_trace.set(trace)
    try:
        reranked = _docs(0.95, 0.80, 0.10)
        kept, cutoff = _apply_cutoff(reranked, get_settings())
        genisleyen = Document(page_content="Detay bölümü", metadata={
            "source": "projeler.md", "rerank_score": 0.9499, "expanded_from": "projeler.md"})
        _record_trace("projeler", reranked, [*kept, genisleyen], cutoff, 7)
    finally:
        retrieval_trace.set(None)

    kayit, = trace
    assert kayit["kept"] == 3
    assert len(kayit["context"]) == 3, "genişleyen chunk da ize girmeli"
    assert kayit["context"][-1]["expanded"] is True
    assert [c["expanded"] for c in kayit["context"][:2]] == [False, False]
    assert len(kayit["elenen"]) == 1, "eşik altı kalan ayrı anahtarda"
