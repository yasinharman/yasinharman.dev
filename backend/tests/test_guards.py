"""Guard birim testleri — API anahtarı gerektirmez, hızlı suite'te çalışır."""
import pathlib

from app.agent import SYSTEM_PROMPT, _system_prompt
from app.guards import LEAK_SIGNALS, output_guard

DATA = pathlib.Path(__file__).parents[1] / "data"


def test_leak_signals_korpusla_catismaz():
    """Regresyon: LEAK_SIGNALS'ta çıplak "portfolio_kb" vardı; tool'un adı
    data/projeler.md'de RAG projesinin mimarisi anlatılırken de geçiyor. Sonuç:
    "projelerinden bahset" sorusuna üretilen DOĞRU cevap sızıntı sanılıp
    "Üzgünüm, bu soruyu cevaplayamıyorum." ile değiştiriliyordu."""
    catismalar = [
        (f.name, sig)
        for f in sorted(DATA.glob("*.md"))
        for sig in LEAK_SIGNALS
        if sig in f.read_text(encoding="utf-8")
    ]
    assert not catismalar, (
        f"leak sinyali bilgi tabanında geçiyor, meşru cevaplar bloklanır: {catismalar}"
    )


def test_mesru_proje_cevabi_bloklanmaz():
    """Korpustaki mimari açıklamasını birebir içeren cevap geçmeli."""
    cevap = (
        "Yasin'in projelerinden biri Jarvis:\n\n"
        "- Backend: Python FastAPI + LangChain tabanlı RAG servisi; agent, portfolio_kb\n"
        "  adlı retrieval tool'unu kullanır.\n\n"
        "- Vector store: Supabase (PostgreSQL + pgvector)."
    )
    assert output_guard(cevap)[1] is None, "meşru proje cevabı yanlışlıkla bloklandı"


def test_gercek_prompt_sizintisi_yakalanir():
    """Promptun büyük parçaları hâlâ sızıntı olarak yakalanmalı."""
    for lang in ("tr", "en"):
        prompt = _system_prompt(lang)
        assert output_guard(prompt, lang)[1] == "leak", f"{lang}: tam prompt kaçtı"
        assert output_guard(prompt[: len(prompt) // 2], lang)[1] == "leak", f"{lang}: ilk yarı kaçtı"

    for bolum in ("# KARAR AKIŞI", "## 1. Kapsam Kuralı", "# ROL VE AMAÇ"):
        parca = SYSTEM_PROMPT[SYSTEM_PROMPT.index(bolum):][:600]
        assert output_guard(parca)[1] == "leak", f"{bolum!r} bölümü kaçtı"


def test_turkce_yola_dil_katmani_eklenmez():
    """TR prompt = SYSTEM_PROMPT; İngilizce mod Türkçe davranışa hiçbir şey eklemez."""
    assert _system_prompt("tr") == SYSTEM_PROMPT
    assert _system_prompt("en") != SYSTEM_PROMPT
