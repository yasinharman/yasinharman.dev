"""Sınıflandırmanın deterministik kısmı.

Bugün kapsam kararı 250 satırlık SYSTEM_PROMPT'un içinde veriliyor ve dışarı hiçbir
değer vermiyor: ne loglanabiliyor ne test edilebiliyor. FAZ 3.1 bunu LLM tabanlı bir
router'a taşıyacak; bu dosya o taşımanın ilk parçası — LLM'e hiç gerek olmayan kısım.

Selamlama ve teşekkür buraya ait çünkü sabit bir kelime kümesi; bunun için model
çağırmak hem para hem gecikme, üstelik güvenilir de değildi: canlıda temiz bir
oturumda ilk mesaj "merhaba" yazan ziyaretçi
"Üzgünüm, sadece Yasin hakkındaki soruları cevaplamak için eğitildim." alıyordu
(2026-08-26 doğrulaması). Geçmiş VARKEN aynı kelime nazikçe karşılanıyordu, yani
sınıflandırma kelimeye değil bağlama bakıyordu.

Eşleşme mesajın TAMAMI üzerinden yapılır: "merhaba, Yasin hakkında bilgi almak
istiyorum" buraya DÜŞMEZ, normal akışa gider.
"""
import re
import unicodedata

# Eslesme KELIME BAZLI: mesajin butun kelimeleri bu kumelerde geciyorsa nezaket
# mesajidir. Tam cumle listesi tutmak yazim hatalarinda kiriliyordu — gercek bir
# kullanici "teşşekkürler" yazmisti (cift s) ve liste onu kaciriyordu. Kelime bazli
# olunca yeni bir yazim eklemek tek kelime eklemek demek.
#
# Ayni zamanda guvenli tarafta: mesajda kumelerin disindan TEK bir kelime bile
# varsa nezaket sayilmaz. "merhaba, Yasin hakkinda bilgi almak istiyorum" buraya
# dusmez cunku "yasin", "hakkinda" ... kumede yok.

_SELAMLAMA_KELIMELERI = {
    "merhaba", "merhabalar", "selam", "selamlar", "selamun", "aleykum",
    "gunaydin", "gunler", "aksamlar", "geceler", "sabahlar",
    "nasilsin", "nasilsiniz", "naber", "haber", "hosgeldin",
    "hi", "hey", "hello", "morning", "evening", "how", "are", "you",
}

_TESEKKUR_KELIMELERI = {
    "tesekkur", "tesekkurler", "tesekkurederim",
    # cift s ile yazan gercek kullanici loglarda var
    "tessekkur", "tessekkurler",
    "sagol", "sagolun", "sag", "ol", "eyvallah", "ellerine", "saglik",
    "thanks", "thank", "thx", "cheers",
}

# Tek baslarina anlam tasimayan, iki kumeyle birlikte gelebilen kelimeler.
_DOLGU_KELIMELERI = {
    "ederim", "iyi", "cok", "tekrar", "ya", "be", "de", "da", "ve",
    "kardesim", "hocam", "abi", "canim",
    "very", "much", "so", "a", "lot", "good", "day",
}

_MAX_KELIME = 6  # daha uzunu artik bir nezaket mesaji degil, cumledir

_SELAMLAMA_CEVABI = {
    "tr": "Merhaba! Yasin hakkında ne öğrenmek istersiniz?",
    "en": "Hello! What would you like to know about Yasin?",
}
_TESEKKUR_CEVABI = {
    "tr": "Rica ederim! Yasin hakkında başka merak ettiğiniz bir şey olursa sorabilirsiniz.",
    "en": "You're welcome! Feel free to ask anything else about Yasin.",
}

_TEMIZ_RE = re.compile(r"[^a-z0-9\s]")
_BOSLUK_RE = re.compile(r"\s+")


def _normalize(message: str) -> str:
    """Türkçe aksanları ve noktalama işaretlerini düşürüp karşılaştırılabilir hale getirir.

    "Teşekkürler!!!" → "tesekkurler". Kullanıcıların önemli bir kısmı Türkçe karakter
    kullanmadan yazıyor ("tesekkurler"), iki yazım da aynı yere düşmeli.

    'ı' bilerek elle çevriliyor: ayrı bir harf olduğu için NFKD onu ayrıştırmaz,
    dolayısıyla "nasılsın" ile "nasilsin" aksi halde eşleşmezdi.
    """
    text = (message or "").strip().lower().replace("ı", "i")
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = _TEMIZ_RE.sub(" ", text)
    return _BOSLUK_RE.sub(" ", text).strip()


def courtesy_reply(message: str, lang: str = "tr") -> str | None:
    """Mesaj tek başına bir selamlama/teşekkürse hazır cevabı, değilse None döner.

    None dönmesi "normal akışa devam et" demektir; çağıran taraf agent'ı çalıştırır.
    """
    kelimeler = _normalize(message).split()
    if not kelimeler or len(kelimeler) > _MAX_KELIME:
        return None

    tanidik = _SELAMLAMA_KELIMELERI | _TESEKKUR_KELIMELERI | _DOLGU_KELIMELERI
    if not all(k in tanidik for k in kelimeler):
        return None

    # Tesekkur once bakilir: "cok tesekkurler" hem dolgu hem tesekkur iceriyor,
    # "iyi gunler tesekkurler" gibi karisik mesajlarda da kapanis niyeti agir basar.
    if any(k in _TESEKKUR_KELIMELERI for k in kelimeler):
        return _TESEKKUR_CEVABI.get(lang, _TESEKKUR_CEVABI["tr"])
    if any(k in _SELAMLAMA_KELIMELERI for k in kelimeler):
        return _SELAMLAMA_CEVABI.get(lang, _SELAMLAMA_CEVABI["tr"])
    return None  # yalnizca dolgu kelimeler ("cok", "iyi") — nezaket sayilmaz
