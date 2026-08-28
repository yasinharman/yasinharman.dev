"""initial_context'in genişletme notu — deterministik kısmın testi.

Notun cevabı gerçekten düzeltip düzeltmediği burada ölçülemez (model çağrısı
gerekir, üstelik sonuç rastlantısal): o `eval/run_kapsayici.py`'nin işi.
Burada test edilen şey, notun DOĞRU KOŞULDA eklenip eklenmediği.
"""
import asyncio

from langchain_core.documents import Document

from app import agent as agent_modulu


def _kur(monkeypatch, docs):
    async def sahte_arama(query):
        return docs
    monkeypatch.setattr(agent_modulu, "kb_search", sahte_arama)


def _context_metni(monkeypatch, docs) -> str:
    _kur(monkeypatch, docs)
    mesajlar = asyncio.run(agent_modulu.initial_context("projeler"))
    # [0] her zaman tarih mesajı; bağlam ikincisi.
    return mesajlar[1].content


def test_genisletme_varsa_not_eklenir(monkeypatch):
    """Özet bölümünü kopyalayıp durmanın panzehiri; koşulu _expand_overviews
    zaten deterministik olarak işaretliyor (expanded_from)."""
    docs = [
        Document(page_content="Projelerin Listesi", metadata={"source": "projeler.md"}),
        Document(page_content="Detay 1",
                 metadata={"source": "projeler.md", "expanded_from": "projeler.md"}),
    ]
    metin = _context_metni(monkeypatch, docs)
    assert agent_modulu._GENISLETME_NOTU.strip() in metin
    assert metin.index("Detay 1") < metin.index("NOT:"), "not, bölümlerin SONUNA gelmeli"


def test_genisletme_yoksa_not_eklenmez(monkeypatch):
    """Dar sorularda not gereksiz; her turda taşımak bağlamı sulandırır."""
    docs = [Document(page_content="Yasin 23 yaşında.", metadata={"source": "hakkimda.md"})]
    metin = _context_metni(monkeypatch, docs)
    assert "NOT:" not in metin


def test_bos_sonuc_notsuz_gecer(monkeypatch):
    metin = _context_metni(monkeypatch, [])
    assert "Sonuç bulunamadı." in metin
    assert "NOT:" not in metin


def test_kb_query_yoksa_yalnizca_tarih_doner(monkeypatch):
    _kur(monkeypatch, [])
    mesajlar = asyncio.run(agent_modulu.initial_context(""))
    assert len(mesajlar) == 1 and "tarih" in mesajlar[0].content.lower()
