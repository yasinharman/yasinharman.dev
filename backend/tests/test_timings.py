"""Latency ayrıştırması — chat_logs tek bir latency_ms tutuyordu ve yavaşlığın
router'dan mı retrieval'dan mı LLM'den mi geldiği DB'den okunamıyordu."""
from app.routes.chat import _timings


def test_nezaket_yolunda_sadece_toplam_var():
    """Router da retrieval da LLM de çalışmadı; uydurma sıfırlar yazmıyoruz."""
    assert _timings(12) == {"toplam_ms": 12}


def test_kapsam_disi_yolunda_router_var_llm_yok():
    t = _timings(300, router_ms=280)
    assert t == {"toplam_ms": 300, "router_ms": 280}


def test_retrieval_suresi_cagrilarin_toplami():
    """Agent tool'u birden fazla kez çağırabiliyor; tek bir başlangıç/bitiş
    ölçümü bunu kaçırırdı."""
    trace = [{"duration_ms": 120}, {"duration_ms": 200}]
    t = _timings(1500, router_ms=300, trace=trace, agent_ms=1100)

    assert t["retrieval_ms"] == 320
    assert t["llm_ms"] == 780, "llm = agent süresi - retrieval süresi"
    assert t["kb_calls"] == 2


def test_duration_ms_yoksa_sifir_sayilir():
    """Eski trace kayıtlarında bu alan yok; KeyError yerine 0."""
    t = _timings(900, router_ms=100, trace=[{"query": "x"}], agent_ms=800)
    assert t["retrieval_ms"] == 0
    assert t["llm_ms"] == 800


def test_llm_negatife_dusmez():
    """Saat çözünürlüğü retrieval'ı agent'tan uzun gösterebilir; negatif süre
    raporlamak sayının kendisinden daha yanıltıcı olur."""
    t = _timings(500, router_ms=10, trace=[{"duration_ms": 400}], agent_ms=390)
    assert t["llm_ms"] == 0
