"""Cloudflare edge adres araliklari — CF-Connecting-IP'ye ne zaman guvenilecegi.

`ratelimit.client_ip` istemciyi CF-Connecting-IP'den okuyor. O header'a guvenmek
YALNIZCA istek gercekten Cloudflare uzerinden geldiyse dogru: Cloudflare header'i
kendisi yazip istemciden geleni ezer, ama origin'e dogrudan baglanan biri onu
istedigi degerle gonderebilir.

2026-08-28 olcumu — origin, Cloudflare atlanarak dogrudan cevap
veriyordu: `GET /healthz` 200, `GET /chat` 405 (yani uygulamaya ulasiliyor),
gecerli Let's Encrypt sertifikasiyla. Adres tahmin gerektirmiyordu, alan adinin
kendi DNS kayitlarinda yayindaydi (SPF `ip4:` + PTR). Yani sahte bir
CF-Connecting-IP ile her istek kendi kovasina dusurulebilir, rate limit etkisiz.

Bu modul "istek Cloudflare'dan mi geldi" sorusunu cevaplar. Kalici cozum agda
(scripts/origin-firewall.sh — 80/443'u yalnizca bu araliklara acar); bu katman
firewall uygulanana kadar ve o bir gun sessizce kalkarsa diye duruyor.
"""
from functools import lru_cache
from ipaddress import ip_address, ip_network

# Kaynak: https://www.cloudflare.com/ips-v4 ve https://www.cloudflare.com/ips-v6
# 2026-08-28'de alindi. Liste yilda birkac kez degisir ve degistiginde bu dosya
# sessizce eskir; nightly is akisindaki "cloudflare-ip-listesi" isi her gece
# upstream ile karsilastirir, saparsa kirmizi yanar.
CLOUDFLARE_V4 = (
    "173.245.48.0/20",
    "103.21.244.0/22",
    "103.22.200.0/22",
    "103.31.4.0/22",
    "141.101.64.0/18",
    "108.162.192.0/18",
    "190.93.240.0/20",
    "188.114.96.0/20",
    "197.234.240.0/22",
    "198.41.128.0/17",
    "162.158.0.0/15",
    "104.16.0.0/13",
    "104.24.0.0/14",
    "172.64.0.0/13",
    "131.0.72.0/22",
)

CLOUDFLARE_V6 = (
    "2400:cb00::/32",
    "2606:4700::/32",
    "2803:f800::/32",
    "2405:b500::/32",
    "2405:8100::/32",
    "2a06:98c0::/29",
    "2c0f:f248::/32",
)

_AGLAR = tuple(ip_network(a) for a in CLOUDFLARE_V4 + CLOUDFLARE_V6)


# maxsize sinirli: kaynak adres saldirgan tarafindan dondurulebilir, sinirsiz
# cache kendisi bir bellek buyume yolu olurdu.
@lru_cache(maxsize=4096)
def is_cloudflare(ip: str) -> bool:
    """`ip` yayinlanmis bir Cloudflare edge araligina dusuyor mu?"""
    try:
        adres = ip_address(ip)
    except ValueError:
        return False
    return any(adres in ag for ag in _AGLAR)


# Ic ag araliklari ACIKCA yaziliyor; `ip_address(...).is_private` KULLANILMIYOR.
# Stdlib onu "globalde yonlendirilemez" anlaminda kullaniyor ve dokumantasyon
# bloklarini (203.0.113.0/24, 198.51.100.0/24) da kapsiyor — testlerin ve
# orneklerin adresleri tam olarak oradan geliyor. Bize lazim olan dar tanim:
# "onumuzdeki bir ic hop mu".
_IC_AGLAR = tuple(ip_network(a) for a in (
    "10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16",   # RFC1918 (Docker koprusu dahil)
    "127.0.0.0/8", "169.254.0.0/16",                    # loopback, link-local
    "::1/128", "fc00::/7", "fe80::/10",
))


@lru_cache(maxsize=4096)
def is_private(ip: str) -> bool:
    """Ic ag adresi mi (Docker koprusu, loopback, RFC1918)?

    Ayri tutuluyor cunku "ozel adres" belirsizlik demek: onumuzde ikinci bir
    dahili proxy varsa mesru trafigin de peer'i ozel gorunur. O durumda
    Cloudflare'dan gelmedigine karar vermek butun ziyaretcileri tek kovaya
    toplardi — yani kendi kendimize DoS. Bkz. ratelimit.identify_client.
    """
    try:
        adres = ip_address(ip)
    except ValueError:
        return False
    return any(adres in ag for ag in _IC_AGLAR)
