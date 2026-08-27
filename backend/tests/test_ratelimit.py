"""Rate limit birim testleri — sahte saat kullanır, ağ ve bekleme yok."""
import pytest
from starlette.requests import Request

from app.ratelimit import RateLimiter, client_ip


def _istek(headers: list[tuple[bytes, bytes]] | None = None,
           client: tuple[str, int] | None = ("10.0.0.1", 1234)) -> Request:
    return Request({"type": "http", "method": "POST", "path": "/chat",
                    "headers": headers or [], "client": client})


def test_dakika_limiti_ip_basina_uygulanir():
    limiter = RateLimiter(per_min=20, per_day=100)
    sonuclar = [limiter.check("1.2.3.4", "s1", now=1000.0 + i * 0.1) for i in range(25)]

    assert all(v.allowed for v in sonuclar[:20]), "ilk 20 istek geçmeliydi"
    assert not any(v.allowed for v in sonuclar[20:]), "21. istekten sonrası 429 olmalı"
    assert sonuclar[20].reason == "rate_limit_ip"
    assert sonuclar[20].retry_after > 0


def test_pencere_kayinca_kota_geri_gelir():
    limiter = RateLimiter(per_min=2, per_day=100)
    assert limiter.check("1.2.3.4", "s1", now=1000.0).allowed
    assert limiter.check("1.2.3.4", "s1", now=1001.0).allowed
    assert not limiter.check("1.2.3.4", "s1", now=1002.0).allowed
    # ilk vuruş 60 sn geride kaldı → yeniden yer açıldı
    assert limiter.check("1.2.3.4", "s1", now=1061.0).allowed


def test_farkli_ipler_birbirinin_kotasini_tuketmez():
    limiter = RateLimiter(per_min=2, per_day=100)
    for i in range(2):
        assert limiter.check("1.1.1.1", "s1", now=1000.0 + i).allowed
    assert not limiter.check("1.1.1.1", "s1", now=1003.0).allowed
    assert limiter.check("2.2.2.2", "s2", now=1003.0).allowed


def test_gunluk_limit_session_basina_uygulanir():
    """IP değişse bile aynı session_id günlük kotayı aşamaz."""
    limiter = RateLimiter(per_min=1000, per_day=3)
    for i in range(3):
        assert limiter.check(f"10.0.0.{i}", "aynı-session", now=1000.0 + i).allowed
    verdict = limiter.check("10.0.0.9", "aynı-session", now=1010.0)
    assert not verdict.allowed
    assert verdict.reason == "rate_limit_session"


def test_dbye_pencere_basina_yalnizca_ilk_red_yazilir():
    """Aksi halde bir flood, kendisini sınırsız chat_logs yazımına çevirirdi."""
    limiter = RateLimiter(per_min=1, per_day=100)
    assert limiter.check("1.2.3.4", "s1", now=1000.0).allowed

    redler = [limiter.check("1.2.3.4", "s1", now=1000.0 + i) for i in range(1, 30)]
    assert not any(v.allowed for v in redler)
    assert sum(v.should_log for v in redler) == 1, "her red için DB'ye yazılıyor"


def test_eski_anahtarlar_temizlenir():
    """Sözlük sınırsız büyümemeli: bir flood'un IP'leri süresi dolunca düşer."""
    limiter = RateLimiter(per_min=5, per_day=100)
    for i in range(200):
        limiter.check(f"10.1.{i // 256}.{i % 256}", f"s{i}", now=1000.0)

    assert len(limiter._ip._hits) == 200
    limiter.check("9.9.9.9", "son", now=1000.0 + 3600)
    assert len(limiter._ip._hits) == 1, "süresi dolmuş anahtarlar temizlenmedi"


def test_client_ip_cloudflare_headerini_tercih_eder():
    """Canlı regresyon: ilk sürüm XFF'in son elemanını alıyordu ve limit hiç
    tetiklenmiyordu (22 ardışık istek, sıfır 429). Zincir istemci → Cloudflare →
    Traefik → uvicorn olduğu için XFF'in sonunda her istekte değişen bir Cloudflare
    EDGE adresi vardı; her istek kendi kovasına düşüyordu."""
    headers = [
        (b"cf-connecting-ip", b"198.51.100.7"),
        # Cloudflare gercek istemciyi ekler, Traefik de gordugu edge adresini ekler.
        (b"x-forwarded-for", b"198.51.100.7, 172.71.150.33"),
    ]
    assert client_ip(_istek(headers)) == "198.51.100.7"


def test_cloudflare_edge_degisse_de_ayni_kova():
    """Aynı ziyaretçinin ardışık istekleri farklı CF edge'lerinden gelse bile tek
    anahtara düşmeli — limitin çalışmasının önkoşulu bu."""
    limiter = RateLimiter(per_min=2, per_day=100)
    edges = (b"172.71.150.33", b"172.68.22.9", b"104.23.160.5")
    sonuclar = []
    for i, edge in enumerate(edges):
        ip = client_ip(_istek([(b"cf-connecting-ip", b"198.51.100.7"),
                               (b"x-forwarded-for", b"198.51.100.7, " + edge)]))
        sonuclar.append(limiter.check(ip, "s1", now=1000.0 + i).allowed)

    assert sonuclar == [True, True, False], "edge degisimi limiti sifirliyor"


@pytest.mark.parametrize(
    ("xff", "beklenen"),
    [
        (None, "10.0.0.1"),
        (b"203.0.113.9", "203.0.113.9"),
        # Cloudflare yoksa son eleman gercekten Traefik'in gordugu peer'dir.
        (b"1.2.3.4, 203.0.113.9", "203.0.113.9"),
        (b"  ,  203.0.113.9  ", "203.0.113.9"),
    ],
)
def test_cloudflare_yoksa_xffin_son_elemanina_dusulur(xff, beklenen):
    headers = [(b"x-forwarded-for", xff)] if xff else []
    assert client_ip(_istek(headers)) == beklenen


def test_bos_cf_headeri_xffi_engellemez():
    headers = [(b"cf-connecting-ip", b"  "), (b"x-forwarded-for", b"203.0.113.9")]
    assert client_ip(_istek(headers)) == "203.0.113.9"


def test_client_ip_istemci_yoksa_patlamaz():
    assert client_ip(_istek(client=None)) == "unknown"


# --- route seviyesi: 429 gercekten disari cikiyor mu ------------------------


class _SahteAgent:
    async def astream_events(self, _payload, version=None):
        yield {"event": "on_chat_model_stream",
               "data": {"chunk": type("P", (), {"content": "cevap"})()}}


async def test_chat_route_limit_asiminda_429_ve_retry_after_doner(monkeypatch):
    from fastapi import HTTPException

    from app.router import Route
    from app.routes.chat import chat
    from app.schemas import ChatRequest

    async def sahte_classify(message, history=None):
        return Route(category="career", resolved_query=message, kb_query=message)

    limiter = RateLimiter(per_min=20, per_day=100)
    monkeypatch.setattr("app.routes.chat.get_limiter", lambda: limiter)
    monkeypatch.setattr("app.routes.chat.select_runner",
                        lambda bulunan, lang="tr": _SahteAgent())
    # Router gercek LLM cagirir; bu test hiz limitini olcuyor, siniflandirmayi degil.
    monkeypatch.setattr("app.routes.chat.classify", sahte_classify)

    async def sahte_context(kb_query):
        return []

    monkeypatch.setattr("app.routes.chat.initial_context", sahte_context)

    kodlar = []
    for i in range(25):
        try:
            await chat(ChatRequest(message=f"soru {i}", session_id="rl"), _istek())
            kodlar.append(200)
        except HTTPException as exc:
            kodlar.append(exc.status_code)
            assert exc.headers["Retry-After"].isdigit()

    assert kodlar[:20] == [200] * 20
    assert kodlar[20:] == [429] * 5
