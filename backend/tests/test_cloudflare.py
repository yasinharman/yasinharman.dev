"""Cloudflare aralik kontrolu — tamamen offline, ag yok.

Listenin GUNCEL olup olmadigi burada test edilmiyor: bunun icin upstream'e
gitmek gerekir, o da her push'u Cloudflare'in erisilebilirligine baglardi.
Guncellik nightly is akisindaki `cloudflare-ip-listesi` isinde kontrol ediliyor.
"""
from app.cloudflare import CLOUDFLARE_V4, CLOUDFLARE_V6, is_cloudflare, is_private


def test_gercek_edge_adresleri_taninir():
    # Ucu de canli trafikte XFF'in sonunda gordugumuz gercek edge adresleri.
    for ip in ("172.71.150.33", "172.68.22.9", "104.23.160.5"):
        assert is_cloudflare(ip), ip


def test_alan_adinin_kendi_cozumledigi_adres_cloudflaredir():
    """yasinharman.dev bu adrese cozumleniyor (2026-08-28)."""
    assert is_cloudflare("188.114.96.3")


def test_cloudflare_disi_public_adres_taninmaz():
    """Aciga sebep olan durum: origin'e dogrudan baglanan public bir adres.
    (Gercek origin adresi burada YAZILMIYOR — repo public; adresin kendisi
    korunacak seyin ta kendisi. Yer tutucu TEST-NET-3'ten.)"""
    assert not is_cloudflare("203.0.113.55")


def test_ipv6_edge_taninir():
    assert is_cloudflare("2606:4700::1111")
    assert not is_cloudflare("2001:db8::1")


def test_bozuk_girdi_patlamaz():
    for deger in ("", "unknown", "203.0.113.999", "not-an-ip", "::gg"):
        assert is_cloudflare(deger) is False
        assert is_private(deger) is False


def test_ozel_adresler():
    assert is_private("172.18.0.9")      # docker koprusu
    assert is_private("127.0.0.1")
    assert is_private("10.0.0.1")
    assert not is_private("203.0.113.55")


def test_liste_bicimi():
    """Nightly kontrolu bu listeleri satir satir upstream ile karsilastiriyor;
    bicim bozulursa karsilastirma da anlamsizlasir."""
    assert len(CLOUDFLARE_V4) >= 10 and len(CLOUDFLARE_V6) >= 5
    for cidr in CLOUDFLARE_V4 + CLOUDFLARE_V6:
        assert "/" in cidr and cidr == cidr.strip()
