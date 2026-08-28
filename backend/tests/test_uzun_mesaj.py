"""Çok uzun mesaj — kullanıcıya doğru gerekçe, DB'ye bir satır.

Regresyon (2026-08-28): şemadaki `max_length` MAX_INPUT_LENGTH ile aynıydı (1000),
bu yüzden 1000'i aşan her mesaj FastAPI doğrulamasında 422 oluyor ve route'a hiç
girmiyordu. Üç sonucu vardı: `input_guard`'ın `too_long` dalı ölü koddu, olay
`chat_logs`'a hiç yazılmıyordu ve kullanıcı "lütfen tekrar deneyin" diyen yanlış
bir mesaj görüyordu — mesajı kısaltması gerektiğini söyleyen yoktu.
"""
import asyncio

import pytest
from starlette.requests import Request

from app.guards import blocked_user_message
from app.routes.chat import chat
from app.schemas import ChatRequest


def _istek() -> Request:
    return Request({"type": "http", "method": "POST", "path": "/chat",
                    "headers": [], "client": ("203.0.113.7", 12345)})


def test_semada_guardin_calisacagi_alan_var():
    """Şema sınırı MAX_INPUT_LENGTH'ten geniş olmazsa guard'a sıra gelmez."""
    from app.config import get_settings
    sinir = ChatRequest.model_fields["message"].metadata
    en_fazla = next(m.max_length for m in sinir if hasattr(m, "max_length"))
    assert en_fazla > get_settings().MAX_INPUT_LENGTH


def test_uzun_mesaj_dogru_gerekceyle_loglanir(monkeypatch):
    yazilan = {}

    async def sahte_blocked(session_id, user_message, reason, latency_ms, **kw):
        yazilan.update(reason=reason, session_id=session_id)

    monkeypatch.setattr("app.routes.chat.log_blocked", sahte_blocked)

    req = ChatRequest(message="A" * 1500, session_id="uzun-test")
    cevap = asyncio.run(chat(req, _istek()))

    assert yazilan["reason"] == "too_long", "olay chat_logs'a bu gerekçeyle düşmeli"
    assert cevap.blocked is True
    assert cevap.response == blocked_user_message("tr", "too_long")


@pytest.mark.parametrize("lang", ["tr", "en"])
def test_uzunluk_mesaji_kapsam_reddinden_farkli(lang):
    """Kapsam reddi 'Yasin'in projelerini sorabilirsin' diyor; uzun bir mesaja
    verildiğinde kullanıcıyı yanıltıyor — sorun konu değil, uzunluk."""
    uzunluk = blocked_user_message(lang, "too_long")
    kapsam = blocked_user_message(lang)
    assert uzunluk != kapsam
    assert uzunluk == blocked_user_message(lang, "too_long")


def test_bilinmeyen_gerekce_kapsam_reddine_duser():
    assert blocked_user_message("tr", "injection") == blocked_user_message("tr")
    assert blocked_user_message("tr", None) == blocked_user_message("tr")
