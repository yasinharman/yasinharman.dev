"""/chat/stream — SSE olay akışı.

/chat ile /chat/stream aynı üreticiden besleniyor; testler o üreticinin
sözleşmesini sabitliyor: "bitti" HER ZAMAN son olay ve tam cevabı taşır."""
import json

import pytest

from app.router import Route
from app.routes.chat import chat, chat_stream
from app.schemas import ChatRequest


class _Istek:
    def __init__(self, ip="203.0.113.7"):
        self.headers = {"cf-connecting-ip": ip}
        self.client = type("c", (), {"host": ip})()


class _AkanAgent:
    def __init__(self, parcalar):
        self._parcalar = parcalar

    async def astream_events(self, _payload, version=None):
        for p in self._parcalar:
            yield {"event": "on_chat_model_stream",
                   "data": {"chunk": type("P", (), {"content": p})()}}
        # Akista ilgilenmedigimiz olay tipleri de geliyor; suzguc calismali.
        yield {"event": "on_chain_end", "data": {}}


@pytest.fixture
def kariyer_yolu(monkeypatch):
    def kur(parcalar):
        async def sahte_classify(message, history=None):
            return Route(category="career", resolved_query=message, kb_query=message)

        async def sahte_context(kb_query):
            return []

        monkeypatch.setattr("app.routes.chat.classify", sahte_classify)
        monkeypatch.setattr("app.routes.chat.initial_context", sahte_context)
        monkeypatch.setattr("app.routes.chat.agent_executor",
                            lambda lang="tr": _AkanAgent(parcalar))
    return kur


async def _olaylar(resp) -> list[dict]:
    out = []
    async for parca in resp.body_iterator:
        for satir in parca.strip().split("\n\n"):
            if satir.startswith("data: "):
                out.append(json.loads(satir[len("data: "):]))
    return out


async def test_kariyer_yolunda_asama_sonra_token_sonra_bitti(kariyer_yolu):
    kariyer_yolu(["Yasin ", "Python ", "biliyor." + "x" * 200])
    resp = await chat_stream(ChatRequest(message="Yasin ne biliyor?", session_id="s1"),
                             _Istek())
    olaylar = await _olaylar(resp)

    tipler = [o["tip"] for o in olaylar]
    assert tipler[0] == "asama", "ilk olay aşama olmalı — ekranın boş kalmaması bu"
    assert tipler[-1] == "bitti", "bitti her zaman son olay"
    assert "token" in tipler

    asamalar = [o["asama"] for o in olaylar if o["tip"] == "asama"]
    assert asamalar == ["yonlendiriliyor", "araniyor", "bulundu"]

    yayinlanan = "".join(o["metin"] for o in olaylar if o["tip"] == "token")
    assert yayinlanan == olaylar[-1]["cevap"], "akan metin ile tam cevap ayrışmamalı"


async def test_sse_bicimi_ve_tampon_kapatma_basligi(kariyer_yolu):
    kariyer_yolu(["merhaba"])
    resp = await chat_stream(ChatRequest(message="Yasin kimdir?", session_id="s2"),
                             _Istek())
    assert resp.media_type == "text/event-stream"
    # nginx proxy cevaplarini tamponluyor; tamponlanan SSE tek parca cevaba doner.
    assert resp.headers["x-accel-buffering"] == "no"


async def test_nezaket_yolunda_tek_bitti_olayi(kariyer_yolu):
    kariyer_yolu(["kullanilmayacak"])
    resp = await chat_stream(ChatRequest(message="merhaba", session_id="s3"), _Istek())
    olaylar = await _olaylar(resp)

    assert [o["tip"] for o in olaylar] == ["bitti"], "LLM'e hiç gidilmeden kapanmalı"
    assert olaylar[0]["engellendi"] is False
    assert olaylar[0]["cevap"]


async def test_akissiz_yol_ayni_cevabi_uretir(kariyer_yolu):
    """/chat ile /chat/stream tek üreticiden besleniyor; ayrışırlarsa iki ayrı
    davranış bakımı gerekir ve bu sıra üç canlı bug'ın kaynağıydı."""
    kariyer_yolu(["tek ", "parça ", "cevap"])
    resp = await chat(ChatRequest(message="Yasin ne biliyor?", session_id="s4"), _Istek())
    assert resp.response == "tek parça cevap"
    assert resp.blocked is False
