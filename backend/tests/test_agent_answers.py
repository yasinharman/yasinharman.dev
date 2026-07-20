"""Agent-seviyesi eval: retriever değil, agent'ın ÜRETTİĞİ sorgular test edilir.

golden.yaml search()'ü hazır tam cümlelerle çağırdığı için, agent'ın tool'a
kısa keyword göndermesinden kaynaklanan hataları yapısal olarak yakalayamaz
(bkz. "hobiler" → rerank 0.09, "Yasin'in hobileri neler?" → 0.99). Bu dosya
agent'ı uçtan uca çalıştırıp hem final cevabı hem de retrieval_trace'e düşen
sorguların biçimini doğrular.

Çalıştırma: pytest -m integration
"""
import os
from pathlib import Path

import pytest

_HAS_KEYS = bool(os.getenv("OPENAI_API_KEY")) or (Path(__file__).parents[1] / ".env").exists()

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(not _HAS_KEYS, reason="gerçek API anahtarları yok"),
]

_NO_INFO = "bilgim yok"


async def _ask(question: str) -> tuple[str, list[dict]]:
    """Agent'ı /chat route'uyla aynı şekilde çalıştırır; (cevap, trace) döner."""
    from app.agent import agent_executor
    from app.retriever import retrieval_trace

    trace: list[dict] = []
    retrieval_trace.set(trace)
    result = await agent_executor().ainvoke({"input": question, "history": []})
    return (result.get("output") or "").lower(), trace


async def test_hobi_sorusu_cevaplanir():
    """Hobiler chunk'ı DB'de var; agent kısa sorgu atarsa eşik altı kalıp boş döner."""
    answer, trace = await _ask("Yasin'in hobilerinden bahseder misin?")
    assert "powerlifting" in answer, f"hobi bilgisi cevaba girmedi: {answer!r}"
    assert _NO_INFO not in answer, f"bilgi tabanında olan konuya 'bilgim yok' dedi: {answer!r}"
    assert trace, "portfolio_kb hiç çağrılmadı"


async def test_is_tecrubesi_tum_megagear_calismalarini_kapsar():
    """deneyim.md'de MegaGear 3 ayrı bölüm; tek sorgu yalnızca ilkini getirir."""
    answer, _ = await _ask("Yasin'in iş tecrübelerinden bahseder misin?")
    eksik = [ad for ad, anahtarlar in {
        "veri altyapısı": ("postgresql", "etsy", "shopify"),
        "scoring engine": ("scoring", "segment"),
        "meta reklam botu": ("meta", "custom audience", "reklam"),
    }.items() if not any(k in answer for k in anahtarlar)]
    assert not eksik, f"MegaGear çalışmalarından bahsedilmedi: {eksik} — cevap: {answer!r}"


@pytest.mark.parametrize("soru", [
    "Yasin'in hobilerinden bahseder misin?",
    "Yasin'in iş tecrübelerinden bahseder misin?",
    "projeler",
])
async def test_tool_sorgulari_keyword_degil_cumle(soru):
    """Rerank çıplak keyword'de skoru eşiğin altına düşürdüğü için sorgular
    cümle biçiminde olmalı — kullanıcı tek kelime yazsa bile."""
    _, trace = await _ask(soru)
    assert trace, "portfolio_kb hiç çağrılmadı"
    kisa = [c["query"] for c in trace if len(c["query"].split()) < 3]
    assert not kisa, f"agent tool'a kısa keyword sorgu gönderdi: {kisa}"
