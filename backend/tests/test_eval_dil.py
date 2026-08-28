"""Groundedness eval'inin dil kontrolü — ağ yok.

Neden var: İngilizce vakalar yalnızca iddia desteğini ölçüyordu. EN kod yolu
bozulup cevap Türkçe dönse iddialar yine destekli çıkar, eval yeşil yanardı —
vaka korumaya yazıldığı şeyi göremezdi.
"""
import pytest

from eval.run_groundedness import _dil_uyumlu

_EN = "Yasin is a developer and works with Docker in Istanbul."
_TR = "Yasin bir yazılım geliştiricisidir ve İstanbul'da yaşıyor."


def test_ingilizce_cevap_gecer():
    assert _dil_uyumlu(_EN, "en")


def test_turkce_cevap_ingilizce_bekleniyorken_yakalanir():
    assert not _dil_uyumlu(_TR, "en")


@pytest.mark.parametrize("cevap", [_EN, _TR, ""])
def test_turkce_vakada_kontrol_yapilmaz(cevap):
    """lang=tr vakalarda kontrol devreye girmemeli; aksi halde mevcut 13 vaka
    ölçtükleri şeyden başka bir sebeple kırmızı yanardı."""
    assert _dil_uyumlu(cevap, "tr")


def test_turkce_proje_adi_yanlis_pozitif_uretmez():
    """Korpustaki proje adları Türkçe ve İngilizce cevapta AYNEN aktarılıyor —
    bu doğru davranış. Negatif kontrol (Türkçe sözcük arama) tam burada yanlış
    pozitif üretmişti; kontrol bu yüzden pozitif tarafta."""
    cevap = ("The second project is Internship Tracker — Uçtan Uca Otomatize "
             "İş İlanı ETL ve Dashboard Sistemi, built with n8n.")
    assert _dil_uyumlu(cevap, "en")


def test_cok_kisa_ingilizce_cevap_esigi_gecemez():
    """Üç ayrı işlev sözcüğü şartı bilinçli: tek 'is' geçen bir Türkçe cümle
    (örn. 'Bu is ile ilgili') eşiği geçmemeli."""
    assert not _dil_uyumlu("Docker.", "en")
    assert not _dil_uyumlu("Yasin Harman is.", "en")
