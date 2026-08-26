"""Rerank eşiği birim testleri — ağ gerektirmez.

Regresyon: RERANK_MIN_SCORE=0.3 sabit eşikti. Cohere skorları sorgunun BİÇİMİNE
göre uçtuğu için ("hobiler" → 0.09, "Yasin'in hobileri neler?" → 0.99) bu sayı
anlamlı bir sınır değildi; altında kalan her şey elenince kept=[] oluyor ve model,
aramanın başarısız olduğunu bilmeden "bilgim yok" diyordu.
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
    kept, cutoff, fallback = _apply_cutoff(_docs(0.99, 0.81, 0.44, 0.12, 0.03), s)

    assert cutoff == 0.99 * s.RERANK_REL_RATIO
    assert _skorlar(kept) == [0.99, 0.81, 0.44]
    assert fallback is False


def test_duz_dagilimda_hepsi_kalir():
    """Skorlar birbirine yakınsa hiçbiri elenmemeli — mutlak eşik burada
    keyfi bir yerden keserdi."""
    kept, _, fallback = _apply_cutoff(_docs(0.62, 0.58, 0.55, 0.51), get_settings())
    assert len(kept) == 4
    assert fallback is False


def test_hepsi_dusukse_bos_donmez():
    """"hobiler" senaryosu: chunk DB'de var, skoru 0.09. Eski davranış boş dönüp
    "bilgim yok" ürettiriyordu."""
    s = get_settings()
    kept, cutoff, fallback = _apply_cutoff(_docs(0.09, 0.07, 0.05, 0.02), s)

    assert fallback is True
    assert len(kept) == s.RERANK_FALLBACK_N
    assert _skorlar(kept) == [0.09, 0.07, 0.05], "en iyi N chunk sırayla dönmeli"
    assert cutoff == s.RERANK_ABS_FLOOR, "top1 zaten tabanın altında"


def test_esik_hicbir_zaman_tabanin_altina_inmez():
    """Relative cutoff tek başına kullanılsaydı top1 ne kadar düşük olursa olsun
    daima birileri geçerdi; taban bunu engelliyor."""
    s = get_settings()
    _, cutoff, _ = _apply_cutoff(_docs(0.20, 0.19), s)
    assert cutoff == s.RERANK_ABS_FLOOR
    assert cutoff > 0.20 * s.RERANK_REL_RATIO


def test_bos_liste_patlatmaz():
    assert _apply_cutoff([], get_settings()) == ([], 0.0, False)


def test_trace_esigi_ve_fallbacki_kaydeder():
    """Kaç sorguda hiçbir chunk eşiği geçemedi — bunu hiçbir yerde ölçmüyorduk."""
    trace: list[dict] = []
    retrieval_trace.set(trace)
    try:
        reranked = _docs(0.09, 0.07)
        kept, cutoff, fallback = _apply_cutoff(reranked, get_settings())
        _record_trace("hobiler", reranked, kept, cutoff, fallback)
    finally:
        retrieval_trace.set(None)

    kayit, = trace
    assert kayit["query"] == "hobiler"
    assert kayit["fallback_used"] is True
    assert kayit["cutoff"] == 0.15
    assert kayit["kept"] == 2
