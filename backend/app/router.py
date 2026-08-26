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
from typing import Literal

from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from .deps import router_llm

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


# ---------------------------------------------------------------------------
# LLM sınıflandırma (FAZ 3.1)
# ---------------------------------------------------------------------------

_ROUTER_PROMPT = """Sen bir SINIFLANDIRICISIN. Cevap ÜRETMİYORSUN.

Yasin Harman'ın portfolyo asistanına gelen mesajı üç alana ayırıyorsun.

# KATEGORİLER

career — Yasin'in kariyeri, profili veya kim olduğu.
  Projeler, yetenekler, teknolojiler, iş deneyimi, freelance işleri, eğitim, pozisyon
  uygunluğu, iletişim bilgileri, konuştuğu diller, hobileri, yaşadığı şehir, YAŞI,
  soft skill'leri, çalışma tarzı; "Yasin kim / kimdir / kendini tanıt" tanıtım soruları.
  Bilgi tabanındaki her biyografik bilgi buraya girer.

personal — Yasin'in kariyer dışı özel hayatı. Bu KAPALI bir listedir, SADECE şunlar:
  zevkleri (en sevdiği yemek / renk / müzik / film / takım), ilişki ve aile durumu,
  sağlığı, dini görüşü, siyasi görüşü, fiziksel özellikleri (boy, kilo, görünüş).
  Bu listede OLMAYAN hiçbir şeyi personal yapma. Özellikle İLETİŞİM BİLGİLERİ
  (e-posta, telefon, LinkedIn, GitHub, konum) bu listede YOKTUR → career'dır;
  "özel bilgi" gibi durmaları onları personal yapmaz.

unrelated — Yasin hakkında hiç değil: hava durumu, genel kültür, matematik, kod
  yazdırma, çeviri, başka kişiler, haberler, hakaret, anlamsız test mesajları.

courtesy — sadece selamlama veya teşekkür; içinde soru yok.

# EN SIK YAPILAN HATA — DİKKAT

Bir ÖZEL AD (proje, ürün, araç, şirket, teknoloji adı) geçiyorsa ve mesaj başka bir
kişiden bahsetmiyorsa, bu Yasin'in projesi veya deneyimi hakkındadır → **career**.
Adı tanımıyor olman onu unrelated yapmaz; bilgi tabanında olup olmadığına SEN karar
veremezsin, bunu arama belirler.
  "Business Data Finder nedir" → career
  "Jarvis nedir" → career
  "Internship Tracker hangi tur ilanlari topluyor" → career

YAZIM HATASI KATEGORİ DEĞİŞTİRMEZ. Kullanıcılar hızlı ve hatalı yazar:
"nwrde" = nerede, "bhaset" = bahset, "okusdu" = okudu, "geçicem" = geçeceğim.
Bir kelimeyi çözemediysen mesajı unrelated'a atma; kalan kelimelerden konuyu çıkar.
  "Liseyi nwrde okudu nasıl okusdu" → career (eğitim sorusu)

Aynı şekilde: kimseden isim vermeden sorulan her şey Yasin hakkında sorulmuş sayılır.
  "kaç yıldır çalışıyor" → career     "hobileri nedir" → career

Bilgi tabanında cevabın olmayacağını düşünmek unrelated/personal sebebi DEĞİLDİR.
Kariyerle ilgili ama bilgi olmayabilecek sorular (maaş beklentisi gibi) yine career'dır;
arama boş dönerse dürüst cevabı bir sonraki adım verir.

# ALANLAR

resolved_query — Kullanıcının GERÇEKTE sorduğu tam soru.
  Mesaj eksik, zamirli veya bir öncekine bağlıysa ("peki ya", "o zaman", "nasıl",
  "bunu detaylandır") konuşma geçmişiyle birleştirip tam soruyu yeniden kur.
  Mesaj zaten tamsa olduğu gibi bırak.
  ASLA cevabı buraya yazma — burası her zaman bir SORU kalır.

kb_query — Aramaya gidecek sorgu. HER ZAMAN TÜRKÇE tam cümle, mesaj İngilizce olsa bile.
  Tek kelimelik anahtar kelime yazma: "hobiler" değil "Yasin'in hobileri nelerdir?".
  career dışındaki kategorilerde boş string bırak.

# GEÇMİŞ

Konuşma geçmişi başka dilde olabilir; bu sınıflandırmayı DEĞİŞTİRMEZ.
Kısa veya zamirli bir takip sorusu, devam ettiği turun kategorisinde KALIR — kısalık
bir soruyu personal veya unrelated yapmaz.
Ama önceki tur bir KAPSAM REDDİ ise ("sadece Yasin hakkındaki soruları cevaplamak
için eğitildim" gibi) veya kullanıcı açıkça yeni bir konuya geçtiyse, eski bağlamı
zorlama; yeni mesajı kendi içeriğine göre sınıflandır.

DİKKAT: "Bu konuda elimde bilgi yok, Yasin ile iletişime geçebilirsiniz" bir kapsam
reddi DEĞİLDİR — kariyer sorusuna verilmiş dürüst bir cevaptır. Ardından gelen
"nasıl geçicem / nasıl ulaşırım / nereden" sorusu Yasin'in İLETİŞİM BİLGİLERİNİ
istiyor demektir → career, kb_query = "Yasin'in iletişim bilgileri nelerdir?"."""


class Route(BaseModel):
    """Router'ın açık çıktısı — loglanabilir, test edilebilir, ölçülebilir.

    Bugün bu üç değer 250 satırlık SYSTEM_PROMPT'un içinde örtük olarak üretiliyor
    ve dışarı hiç çıkmıyor: modelin takip sorusunu doğru çözüp çözmediğini
    göremiyor, kategoriyi loglayamıyor, hiçbirini test edemiyoruz.
    """

    category: Literal["career", "personal", "unrelated", "courtesy"]
    resolved_query: str = Field(description="Kullanıcının gerçekte sorduğu tam soru")
    kb_query: str = Field(default="", description="Aramaya gidecek Türkçe cümle")


def _gecmis_metni(history: list[BaseMessage] | None, limit: int = 6) -> str:
    if not history:
        return "(geçmiş yok — bu ilk mesaj)"
    satirlar = []
    for m in history[-limit:]:
        rol = "Kullanıcı" if isinstance(m, HumanMessage) else "Asistan"
        satirlar.append(f"{rol}: {str(m.content)[:400]}")
    return "\n".join(satirlar)


async def classify(message: str, history: list[BaseMessage] | None = None) -> Route:
    """Mesajı sınıflandırır. Tek LLM çağrısı, structured output, temperature=0."""
    llm = router_llm().with_structured_output(Route, method="json_schema", strict=True)
    return await llm.ainvoke([
        SystemMessage(content=_ROUTER_PROMPT),
        HumanMessage(content=(
            f"# KONUŞMA GEÇMİŞİ\n{_gecmis_metni(history)}\n\n"
            f"# SINIFLANDIRILACAK YENİ MESAJ\n{message}"
        )),
    ])
