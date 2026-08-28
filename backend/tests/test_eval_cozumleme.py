"""routing eval'inin çözümleme assert'i — eval'in kendisinin testi, ağ yok.

Neden gerekli: bu assert, canlı bir olayın (zamirli takip sorusu → uydurma
e-posta) regresyon korumasıdır. Assert'in kendisi sessizce bozulursa koruma da
gider; üstelik yanlış pozitif üretirse ("This" içindeki "his") eval güvenilmez
hale gelir ve insanlar kırmızıyı görmezden gelmeye başlar.
"""
from dataclasses import dataclass

from eval.run_routing import _cozumleme_kontrolu


@dataclass
class _Route:
    resolved_query: str
    kb_query: str = ""


def test_alan_verilmeyen_vaka_eskisi_gibi_calisir():
    assert _cozumleme_kontrolu({}, _Route("How can I reach him?")) is None


def test_beklenen_parca_varsa_gecer():
    case = {"resolved_contains": ["Yasin"]}
    assert _cozumleme_kontrolu(case, _Route("How can I reach Yasin?")) is None


def test_beklenen_parca_kb_querydeden_de_saglanabilir():
    """Bağlam ikisinden birinde taşınıyorsa yeterli."""
    case = {"resolved_contains": ["Scoring Engine"]}
    route = _Route("Bunu detaylandır", "Yasin'in Scoring Engine botu nedir?")
    assert _cozumleme_kontrolu(case, route) is None


def test_baglam_kaybi_yakalanir():
    case = {"resolved_contains": ["Internship Tracker"]}
    kusur = _cozumleme_kontrolu(case, _Route("İkincisini anlat"))
    assert kusur and "BAGLAM KAYBI" in kusur


def test_kalan_zamir_yakalanir():
    """Olayın tam kendisi: kategori doğru, resolved_query eksik."""
    case = {"resolved_forbids": ["him", "his"]}
    kusur = _cozumleme_kontrolu(case, _Route("How do I reach him?"))
    assert kusur and "ZAMIR KALDI" in kusur


def test_kelime_icindeki_parca_yanlis_pozitif_uretmez():
    """'This' içinde 'his' geçiyor; kelime sınırı olmadan eval güvenilmez olurdu."""
    case = {"resolved_forbids": ["his", "it"]}
    assert _cozumleme_kontrolu(case, _Route("This is Yasin's italian project")) is None


def test_kontrol_buyuk_kucuk_harf_duyarsiz():
    case = {"resolved_contains": ["yasin"], "resolved_forbids": ["HIM"]}
    assert _cozumleme_kontrolu(case, _Route("How can I reach Yasin?")) is None
    kusur = _cozumleme_kontrolu(case, _Route("How can I reach Yasin and him?"))
    assert kusur and "ZAMIR KALDI" in kusur
