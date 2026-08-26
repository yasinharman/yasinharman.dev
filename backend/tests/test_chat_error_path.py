"""/chat hata yolu — ağ ve DB gerektirmez.

Regresyon: agent patladığında (OpenAI 429, Cohere timeout, Supabase kopması)
istek 500 ile bitiyor ve chat_logs'a HİÇBİR satır yazılmıyordu. Yani yalnızca
başarılı istekleri logluyorduk; prod hata oranı tamamen görünmezdi.
"""
import asyncpg
import pytest
from starlette.requests import Request

from app import logging_db
from app.guards import error_user_message
from app.routes.chat import chat
from app.schemas import ChatRequest


async def _yut(*_a, **_kw):
    return None


def _istek(ip: str = "203.0.113.7") -> Request:
    return Request({"type": "http", "method": "POST", "path": "/chat",
                    "headers": [], "client": (ip, 12345)})


class _PatlayanAgent:
    async def ainvoke(self, _payload):
        raise RuntimeError("openai 429")


@pytest.fixture
def patlayan_agent(monkeypatch):
    monkeypatch.setattr("app.routes.chat.agent_executor", lambda lang="tr": _PatlayanAgent())


async def test_agent_patlayinca_kullanici_nazik_metin_alir(patlayan_agent, monkeypatch):
    kayitlar = []

    async def sahte_log_error(session_id, user_message, exc, latency_ms, retrieval=None):
        kayitlar.append((session_id, user_message, type(exc).__name__, retrieval))

    monkeypatch.setattr("app.routes.chat.log_error", sahte_log_error)

    resp = await chat(ChatRequest(message="Yasin kaç yaşında?", session_id="s-hata"), _istek())

    assert resp.response == error_user_message("tr")
    assert resp.blocked is False, "hata bir guard bloğu değil, blocked işaretlenmemeli"
    assert kayitlar == [("s-hata", "Yasin kaç yaşında?", "RuntimeError", None)]


async def test_ingilizce_hata_metni_ingilizce_doner(patlayan_agent, monkeypatch):
    monkeypatch.setattr("app.routes.chat.log_error", _yut)
    resp = await chat(ChatRequest(message="How old is Yasin?", session_id="s-hata-en", lang="en"),
                       _istek())
    assert resp.response == error_user_message("en")


# --- logging_db gerileme yolları ---------------------------------------------
#
# Migration'lar canlıya ELLE uygulanıyor ve main'e push otomatik deploy tetikliyor:
# kod, migration'ından önce canlıda olabilir. Loglama bu durumda satırı kaybetmemeli
# ve hiçbir koşulda isteği patlatmamalı.


class _SahteConn:
    def __init__(self, *, reddet: type[Exception] | None = None):
        self.reddet = reddet
        self.cagrilar: list[tuple[str, tuple]] = []

    async def execute(self, sql, *args):
        self.cagrilar.append((sql, args))
        if self.reddet is asyncpg.exceptions.CheckViolationError and args[1] == "error":
            raise asyncpg.exceptions.CheckViolationError("chat_logs_status_check")
        if self.reddet is asyncpg.exceptions.UndefinedColumnError and "retrieval" in sql:
            raise asyncpg.exceptions.UndefinedColumnError("retrieval")


class _SahtePool:
    def __init__(self, conn):
        self._conn = conn

    def acquire(self):
        conn = self._conn

        class _Ctx:
            async def __aenter__(self):
                return conn

            async def __aexit__(self, *_exc):
                return False

        return _Ctx()


@pytest.fixture
def sahte_db(monkeypatch):
    def kur(**kw):
        conn = _SahteConn(**kw)
        monkeypatch.setattr(logging_db, "persistence_enabled", lambda: True)
        monkeypatch.setattr(logging_db, "pool", lambda: _SahtePool(conn))
        return conn
    return kur


async def test_error_satiri_yazilir(sahte_db):
    conn = sahte_db()
    await logging_db.log_error("s1", "soru", RuntimeError("openai 429"), 120, retrieval=[{"q": "x"}])

    (sql, args), = conn.cagrilar
    assert args[1] == "error"
    assert args[2] == "RuntimeError: openai 429"
    assert args[4] is None, "hata satırında ai_response olmamalı"
    assert "retrieval" in sql, "patlamadan önce getirilen chunk'lar da yazılmalı"


async def test_004_uygulanmadiysa_satir_kaybolmaz(sahte_db):
    """CHECK kısıtı 'error'ü reddediyorsa satır blocked olarak yazılır, atılmaz."""
    conn = sahte_db(reddet=asyncpg.exceptions.CheckViolationError)
    await logging_db.log_error("s1", "soru", TimeoutError("cohere"), 90)

    assert len(conn.cagrilar) == 2, "reddedilen INSERT'ten sonra yeniden denenmedi"
    _, args = conn.cagrilar[-1]
    assert args[1] == "blocked"
    assert args[2] == "error:TimeoutError: cohere", "sebep reason'da korunmalı"


async def test_003_uygulanmadiysa_retrieval_kolonsuz_yazilir(sahte_db):
    conn = sahte_db(reddet=asyncpg.exceptions.UndefinedColumnError)
    await logging_db.log_allowed("s1", "soru", "cevap", 50, retrieval=[{"q": "x"}])

    assert len(conn.cagrilar) == 2
    assert "retrieval" not in conn.cagrilar[-1][0]


async def test_log_yazamamak_istegi_patlatmaz(monkeypatch):
    """DB tamamen erişilemezse bile cevap kullanıcıya gitmeli."""
    monkeypatch.setattr(logging_db, "persistence_enabled", lambda: True)

    def patla():
        raise ConnectionError("pool down")

    monkeypatch.setattr(logging_db, "pool", patla)
    await logging_db.log_allowed("s1", "soru", "cevap", 50)  # yükselmemeli
