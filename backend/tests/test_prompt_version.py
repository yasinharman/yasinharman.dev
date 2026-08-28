"""Prompt sürümü — 'geçen hafta daha iyi cevap veriyordu' sorusunu DB'den
cevaplayabilmek için. Değer opak; neyin değil, DEĞİŞTİĞİNİ söyler."""
import app.version as version_modulu
from app.version import prompt_version


def _taze() -> str:
    prompt_version.cache_clear()
    return prompt_version()


def test_kararli():
    assert _taze() == _taze()
    assert len(_taze()) == 12


def test_system_prompt_degisince_degisir(monkeypatch):
    once = _taze()
    monkeypatch.setattr(version_modulu, "SYSTEM_PROMPT",
                        version_modulu.SYSTEM_PROMPT + " ")
    assert _taze() != once, "tek boşluk bile sürümü oynatmalı"


def test_router_prompt_degisince_de_degisir(monkeypatch):
    """Yalnızca SYSTEM_PROMPT hash'lenseydi 3.1'den beri yapılan değişikliklerin
    çoğu (router prompt'u) sürümü hiç oynatmazdı."""
    once = _taze()
    monkeypatch.setattr(version_modulu, "ROUTER_PROMPT",
                        version_modulu.ROUTER_PROMPT + " ")
    assert _taze() != once


def test_model_degisince_de_degisir(monkeypatch):
    """Aynı prompt, farklı model = farklı davranış. Sürüm bunu da kapsamalı."""
    once = _taze()
    s = version_modulu.get_settings()
    monkeypatch.setattr(s, "OPENAI_CHAT_MODEL", s.OPENAI_CHAT_MODEL + "-x")
    assert _taze() != once
    prompt_version.cache_clear()


def test_tur_baglami_degisince_de_degisir(monkeypatch):
    """2026-08-28'de _GENISLETME_NOTU eklendi ve kopya cevap oranı %28'den %0'a
    düştü — davranış ölçülebilir şekilde değişti ama sürüm aynı kalmıştı. Parmak
    izi böyle bir deploy'u kaçırırsa var olma sebebini kaybediyor."""
    once = _taze()
    monkeypatch.setattr(version_modulu, "_GENISLETME_NOTU",
                        version_modulu._GENISLETME_NOTU + " ")
    assert _taze() != once


def test_baglam_onsozu_degisince_de_degisir(monkeypatch):
    once = _taze()
    monkeypatch.setattr(version_modulu, "_BAGLAM_ONSOZU",
                        version_modulu._BAGLAM_ONSOZU + " ")
    assert _taze() != once
