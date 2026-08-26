"""/admin/ingest-path yol kısıtı — ağ gerektirmez.

Regresyon: IngestPathRequest.path doğrudan Path()'e gidiyordu. Admin key sızarsa
saldırgan sunucudaki her .md/.txt/.pdf/.docx'i vektör DB'ye yazıp chatbot üzerinden
okuyabilirdi — key sızıntısı bir dosya okuma primitifine dönüşüyordu.
"""
import pytest
from fastapi import HTTPException

from app.ingest import DATA_ROOT
from app.routes.admin import _resolve_data_path
from app.schemas import IngestPathRequest


@pytest.mark.parametrize("yol", [
    "/etc",
    "/etc/passwd",
    "~/.ssh/id_rsa",
    "../.env",
    "data/../../.env",
    "/app/.env",
])
def test_data_disi_yollar_reddedilir(yol):
    with pytest.raises(HTTPException) as exc:
        _resolve_data_path(yol)
    assert exc.value.status_code == 400


@pytest.mark.parametrize("yol", [
    "data",
    "data/projeler.md",
    "data/../data/projeler.md",
])
def test_data_altindaki_yollar_kabul_edilir(yol, monkeypatch):
    # Göreli yollar CWD'ye göre çözülür; testin nereden koşulduğuna bağlı kalmasın.
    monkeypatch.chdir(DATA_ROOT.parent)
    assert _resolve_data_path(yol).is_relative_to(DATA_ROOT.resolve())


def test_mutlak_data_yolu_kabul_edilir():
    hedef = DATA_ROOT / "projeler.md"
    assert _resolve_data_path(str(hedef)) == hedef.resolve()


def test_data_kokunun_kendisi_kabul_edilir():
    assert _resolve_data_path(str(DATA_ROOT)) == DATA_ROOT.resolve()


def test_data_ile_ayni_onekli_kardes_dizin_reddedilir():
    """String prefix kontrolü olsaydı backend/data-yedek/ kaçardı; is_relative_to kaçırmaz."""
    with pytest.raises(HTTPException):
        _resolve_data_path(str(DATA_ROOT) + "-yedek/gizli.md")


def test_wipe_http_yuzeyinden_kaldirildi():
    """Tüm korpusu silmek yalnızca CLI'da kalmalı: sızmış bir key tek istekle
    vektör DB'yi silememeli. Pydantic bilinmeyen alanı sessizce yutarsa bu
    testin görevi onu yakalamak."""
    body = IngestPathRequest.model_validate({"path": "data", "wipe": True})
    assert not hasattr(body, "wipe")
