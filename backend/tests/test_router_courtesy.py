"""Selamlama/teşekkür sınıflandırması — ağ gerektirmez.

Regresyon: temiz bir oturumda ilk mesaj "merhaba" yazan ziyaretçi
"Üzgünüm, sadece Yasin hakkındaki soruları cevaplamak için eğitildim." alıyordu.
Aynı kelime sohbetin ortasında nazikçe karşılanıyordu — sınıflandırma kelimeye
değil bağlama bakıyordu (2026-08-26, canlıda doğrulandı).
"""
import pytest

from app.router import courtesy_reply


@pytest.mark.parametrize("mesaj", [
    "merhaba", "Merhaba", "MERHABA", "merhaba!", "  merhaba  ",
    "selam", "selamlar", "Selam!", "iyi günler", "günaydın",
    "nasılsın", "naber", "selam nasılsın",
    "hi", "Hello", "good morning",
])
def test_selamlama_karsilanir(mesaj):
    cevap = courtesy_reply(mesaj, "tr")
    assert cevap is not None, f"{mesaj!r} selamlama olarak tanınmadı"
    assert "ne öğrenmek istersiniz" in cevap


@pytest.mark.parametrize("mesaj", [
    "teşekkürler", "Teşekkürler!", "teşekkür ederim", "çok teşekkürler",
    "sağol", "sağ ol", "eyvallah",
    # Turkce karakter kullanmadan yazanlar ayni yere dusmeli
    "tesekkurler", "tesekkur ederim", "sagol",
    "thanks", "thank you",
])
def test_tesekkur_karsilanir(mesaj):
    cevap = courtesy_reply(mesaj, "tr")
    assert cevap is not None, f"{mesaj!r} teşekkür olarak tanınmadı"
    assert "Rica ederim" in cevap


@pytest.mark.parametrize("mesaj", [
    # Selamlama İÇEREN ama asıl soru olan mesajlar normal akışa gitmeli.
    "merhaba, Yasin hakkında bilgi almak istiyorum",
    "selam, projelerinden bahseder misin",
    "iyi günler, hangi teknolojileri biliyor?",
    "teşekkürler ama hobilerini de anlatır mısın",
    # Gerçek sorular
    "yasin kimdir",
    "Business Data Finder nedir",
    "hobileri nedir",
    "hava kaç derece",
])
def test_gercek_sorular_normal_akisa_gider(mesaj):
    assert courtesy_reply(mesaj, "tr") is None, f"{mesaj!r} yanlışlıkla nezaket sayıldı"


def test_ingilizce_cevap_ingilizce():
    assert "What would you like to know" in courtesy_reply("hello", "en")
    assert "You're welcome" in courtesy_reply("thanks", "en")


def test_bos_mesaj_none_doner():
    for m in ("", "   ", "!!!", None):
        assert courtesy_reply(m, "tr") is None


@pytest.mark.parametrize("mesaj", [
    "teşşekkürler",   # gercek kullanici logundan: cift s
    "teşşekkürler!",
    "çok teşşekkür ederim",
    "iyi günler",
    "merhaba iyi günler",
    "eyvallah kardeşim",
    "thank you very much",
])
def test_yazim_varyasyonlari_kacmaz(mesaj):
    """Tam cümle listesi tutuluyordu ve gerçek bir kullanıcının 'teşşekkürler'
    yazımı listeden kaçıyordu. Kelime bazlı eşleşme bunu kapatır."""
    assert courtesy_reply(mesaj, "tr") is not None, f"{mesaj!r} kaçtı"


@pytest.mark.parametrize("mesaj", [
    "çok",
    "iyi",
    "tekrar",
])
def test_sadece_dolgu_kelime_nezaket_sayilmaz(mesaj):
    assert courtesy_reply(mesaj, "tr") is None


def test_uzun_mesaj_nezaket_sayilmaz():
    """Altı kelimeden uzunu artık bir cümledir, nezaket mesajı değil."""
    assert courtesy_reply("merhaba selam iyi günler nasılsın naber ne haber", "tr") is None


@pytest.mark.parametrize("mesaj", [
    "how?",           # takip sorusu: "nasil ulasirim?" demek
    "how",
    "nasıl?",
    "ne?",
])
def test_tek_kelimelik_takip_sorusu_selamlama_sayilmaz(mesaj):
    """Regresyon: "how are you"yu desteklemek için how/are/you kelimeleri tek tek
    selamlama kümesine konmuştu; çıplak "how?" de oraya düşüyordu. Sonuç: takip
    sorusu olarak "how?" yazan kullanıcı "Hello! What would you like to know about
    Yasin?" alıyor, gerçek sorusu hiç cevaplanmıyordu."""
    assert courtesy_reply(mesaj, "en") is None, f"{mesaj!r} selamlama sayıldı"


@pytest.mark.parametrize("mesaj", ["how are you", "How are you?", "nasıl gidiyor"])
def test_cok_kelimeli_selamlama_ifadeleri_tanınır(mesaj):
    assert courtesy_reply(mesaj, "tr") is not None
