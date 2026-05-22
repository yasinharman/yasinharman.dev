"""Deterministic input and output guards ported from the n8n Code nodes."""
import re
from pydantic import BaseModel


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
    if len(msg) > 500:
        return GuardVerdict(allowed=False, category="too_long", reason="too_long")

    lower = msg.lower()
    if any(p in lower for p in INJECTION_PATTERNS):
        return GuardVerdict(allowed=False, category="injection", reason="injection")

    if len(_SUSPICIOUS_CHARS_RE.findall(msg)) > 10:
        return GuardVerdict(allowed=False, category="format", reason="format")

    return GuardVerdict(allowed=True, category="ok")


LEAK_SIGNALS = [
    "ARAÇ KULLANIM KURALI", "ROL VE AMAÇ", "TEMEL KURALLAR",
    "Supabase Vector Store1", "portfolio_kb", "KARAR AKIŞI", "YASAKLAR",
    "system prompt", "system message",
    "Kapsam Kuralı", "Dürüstlük Kuralı",
]

OUTPUT_LEAK_REPLACEMENT = "Üzgünüm, bu soruyu cevaplayamıyorum."
OUTPUT_EMPTY_REPLACEMENT = "Üzgünüm, şu an cevap üretemiyorum. Lütfen tekrar deneyin."
OUTPUT_MAX_LEN = 3000


def output_guard(answer: str) -> tuple[str, str | None]:
    """Return (sanitized_text, reason_if_modified)."""
    text = answer or ""

    if any(s in text for s in LEAK_SIGNALS):
        return OUTPUT_LEAK_REPLACEMENT, "leak"

    if len(text) > OUTPUT_MAX_LEN:
        return text[:OUTPUT_MAX_LEN] + "...", "truncated"

    if not text.strip():
        return OUTPUT_EMPTY_REPLACEMENT, "empty"

    return text, None


BLOCKED_USER_MESSAGE = (
    "Üzgünüm, bu konuda yardımcı olamam. Yasin'in projeleri, deneyimi veya yetenekleri "
    "hakkında bir şey sormak ister misin?"
)
