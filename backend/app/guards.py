"""Deterministic input and output guards ported from the n8n Code nodes."""
import re

from pydantic import BaseModel

from .config import get_settings


class GuardVerdict(BaseModel):
    allowed: bool
    category: str = "ok"
    reason: str = ""


INJECTION_PATTERNS = [
    "ignore previous", "ignore all previous", "disregard previous",
    "forget previous", "forget all", "forget everything",
    "system prompt", "system message", "your instructions",
    "you are now", "you are no longer", "new instructions",
    "önceki talimat", "önceki komut", "tüm talimatları unut",
    "sistem mesaj", "sistem talimat", "kurallarını unut",
    "rolünü değiştir", "rolünden çık", "artık sen",
    "###system", "<|system|>", "[system]", "```system",
    "assistant:", "user:", "system:",
    "jailbreak", "dan mode", "developer mode",
    "prompt leak", "reveal your", "show your prompt",
    "sistem promptunu", "promptunu göster", "promptunu yaz",
]

_SUSPICIOUS_CHARS_RE = re.compile(r"[#`{}\[\]<>|]")


async def input_guard(message: str) -> GuardVerdict:
    msg = (message or "").strip()
    if not msg or len(msg) < 2:
        return GuardVerdict(allowed=False, category="empty_or_short", reason="empty_or_short")
    if len(msg) > get_settings().MAX_INPUT_LENGTH:
        return GuardVerdict(allowed=False, category="too_long", reason="too_long")

    lower = msg.lower()
    if any(p in lower for p in INJECTION_PATTERNS):
        return GuardVerdict(allowed=False, category="injection", reason="injection")

    if len(_SUSPICIOUS_CHARS_RE.findall(msg)) > 10:
        return GuardVerdict(allowed=False, category="format", reason="format")

    return GuardVerdict(allowed=True, category="ok")


# Sistem promptunun kullanıcıya sızdığını gösteren işaretler.
#
# DİKKAT: Buraya çıplak "portfolio_kb" KOYMAYIN. Tool'un adı bilgi tabanında da
# geçiyor (data/projeler.md, RAG projesinin mimarisi anlatılırken), dolayısıyla
# "projelerinden bahset" gibi tamamen meşru bir soruya verilen doğru cevap
# sızıntı sanılıp siliniyordu. Sinyaller, prompt'a özgü TALİMAT ifadeleri
# olmalı — bir proje açıklamasında geçmesi mümkün olmayan cümle parçaları.
# İki liste bilerek ayrı:
#   _PROMPT_SIGNALS  -> prompt'ta GERÇEKTEN geçen ifadeler. Bir bölüm yeniden
#                       adlandırılırsa guard sessizce körleşirdi; artık
#                       test_leak_signals_prompt_ile_senkron bunu yakalıyor.
#   _GENERIC_SIGNALS -> prompt'a bağlı olmayan, her zaman şüpheli ifadeler.
#
# Router geldikten sonra prompt'tan silinen bölümlerin sinyalleri de buradan
# temizlendi (KARAR AKIŞI, Kapsam Kuralı, "### A)" ... ). Ölü sinyal zararsız
# görünür ama listeyi okuyan bir sonraki kişiyi yanıltır: guard'ın hâlâ o bölümü
# koruduğunu sanır.
_PROMPT_SIGNALS = [
    # Bolum basliklari
    "ROL VE AMAÇ", "ARAÇ KULLANIMI", "DÜRÜSTLÜK", "POZİSYON UYGUNLUĞU",
    "PROJE ANLATIMI", "CEVAP FORMATI", "YASAKLAR", "Biçim Sözleşmesi",
    # Prompt'a ozgu talimat cumleleri — bir proje aciklamasinda gecmesi mumkun degil
    "KAPSAM KARARI SANA GELMEDEN ÖNCE VERİLDİ",
    "BİLGİYİ ERTELEYEN CEVAP YASAK",
    "GENİŞ SORULARDA ÖZET + DETAY",
    "transferable skill yaklaşımı",
    # Tool'a dair TALIMAT cumleleri (yalin tool adi bilerek yok — korpusta geciyor)
    "tool'unu çağır",
    # Ingilizce dil direktifi blogu
    "ANSWER LANGUAGE: ENGLISH",
]

_GENERIC_SIGNALS = [
    "system prompt", "system message",
]

LEAK_SIGNALS = _PROMPT_SIGNALS + _GENERIC_SIGNALS

_OUTPUT_LEAK_REPLACEMENT = {
    "tr": "Üzgünüm, bu soruyu cevaplayamıyorum.",
    "en": "Sorry, I can't answer that question.",
}
_OUTPUT_EMPTY_REPLACEMENT = {
    "tr": "Üzgünüm, şu an cevap üretemiyorum. Lütfen tekrar deneyin.",
    "en": "Sorry, I can't produce an answer right now. Please try again.",
}
OUTPUT_MAX_LEN = 3000

# LangChain, AgentExecutor iterasyon limitine carpinca cevap yerine sabit bir
# Ingilizce metin dondurur (langchain/agents/agent.py:967 ve :311 — iki farkli
# metin, ortak prefix bu). Metin output_guard'in uc kontrolunden de geciyordu:
# leak sinyali degil, 3000 karakterden kisa, bos degil. Sonuc: kullanicinin
# ekraninda Ingilizce bir LangChain hata mesaji.
#
# startswith kullaniliyor cunku LangChain bu metni cevabin TAMAMI olarak
# donduruyor; substring aramasi mesru bir cevabin icinde yanlis pozitif uretebilirdi.
#
# Bu bir yara bandi: dogru cozum limite carpildiginda eldeki chunk'larla bir
# synthesis cagrisi yapmak, o da kendi graph'imizi kurmayi gerektiriyor
# (bkz. notes/yapilacaklar.md FAZ 3.4).
_AGENT_STOPPED_PREFIX = "Agent stopped due to"


def output_guard(answer: str, lang: str = "tr") -> tuple[str, str | None]:
    """Return (sanitized_text, reason_if_modified)."""
    text = answer or ""

    if text.strip().startswith(_AGENT_STOPPED_PREFIX):
        return _OUTPUT_EMPTY_REPLACEMENT.get(lang, _OUTPUT_EMPTY_REPLACEMENT["tr"]), "iteration_limit"

    if any(s in text for s in LEAK_SIGNALS):
        return _OUTPUT_LEAK_REPLACEMENT.get(lang, _OUTPUT_LEAK_REPLACEMENT["tr"]), "leak"

    if len(text) > OUTPUT_MAX_LEN:
        return text[:OUTPUT_MAX_LEN] + "...", "truncated"

    if not text.strip():
        return _OUTPUT_EMPTY_REPLACEMENT.get(lang, _OUTPUT_EMPTY_REPLACEMENT["tr"]), "empty"

    return text, None


# Token akisinda output_guard'i sona saklamak ise yaramaz: sizinti daha guard
# calismadan ekrana yazilmis olur. Cozum bir GECIKME PENCERESI — en uzun leak
# sinyali kadar metin her zaman elde tutulur ve birikmis metin her token'da
# taranir, boylece sinyal tamamlandigi anda henuz serbest birakilmamis olur.
# Sinyalin ilk birkac harfinin cikmis olmasi sizinti degil.
_TUTMA_PENCERESI = max(len(s) for s in LEAK_SIGNALS)


class StreamingOutputGuard:
    """output_guard'in akis hali. Kullanim:

        g = StreamingOutputGuard(lang)
        for parca in token_akisi:
            if metin := g.push(parca): yayinla(metin)
            if g.reason: break          # sizinti/uzunluk: akisi kes
        kalan, tam_cevap, reason = g.finish()
    """

    def __init__(self, lang: str = "tr") -> None:
        self.lang = lang
        self.reason: str | None = None
        self._birikmis = ""
        self._yayinlanan = 0

    def push(self, parca: str) -> str:
        if self.reason or not parca:
            return ""
        self._birikmis += parca
        if any(sig in self._birikmis for sig in LEAK_SIGNALS):
            self.reason = "leak"
            return ""
        if len(self._birikmis) > OUTPUT_MAX_LEN:
            self.reason = "truncated"
            return ""
        guvenli = max(len(self._birikmis) - _TUTMA_PENCERESI, 0)
        cikti = self._birikmis[self._yayinlanan:guvenli]
        self._yayinlanan = guvenli
        return cikti

    def finish(self) -> tuple[str, str, str | None]:
        """(yayinlanacak_kalan, loglanacak_tam_cevap, reason).

        Tam cevap yine output_guard'dan geciyor: akis kontrolu yalnizca sizintiya
        ve uzunluga bakiyor, bos cevap ve iteration_limit kontrolleri burada."""
        tam, reason = output_guard(self._birikmis, self.lang)
        if reason is not None:
            # Cevap degistirildi; yayinlanmis metin artik gecersiz. Cagiran
            # "bitti" olayindaki tam cevabi kullanicinin ekranina yazmali.
            return "", tam, reason
        return self._birikmis[self._yayinlanan:], tam, None


_BLOCKED_USER_MESSAGE = {
    "tr": (
        "Üzgünüm, bu konuda yardımcı olamam. Yasin'in projeleri, deneyimi veya yetenekleri "
        "hakkında bir şey sormak ister misin?"
    ),
    "en": (
        "Sorry, I can't help with that. Would you like to ask about Yasin's projects, "
        "experience or skills?"
    ),
}


def blocked_user_message(lang: str = "tr") -> str:
    return _BLOCKED_USER_MESSAGE.get(lang, _BLOCKED_USER_MESSAGE["tr"])


def error_user_message(lang: str = "tr") -> str:
    """Agent/altyapı patladığında kullanıcıya gösterilen metin.

    Bilerek output_guard'ın "boş cevap" metniyle aynı: kullanıcı açısından ikisi de
    "şu an cevap üretemedik" durumu, ayırt etmesi gereken bir fark yok.
    """
    return _OUTPUT_EMPTY_REPLACEMENT.get(lang, _OUTPUT_EMPTY_REPLACEMENT["tr"])
