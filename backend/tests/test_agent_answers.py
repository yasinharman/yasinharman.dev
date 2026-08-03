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
from langchain_core.messages import AIMessage, HumanMessage

_HAS_KEYS = bool(os.getenv("OPENAI_API_KEY")) or (Path(__file__).parents[1] / ".env").exists()

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(not _HAS_KEYS, reason="gerçek API anahtarları yok"),
]

_NO_INFO = "bilgim yok"


async def _ask(question: str, history: list | None = None) -> tuple[str, list[dict]]:
    """Agent'ı /chat route'uyla aynı şekilde çalıştırır; (cevap, trace) döner."""
    from app.agent import agent_executor
    from app.retriever import retrieval_trace

    trace: list[dict] = []
    retrieval_trace.set(trace)
    result = await agent_executor().ainvoke({"input": question, "history": history or []})
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


@pytest.mark.parametrize("soru", ["yasin kim", "yasin kimdir", "yasini tanıt"])
async def test_kimlik_sorusu_cevaplanir(soru):
    """'Yasin kim/kimdir' kimlik sorusudur, kapsam-dışı DEĞİL: model bunu
    reddedip tool'u atlıyordu (regresyon). Tool çağrılıp tanıtım verilmeli."""
    answer, trace = await _ask(soru)
    assert trace, f"kimlik sorusunda portfolio_kb çağrılmadı: {soru!r}"
    assert "eğitildim" not in answer, f"kimlik sorusu yanlışlıkla reddedildi: {answer!r}"
    assert "python" in answer, f"tanıtım içeriği gelmedi: {answer!r}"


async def test_kariyer_disi_ozel_soru_reddedilir():
    """Yasin hakkında ama kariyer dışı özel soru -> 'kariyeri hakkındaki' reddi."""
    answer, _ = await _ask("Yasin'in en sevdiği yemek nedir?")
    assert "kariyeri hakkındaki sorulara cevap vermek için eğitildim" in answer, (
        f"kariyer-dışı özel soruya yanlış cevap: {answer!r}")


async def test_alakasiz_soru_reddedilir():
    """Yasin ile ilgisiz soru -> 'Yasin hakkındaki soruları' reddi (kariyer reddi DEĞİL)."""
    answer, _ = await _ask("Bugün İstanbul'da hava nasıl?")
    assert "yasin hakkındaki soruları cevaplamak için eğitildim" in answer, (
        f"alakasız soruya yanlış cevap: {answer!r}")
    assert "kariyeri" not in answer, f"alakasız soruya kariyer reddi verildi: {answer!r}"


async def _turn(question: str, history: list) -> str:
    """Ham (küçük harfe çevrilmemiş) cevabı döner — bir sonraki turn'ün
    history'sinde AIMessage içeriği olarak kullanılmak üzere."""
    from app.agent import agent_executor

    result = await agent_executor().ainvoke({"input": question, "history": history})
    return result.get("output") or ""


async def test_baglam_takip_sorusu_iletisim_bilgisi_verir():
    """Regresyon: 'nasıl geçicem?' gibi eksik bir takip sorusu, önceki asistan
    cevabıyla ('Yasin ile iletişime geçebilirsiniz') birleştirilip 'Yasin'in
    iletişim bilgileri nelerdir?' olarak yorumlanmalı — kapsam-dışı (C) reddi
    VERİLMEMELİ, iletişim bilgisi VERİLMELİ."""
    ilk_soru = "Yasin'in maaş beklentisi nedir?"
    ilk_cevap = await _turn(ilk_soru, [])
    history = [HumanMessage(content=ilk_soru), AIMessage(content=ilk_cevap)]

    answer, trace = await _ask("nasıl geçicem?", history=history)
    assert "eğitildim" not in answer, (
        f"bağlama bağlı takip sorusu yanlışlıkla kapsam-dışı reddedildi: {answer!r}")
    assert any(s in answer for s in ["contact@yasinharman.dev", "linkedin", "upwork", "0532"]), (
        f"iletişim bilgisi cevaba girmedi: {answer!r}")


async def test_baglam_konu_degisince_eski_baglami_zorlamaz():
    """Önceki turn Yasin hakkında olsa bile, kullanıcı tamamen alakasız yeni
    bir konuya geçerse eski bağlam ZORLA uygulanmamalı; normal Kategori C
    reddi hâlâ verilmeli (Bağlam Çözümleme istisnasının regresyon testi)."""
    ilk_soru = "Yasin'in projelerinden bahseder misin?"
    ilk_cevap = await _turn(ilk_soru, [])
    history = [HumanMessage(content=ilk_soru), AIMessage(content=ilk_cevap)]

    answer, _ = await _ask("Bugün İstanbul'da hava nasıl?", history=history)
    assert "yasin hakkındaki soruları cevaplamak için eğitildim" in answer, (
        f"konu değiştiğinde eski bağlam sızdı / yanlış cevap: {answer!r}")
