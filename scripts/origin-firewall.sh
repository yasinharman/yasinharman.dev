#!/usr/bin/env bash
# SUNUCUDA calistirilir (Coolify host'u) — 80/443'u yalnizca Cloudflare edge
# araliklarina acar. Gelistirme makinesinde isi yok.
#
# NEDEN: 2026-08-28'de origin dogrudan cevap veriyordu — https://<origin-ip>/healthz
# 200, /chat 405, gecerli sertifikayla. Adres tahmin bile gerektirmiyordu, alan
# adinin kendi DNS kayitlarindan okunuyordu. Cloudflare'i atlayan biri
# CF-Connecting-IP'yi uydurup rate limit'i etkisiz birakabiliyor, WAF/bot
# korumasi devre disi kaliyor, DDoS dogrudan sunucuya iniyor.
#
# NEDEN ufw DEGIL: Coolify Traefik'i portlari Docker uzerinden yayinliyor.
# Docker kendi iptables kurallarini ufw'nin ONUNE koyar, dolayisiyla
# `ufw deny 443` SESSIZCE etkisiz kalir — kural listede gorunur, trafik gecer.
# Docker'in saygi duydugu tek yer DOCKER-USER zinciri; kurallar oraya yaziliyor.
#
# Kullanim:
#   ./scripts/origin-firewall.sh              # ne yapacagini yazar, dokunmaz
#   sudo ./scripts/origin-firewall.sh --apply # uygular
#   sudo ./scripts/origin-firewall.sh --kaldir
#
# Uyguladiktan sonra DISARIDAN dogrula (kendi makinenden):
#   curl -m 8 -sk https://<origin-ip>/healthz -H 'Host: api.yasinharman.dev'
#   -> baglanti zaman asimina ugramali. Hala 200 donuyorsa Traefik host
#      network'undedir; o durumda ayni kurallar INPUT zincirine yazilmali.
set -euo pipefail

ZINCIR="CLOUDFLARE-ONLY"
PORTLAR="80,443"
IC_AGLAR_V4="10.0.0.0/8 172.16.0.0/12 192.168.0.0/16 127.0.0.0/8"
IC_AGLAR_V6="fc00::/7 fe80::/10 ::1/128"
MOD="${1:---dry-run}"

hata() { echo "HATA: $*" >&2; exit 1; }

araliklari_cek() {
  local url="$1" cikti
  cikti="$(curl -fsS --max-time 20 "$url")" || hata "$url cekilemedi"
  echo "$cikti" | sed '/^[[:space:]]*$/d'
}

V4="$(araliklari_cek https://www.cloudflare.com/ips-v4)"
V6="$(araliklari_cek https://www.cloudflare.com/ips-v6)"

# Emniyet: kisa/bos bir cevapla kurallari yazmak butun trafigi keser. Liste
# 2026-08-28'de 15 v4 + 7 v6; 10'un altina dusmesi cevabin bozuk oldugu anlamina
# gelir, Cloudflare'in araliklarini yariya indirdigi degil.
[ "$(echo "$V4" | wc -l)" -ge 10 ] || hata "ips-v4 beklenenden kisa; uygulanmadi"
[ "$(echo "$V6" | wc -l)" -ge 5 ]  || hata "ips-v6 beklenenden kisa; uygulanmadi"

kurallar() {          # $1: iptables|ip6tables  $2: cf araliklari  $3: ic aglar
  local ipt="$1"
  echo "$ipt -N $ZINCIR"
  echo "$ipt -F $ZINCIR"
  # Kurulmus baglantilar once: kural degisirken acik oturumlar kopmasin.
  echo "$ipt -A $ZINCIR -m conntrack --ctstate RELATED,ESTABLISHED -j RETURN"
  local cidr
  for cidr in $2; do
    echo "$ipt -A $ZINCIR -p tcp -m multiport --dports $PORTLAR -s $cidr -j RETURN"
  done
  # Container'lar arasi ve host ici trafik (Traefik -> uygulama, healthcheck).
  for cidr in $3; do
    echo "$ipt -A $ZINCIR -s $cidr -j RETURN"
  done
  # Yalnizca 80/443 kesiliyor: SSH ve diger portlar bu zincire hic girmiyor.
  echo "$ipt -A $ZINCIR -p tcp -m multiport --dports $PORTLAR -j DROP"
  echo "$ipt -I DOCKER-USER 1 -j $ZINCIR"
}

if [ "$MOD" = "--kaldir" ]; then
  [ "$(id -u)" -eq 0 ] || hata "root gerekli"
  for ipt in iptables ip6tables; do
    while $ipt -C DOCKER-USER -j "$ZINCIR" 2>/dev/null; do
      $ipt -D DOCKER-USER -j "$ZINCIR"
    done
    $ipt -F "$ZINCIR" 2>/dev/null || true
    $ipt -X "$ZINCIR" 2>/dev/null || true
  done
  echo "$ZINCIR kaldirildi. Origin yeniden herkese acik."
  exit 0
fi

if [ "$MOD" != "--apply" ]; then
  echo "# --- kuru calisma; hicbir sey uygulanmadi (--apply ile uygulanir) ---"
  kurallar iptables "$V4" "$IC_AGLAR_V4"
  kurallar ip6tables "$V6" "$IC_AGLAR_V6"
  exit 0
fi

[ "$(id -u)" -eq 0 ] || hata "root gerekli: sudo $0 --apply"
iptables -n -L DOCKER-USER >/dev/null 2>&1 \
  || hata "DOCKER-USER zinciri yok — Docker calisiyor mu?"

uygula() {            # zinciri bastan kurar, tekrar tekrar calistirilabilir
  local ipt="$1"; shift
  $ipt -N "$ZINCIR" 2>/dev/null || true
  $ipt -F "$ZINCIR"
  $ipt -A "$ZINCIR" -m conntrack --ctstate RELATED,ESTABLISHED -j RETURN
  local cidr
  for cidr in $1; do
    $ipt -A "$ZINCIR" -p tcp -m multiport --dports "$PORTLAR" -s "$cidr" -j RETURN
  done
  for cidr in $2; do
    $ipt -A "$ZINCIR" -s "$cidr" -j RETURN
  done
  $ipt -A "$ZINCIR" -p tcp -m multiport --dports "$PORTLAR" -j DROP
  # Kanca yalnizca bir kez: script tekrar calistirildiginda kural cogalmasin.
  $ipt -C DOCKER-USER -j "$ZINCIR" 2>/dev/null || $ipt -I DOCKER-USER 1 -j "$ZINCIR"
}

uygula iptables "$V4" "$IC_AGLAR_V4"
if ip6tables -n -L DOCKER-USER >/dev/null 2>&1; then
  uygula ip6tables "$V6" "$IC_AGLAR_V6"
else
  echo "UYARI: ip6tables/DOCKER-USER yok; IPv6 kurali yazilmadi." >&2
fi

echo "Uygulandi: 80/443 yalnizca Cloudflare araliklarindan."
echo
echo "KALICILIK: kurallar yeniden baslatmada kaybolur. Kalici yapmak icin:"
echo "  apt-get install -y iptables-persistent && netfilter-persistent save"
echo "Aksi halde bu scripti reboot sonrasi tekrar calistirin."
