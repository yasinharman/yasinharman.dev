"""Router'ın LLM'siz kısımları — ağ gerektirmez.

Sınıflandırma DOĞRULUĞU burada ölçülmez; o gerçek model gerektirir ve
`python -m eval.run_routing --router` ile ölçülür (37 vaka, hedef ≥%95).
Buradaki testler şemayı ve LLM'e giden mesajın kurulumunu koruyor.
"""
import pytest
from langchain_core.messages import AIMessage, HumanMessage

from app import router as router_mod
from app.router import Route, _gecmis_metni, classify


def test_route_semasi_uc_alan_tasir():
    """Bu üç alanın varlığı router'ın bütün gerekçesi: bugün aynı kararlar
    250 satırlık prompt'un içinde örtük veriliyor ve dışarı hiç çıkmıyor."""
    alanlar = Route.model_json_schema()["properties"]
    assert set(alanlar) == {"category", "resolved_query", "kb_query"}
    assert alanlar["category"]["enum"] == ["career", "personal", "unrelated", "courtesy"]


def test_gecmissiz_mesaj_acikca_isaretlenir():
    """Model 'geçmiş yok' ile 'geçmiş boş geldi'yi ayırt edebilmeli."""
    assert "ilk mesaj" in _gecmis_metni(None)
    assert "ilk mesaj" in _gecmis_metni([])


def test_gecmis_rolleriyle_birlikte_yazilir():
    metin = _gecmis_metni([HumanMessage(content="yasin kimdir"),
                           AIMessage(content="Yasin bir Python geliştiricisi.")])
    assert "Kullanıcı: yasin kimdir" in metin
    assert "Asistan: Yasin bir Python geliştiricisi." in metin


def test_gecmis_son_n_turla_sinirli():
    """Uzun sohbetlerde router prompt'u sınırsız büyümemeli."""
    uzun = [HumanMessage(content=f"soru {i}") for i in range(20)]
    assert len(_gecmis_metni(uzun, limit=6).splitlines()) == 6


def test_uzun_mesajlar_kirpilir():
    metin = _gecmis_metni([AIMessage(content="x" * 5000)])
    assert len(metin) < 600


class _SahteLLM:
    def __init__(self):
        self.gorulen = None

    def with_structured_output(self, *_a, **_kw):
        return self

    async def ainvoke(self, messages):
        self.gorulen = messages
        return Route(category="career", resolved_query="Yasin kimdir?",
                     kb_query="Yasin kimdir?")


@pytest.fixture
def sahte_llm(monkeypatch):
    llm = _SahteLLM()
    monkeypatch.setattr(router_mod, "router_llm", lambda: llm)
    return llm


async def test_classify_sistem_ve_kullanici_mesaji_gonderir(sahte_llm):
    await classify("yasin kimdir", [HumanMessage(content="merhaba")])

    sistem, kullanici = sahte_llm.gorulen
    assert "SINIFLANDIRICISIN" in sistem.content
    assert "yasin kimdir" in kullanici.content
    assert "Kullanıcı: merhaba" in kullanici.content


async def test_classify_route_dondurur(sahte_llm):
    route = await classify("yasin kimdir")
    assert route.category == "career"
    assert route.kb_query == "Yasin kimdir?"


def test_prompt_kritik_kurallari_tasir():
    """Bunlar canlıda görülmüş hatalardan çıkarılmış kurallar; prompt yeniden
    yazılırken sessizce düşerlerse eval'e kadar fark edilmez."""
    p = router_mod._ROUTER_PROMPT
    assert "Business Data Finder" in p, "çıplak proje adı kuralı düştü"
    assert "YAZIM HATASI" in p, "yazım hatası kuralı düştü"
    assert "İLETİŞİM BİLGİLERİ" in p, "iletişim bilgisi career kuralı düştü"
    # Satir sarmasina takilmasin diye bosluklar normalize edilir.
    duz = " ".join(p.split())
    assert "kapsam reddi DEĞİLDİR" in duz, "'iletişime geçin' bağlam kuralı düştü"
