"""/chat için bellek içi sliding window rate limit.

/chat auth'suz ve halka açık; her istek 2-5 OpenAI + 2-5 Cohere çağrısı demek.
MAX_INPUT_LENGTH mesaj boyutunu sınırlıyordu ama istek SAYISI sınırsızdı —
basit bir script dakikada yüzlerce istek atıp faturayı şişirebilirdi.

Tek container çalıştığımız için sayaç süreç belleğinde tutuluyor; Redis'in
getireceği operasyon yükü bu ölçekte karşılığını vermez. Bedeli: deploy'da
pencereler sıfırlanır ve yatay ölçeklenirsek limit instance başına uygulanır.
İkisi de bugünkü kurulumda kabul edilebilir.
"""
from collections import deque
from dataclasses import dataclass
from functools import lru_cache
from time import monotonic

from fastapi import Request

from .cloudflare import is_cloudflare, is_private
from .config import get_settings

_MINUTE = 60.0
_DAY = 86_400.0
_PRUNE_INTERVAL = 60.0


class _Window:
    """Tek bir limit için anahtar başına kayan pencere sayacı."""

    def __init__(self, limit: int, window_s: float) -> None:
        self.limit = limit
        self.window_s = window_s
        self._hits: dict[str, deque[float]] = {}

    def check(self, key: str, now: float) -> float | None:
        """İzin varsa vuruşu kaydedip None döner; yoksa saniye cinsinden bekleme süresi."""
        hits = self._hits.setdefault(key, deque())
        cutoff = now - self.window_s
        while hits and hits[0] <= cutoff:
            hits.popleft()
        if len(hits) >= self.limit:
            return max(1.0, hits[0] + self.window_s - now)
        hits.append(now)
        return None

    def prune(self, now: float) -> None:
        cutoff = now - self.window_s
        stale = [k for k, hits in self._hits.items() if not hits or hits[-1] <= cutoff]
        for k in stale:
            del self._hits[k]


@dataclass(frozen=True)
class RateVerdict:
    allowed: bool
    reason: str = ""
    retry_after: int = 0
    # DB'ye yalnızca pencere başına ilk red yazılır: aksi halde bir flood, kendisini
    # sınırsız chat_logs yazımına çevirirdi. structlog her redde yazmaya devam eder.
    should_log: bool = False


class RateLimiter:
    def __init__(self, per_min: int, per_day: int) -> None:
        self._ip = _Window(per_min, _MINUTE)
        self._session = _Window(per_day, _DAY)
        self._logged: dict[str, float] = {}
        self._last_prune = 0.0

    def check(self, ip: str, session_id: str, now: float | None = None) -> RateVerdict:
        now = monotonic() if now is None else now
        self._maybe_prune(now)

        wait = self._ip.check(f"ip:{ip}", now)
        reason = "rate_limit_ip"
        if wait is None:
            wait = self._session.check(f"sid:{session_id}", now)
            reason = "rate_limit_session"
        if wait is None:
            return RateVerdict(allowed=True)

        return RateVerdict(
            allowed=False,
            reason=reason,
            retry_after=int(wait) + 1,
            should_log=self._mark_logged(f"{reason}:{ip}:{session_id}", now),
        )

    def _mark_logged(self, key: str, now: float) -> bool:
        last = self._logged.get(key)
        if last is not None and now - last < _MINUTE:
            return False
        self._logged[key] = now
        return True

    def _maybe_prune(self, now: float) -> None:
        if now - self._last_prune < _PRUNE_INTERVAL:
            return
        self._last_prune = now
        self._ip.prune(now)
        self._session.prune(now)
        self._logged = {k: t for k, t in self._logged.items() if now - t < _MINUTE}


@lru_cache
def get_limiter() -> RateLimiter:
    s = get_settings()
    return RateLimiter(s.RATE_LIMIT_PER_MIN, s.RATE_LIMIT_PER_DAY)


@dataclass(frozen=True)
class Client:
    ip: str
    # Bize baglanan adres — Cloudflare edge'i, Docker koprusu ya da (Cloudflare
    # atlanmissa) saldirganin kendisi.
    peer: str
    via_cloudflare: bool

    @property
    def direct_origin(self) -> bool:
        """Public bir adres origin'e DOGRUDAN baglanmis: Cloudflare atlanmis.

        Ozel adresler (lokal gelistirme, Docker ici) haric tutuluyor; yoksa
        `MODE=local` calisirken her istek uyari uretirdi. Firewall uygulandiktan
        sonra bu bayragin canlida bir daha hic dogru olmamasi gerekiyor —
        gorunurse ya kural dusmus ya da yeni bir yol acilmistir.
        """
        return (not self.via_cloudflare
                and self.peer != "unknown"
                and not is_private(self.peer))


def identify_client(request: Request) -> Client:
    """Gercek istemci adresi. Zincir: istemci -> Cloudflare -> Traefik -> uvicorn.

    Iki adres var ve ikisi de gerekli:

    * `peer` — Traefik'in KENDI gordugu baglanti adresi, XFF'in son elemani.
      Traefik gordugu peer'i listenin sonuna EKLER, bu yuzden istemci ne
      gonderirse gondersin son eleman uydurulamaz. Cloudflare uzerinden gelen
      trafikte bu her istekte degisen bir edge adresidir (canli olcum, 2026-08-26).
    * `CF-Connecting-IP` — asil ziyaretci. Cloudflare bu header'i kendisi yazip
      istemciden geleni ezer, ama YALNIZCA istek ondan geciyorsa.

    Kural: header'a ancak peer bir Cloudflare adresiyse guvenilir. 2026-08-28'de
    origin'in Cloudflare atlanarak dogrudan cevap verdigi olculdu;
    o yoldan gelen biri CF-Connecting-IP'yi her istekte degistirip limiti
    tamamen atlatabiliyordu. Peer Cloudflare degilse header yok sayilir ve
    kova peer'in kendisine baglanir — yani dogrudan baglanan da sinirli kalir.

    Peer ozel bir adresse (Docker koprusu, ikinci bir dahili proxy) topolojiyi
    bilmiyoruz: header'a guvenmeye devam edilir. Aksi halde onumuze bir ic proxy
    girdigi gun butun ziyaretciler tek kovaya duser ve limit herkesi keserdi.
    Guvenlik acisindan kayip yok: peer'i ozel gostermek istemcinin elinde degil.
    """
    peer = _peer(request)
    if is_cloudflare(peer) or is_private(peer):
        cf = request.headers.get("cf-connecting-ip", "").strip()
        if cf:
            return Client(ip=cf, peer=peer, via_cloudflare=is_cloudflare(peer))
    return Client(ip=peer, peer=peer, via_cloudflare=False)


def client_ip(request: Request) -> str:
    return identify_client(request).ip


def _peer(request: Request) -> str:
    """Bize baglanan adres: XFF'in son elemani, yoksa soketin karsi ucu."""
    xff = request.headers.get("x-forwarded-for")
    if xff:
        parts = [p.strip() for p in xff.split(",") if p.strip()]
        if parts:
            return parts[-1]
    return request.client.host if request.client else "unknown"
