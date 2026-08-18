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
LEAK_SIGNALS = [
    # Bölüm başlıkları
    "ARAÇ KULLANIM KURALI", "ROL VE AMAÇ", "TEMEL KURALLAR",
    "KARAR AKIŞI", "YASAKLAR", "CEVAP FORMATI", "BAĞLAM ÇÖZÜMLEME",
    "Kapsam Kuralı", "Dürüstlük Kuralı", "Proje Anlatım Kuralı",
    "Pozisyon Uygunluğu Kuralı", "Kişisel Asistan Tonu",
    "Supabase Vector Store1",
    "system prompt", "system message",
    # Kategori bolumleri: baslik veya govdesi tek basina sizarsa da yakalansin
    "### A)", "### B)", "### C)",
    "Tool'u ÇAĞIRMA", "Bu kategoriye giren tipik sorular", "KAPALI bir listedir",
    # Tool'a dair TALİMAT cümleleri (yalın tool adı bilerek yok)
    # "tool'unu çağır" tirnakli/tirnaksiz her iki prompt yazimini da yakalar;
    # korpus ayni tool'dan "tool'unu kullanir" diye bahsettigi icin catismaz.
    "tool'unu çağır", "portfolio_kb çağrılarak",
    "portfolio_kb tool'unu kullanıcının", "call portfolio_kb with",
    # İngilizce dil direktifi bloğu
    "ANSWER LANGUAGE", "OUTPUT LANGUAGE: ENGLISH", "REMINDER BEFORE YOU ANSWER", "Scope rule B", "Scope rule C",
]

_OUTPUT_LEAK_REPLACEMENT = {
    "tr": "Üzgünüm, bu soruyu cevaplayamıyorum.",
    "en": "Sorry, I can't answer that question.",
}
_OUTPUT_EMPTY_REPLACEMENT = {
    "tr": "Üzgünüm, şu an cevap üretemiyorum. Lütfen tekrar deneyin.",
    "en": "Sorry, I can't produce an answer right now. Please try again.",
}
OUTPUT_MAX_LEN = 3000

# Geriye donuk uyumluluk: dil parametresi verilmeyen cagrilar Turkce alir.
OUTPUT_LEAK_REPLACEMENT = _OUTPUT_LEAK_REPLACEMENT["tr"]
OUTPUT_EMPTY_REPLACEMENT = _OUTPUT_EMPTY_REPLACEMENT["tr"]


def output_guard(answer: str, lang: str = "tr") -> tuple[str, str | None]:
    """Return (sanitized_text, reason_if_modified)."""
    text = answer or ""

    if any(s in text for s in LEAK_SIGNALS):
        return _OUTPUT_LEAK_REPLACEMENT.get(lang, OUTPUT_LEAK_REPLACEMENT), "leak"

    if len(text) > OUTPUT_MAX_LEN:
        return text[:OUTPUT_MAX_LEN] + "...", "truncated"

    if not text.strip():
        return _OUTPUT_EMPTY_REPLACEMENT.get(lang, OUTPUT_EMPTY_REPLACEMENT), "empty"

    return text, None


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

BLOCKED_USER_MESSAGE = _BLOCKED_USER_MESSAGE["tr"]


def blocked_user_message(lang: str = "tr") -> str:
    return _BLOCKED_USER_MESSAGE.get(lang, BLOCKED_USER_MESSAGE)
