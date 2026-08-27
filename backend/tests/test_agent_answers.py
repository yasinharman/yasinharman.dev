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


async def _ask(question: str, history: list | None = None, lang: str = "tr") -> tuple[str, list[dict]]:
    """/chat route'unun TAMAMINI çalıştırır; (cevap, trace) döner.

    Router geldikten sonra bu helper agent'ı doğrudan çağırmayı bıraktı: kapsam
    kararı ve bağlam çözümlemesi artık agent'ta değil router'da. Doğrudan çağırınca
    testler "reddetmedi" diye düşüyordu — ama kullanıcı o yolu hiç görmüyor.
    Sıra route ile birebir aynı: nezaket → router → agent.
    """
    from app.agent import initial_context, kept_sayisi, select_runner
    from app.retriever import retrieval_trace
    from app.router import classify, courtesy_reply, scope_reply

    trace: list[dict] = []
    retrieval_trace.set(trace)

    nazik = courtesy_reply(question, lang)
    if nazik is not None:
        return nazik.lower(), trace

    route = await classify(question, history or [])
    if route.category != "career":
        return scope_reply(route.category, lang).lower(), trace

    context = await initial_context(route.kb_query)
    # Secim route ile AYNI fonksiyondan geliyor; ayri secseydik testler
    # kullanicinin hic gormedigi bir yolu olcerdi.
    result = await select_runner(kept_sayisi(trace), lang).ainvoke(
        {"input": route.resolved_query, "history": history or [], "context": context})
    metin = result["output"] if isinstance(result, dict) else result.content
    return (metin or "").lower(), trace


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


async def _turn(question: str, history: list, lang: str = "tr") -> str:
    """Ham (küçük harfe çevrilmemiş) cevabı döner — bir sonraki turn'ün
    history'sinde AIMessage içeriği olarak kullanılmak üzere.

    Bilerek doğrudan agent: burada `context` hiç verilmiyor, yani bilgiye
    ulaşmanın tek yolu tool. Bu helper üretim yolunu ölçmüyor, yalnızca bir
    sonraki tura geçmiş metni üretiyor."""
    from app.agent import agent_executor

    result = await agent_executor(lang).ainvoke({"input": question, "history": history})
    return result.get("output") or ""


async def test_baglam_takip_sorusu_iletisim_bilgisi_verir():
    """Regresyon: 'nasıl geçicem?' gibi eksik bir takip sorusu, önceki asistan
    cevabıyla ('Yasin ile iletişime geçebilirsiniz') birleştirilip 'Yasin'in
    iletişim bilgileri nelerdir?' olarak yorumlanmalı — kapsam-dışı (C) reddi
    VERİLMEMELİ, iletişim bilgisi VERİLMELİ."""
    ilk_soru = "Yasin'in maaş beklentisi nedir?"
    ilk_cevap = await _turn(ilk_soru, [])
    history = [HumanMessage(content=ilk_soru), AIMessage(content=ilk_cevap)]

    answer, _trace = await _ask("nasıl geçicem?", history=history)
    assert "eğitildim" not in answer, (
        f"bağlama bağlı takip sorusu yanlışlıkla kapsam-dışı reddedildi: {answer!r}")
    assert any(s in answer for s in ["contact@yasinharman.dev", "linkedin", "upwork"]), (
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


@pytest.mark.parametrize("soru", [
    "Yasin kaç yaşında?",
    "Yasin kaç yaşında",
    "Yasin'in yaşı kaç?",
    "Yasin nerede yaşıyor?",
])
async def test_biyografik_soru_reddedilmez(soru):
    """Regresyon: yaş/yaşadığı şehir korpusta VAR ve A kategorisidir. Model bunları
    'özel hayat' sanıp tool'u hiç çağırmadan B reddi veriyordu. Aynı soru İngilizcede
    doğru cevaplanıyordu — hata Türkçe sınıflandırmadaydı."""
    answer, trace = await _ask(soru)
    assert trace, f"biyografik soruda portfolio_kb çağrılmadı: {soru!r}"
    assert "eğitildim" not in answer, f"biyografik soru yanlışlıkla reddedildi: {answer!r}"
    assert "bilgi yok" not in answer, f"korpusta olan bilgiye 'bilgi yok' dendi: {answer!r}"


async def test_ingilizce_mod_ingilizce_cevap_verir_ama_turkce_sorgular():
    """EN modunda cevap İngilizce olmalı; bilgi tabanı Türkçe olduğu ve rerank eşiği
    Türkçe sorgulara göre kalibre edildiği için tool sorgusu TÜRKÇE kalmalı."""
    answer, trace = await _ask("How old is Yasin?", lang="en")
    assert trace, "EN modunda portfolio_kb çağrılmadı"
    assert "21" in answer, f"yaş bilgisi cevaba girmedi: {answer!r}"
    turkce_harf = set("çğıöşüÇĞİÖŞÜ")
    turkce_sorgu = [c["query"] for c in trace if turkce_harf & set(c["query"])]
    assert turkce_sorgu, f"tool'a Türkçe sorgu gitmedi: {[c['query'] for c in trace]}"


@pytest.mark.parametrize("soru,beklenen", [
    ("What is Yasin's favourite food?", "about yasin's career"),
    ("What's the weather in Istanbul today?", "questions about yasin."),
])
async def test_ingilizce_reddetme_cumleleri(soru, beklenen):
    """İki reddetme kategorisi EN modunda da birbirine karışmadan çalışmalı."""
    answer, _ = await _ask(soru, lang="en")
    assert beklenen in answer, f"EN reddetme cümlesi yanlış: {answer!r}"


async def _iki_tur(t1: str, t1_lang: str, t2: str, t2_lang: str) -> tuple[str, list[dict]]:
    """İki turluk sohbet: ilk turun cevabı history'ye yazılır, ikinci tur onunla sorulur."""
    ilk = await _turn(t1, [], t1_lang)
    history = [HumanMessage(content=t1), AIMessage(content=ilk)]
    return await _ask(t2, history=history, lang=t2_lang)


async def test_hobi_takip_sorusu_reddedilmez():
    """Regresyon: "Bu spor ona ne kazandırmış?" takip sorusu B reddi alıyordu.
    Hobiler ve hobilerin kazandırdıkları A kategorisi; cevap korpusta var."""
    answer, _ = await _iki_tur("Yasin'in hobileri neler?", "tr",
                               "Bu spor ona ne kazandırmış?", "tr")
    # Yeni bir portfolio_kb çağrısı ŞART DEĞİL: powerlifting detayları ilk turun
    # cevabıyla zaten bağlamda. Önemli olan reddetmemesi ve içeriği vermesi.
    assert "eğitildim" not in answer, f"hobi takip sorusu reddedildi: {answer!r}"
    assert any(k in answer for k in ("disiplin", "hedef", "sistematik")), (
        f"powerlifting'in kazandırdıkları cevaba girmedi: {answer!r}")


async def test_dil_degisiminde_cevap_ingilizce_olur():
    """Regresyon: konuşma geçmişi Türkçeyken İngilizce tura geçilince cevap Türkçe
    geliyor ya da soru B'ye kayıyordu. Dil hatırlatması artık geçmişin hemen
    ardında, kullanıcı mesajının önünde ayrı bir mesaj olarak veriliyor."""
    answer, trace = await _iki_tur("Yasin kaç yaşında?", "tr",
                                   "And where does he live?", "en")
    assert trace, "dil değişimi turunda portfolio_kb çağrılmadı"
    assert "only trained" not in answer, f"dil değişiminde soru reddedildi: {answer!r}"
    assert "istanbul" in answer, f"şehir bilgisi gelmedi: {answer!r}"
    turkce_iz = [w for w in ("yaşıyor", "yaşında", "yaşamaktadır") if w in answer]
    assert not turkce_iz, f"EN turunda Türkçe cevap sızdı: {turkce_iz} -> {answer!r}"


@pytest.mark.parametrize("takip", ["how can I do that?", "how do I reach him?", "how?"])
async def test_ingilizce_eliptik_iletisim_sorusu(takip):
    """Regresyon: EN'de "iletişim kurmak" diye sorgulanınca retriever hakkimda.md'nin
    Diller bölümünü getiriyordu ("profesyonel ortamlarda İngilizce iletişim kurma");
    cevap iletişim bilgisi yerine dil becerisi anlatıyordu."""
    answer, trace = await _iki_tur("What are Yasin's salary expectations?", "en", takip, "en")
    assert trace, f"{takip!r} sorusunda portfolio_kb çağrılmadı"
    assert any(k in answer for k in ("contact@yasinharman.dev", "linkedin")), (
        f"iletişim bilgisi cevaba girmedi: {answer!r}")


@pytest.mark.parametrize("soru", [
    "Business Data Finder nedir",
    "Internship Tracker nedir",
    "Jarvis projesi nedir",
])
async def test_proje_cevabinda_is_deneyimi_rozeti_olmaz(soru):
    """Projelerin çalışma tipi yoktur; cevapta iş deneyimi rozeti çıkmamalı.

    Kontrol ROZET ŞEKLİ üzerinden: arayüz (MessageBody.jsx) bir parantezli satırı
    ancak ayraç, tarih veya bilinen bir çalışma tipi içeriyorsa rozet olarak çizer.
    Model ara sıra "( Proje )" gibi içi boş bir satır yazıyor — prompt kuralı bunu
    azaltıyor ama garanti etmiyor; garanti arayüz tarafında, o satır düz metne
    düşüyor. Burada test edilen şey de o: YANLIŞ ROZET yok."""
    import re
    ROZET_RE = re.compile(r"^\s*\((.+)\)\s*$")
    ANLAMLI_RE = re.compile(
        r"[·|;,]|\d|^\s*(tam zamanlı|yarı zamanlı|freelance|staj|full[- ]time|"
        r"part[- ]time|internship|remote|uzaktan)\s*$", re.IGNORECASE)

    answer, _ = await _ask(soru)
    rozetler = [m.group(1) for ln in answer.splitlines()
                if (m := ROZET_RE.match(ln)) and ANLAMLI_RE.search(m.group(1))]
    assert not rozetler, f"proje cevabında iş deneyimi rozeti var: {rozetler}"
