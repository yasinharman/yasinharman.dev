#!/usr/bin/env bash
# backend/app/cloudflare.py'deki araliklar upstream ile ayni mi?
#
# Neden ayri bir kontrol: liste yilda birkac kez degisir ve degistiginde kod
# SESSIZCE eskir — yeni bir Cloudflare araligindan gelen mesru trafik
# "Cloudflare disi" sayilir. Test suite bunu yakalayamaz (ag yok, yakalamamali
# da: her push'u cloudflare.com'un erisilebilirligine baglamak istemiyoruz).
# Bu yuzden kontrol nightly'de, kendi isinde.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
guncel="$(mktemp)"; paket="$(mktemp)"
trap 'rm -f "$guncel" "$paket"' EXIT

# Iki listeyi ayri ayri cek: birlestirilmis cikti son satiri baslangica
# yapistirabilir (ips-v4 sonunda newline garanti degil).
{ curl -fsS --max-time 20 https://www.cloudflare.com/ips-v4; echo
  curl -fsS --max-time 20 https://www.cloudflare.com/ips-v6; echo
} | sed '/^[[:space:]]*$/d' | sort > "$guncel"

(cd "$ROOT/backend" && python3 -c \
  "from app.cloudflare import CLOUDFLARE_V4, CLOUDFLARE_V6
print('\n'.join(CLOUDFLARE_V4 + CLOUDFLARE_V6))") | sort > "$paket"

if diff -u --label "backend/app/cloudflare.py" "$paket" \
            --label "cloudflare.com (upstream)" "$guncel"; then
  echo "Cloudflare aralik listesi guncel ($(wc -l < "$paket") aralik)."
  exit 0
fi

cat >&2 <<'MSG'

HATA: Paketlenmis aralik listesi upstream ile ayni degil.
Yapilacaklar:
  1. backend/app/cloudflare.py icindeki CLOUDFLARE_V4/V6 listelerini guncelle
     ve yorumdaki tarihi degistir.
  2. Sunucudaki firewall kurallarini yenile: sudo scripts/origin-firewall.sh --apply
     (script araliklari upstream'den kendi cekiyor, ama kurallar bir kez yazilir).
MSG
exit 1
