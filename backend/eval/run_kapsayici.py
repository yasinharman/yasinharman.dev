"""Kapsayıcı soruda cevap, özet listesini kopyalamakla yetiniyor mu?

Neden ayrı bir eval: bu arıza mevcut ölçümlerin HİÇBİRİNDE görünmüyordu.
Retrieval doğruydu (golden 32/32), cevaptaki her iddia destekliydi (groundedness
14/14) — cevap sadece EKSİKTİ. Model `data/projeler.md`'deki "## Projelerin
Listesi" bölümünü olduğu gibi yapıştırıp duruyordu.

Ölçüldü (2026-08-28): 18 örnekte 5'i (%28) 328 karakterlik, bayt bayt aynı
kopyaydı. Rastlantısal olduğu için tek çağrı yetmez; her ifade birkaç kez
örneklenir. Düzeltme sonrası aynı ölçüm 0/18.

Örneklem gücü: varsayılan 3 tekrar = 9 örnek, %28'lik bir regresyonu ~%95
olasılıkla yakalar (1 - 0.72^9). Nightly her gece koştuğu için iki geceyi
birden kaçırma ihtimali binde 2; daha fazla örnek almanın karşılığı yok.

Eşik iki ayaklı ve ikisi de kopyalamayı hedefliyor:
  1. cevap, özet bölümünün kendisinden belirgin şekilde uzun olmalı
  2. listedeki her maddenin adı cevapta geçmeli
"""
from __future__ import annotations

import argparse
import asyncio
import statistics
import sys
from pathlib import Path

from eval.run_groundedness import _cevapla

SORULAR = [
    "Yasin'in projeleri neler?",
    "Yasin'in projeleri nelerdir?",
    "Yasin'in projelerinden bahset",
]

# Cevapta hepsi geçmeli. Kısa ve dosyada birebir duran adlar seçildi; korpus
# yeniden yazılırsa bu liste de güncellenmeli.
MADDELER = ("RAG Agent", "Internship Tracker", "Business Data Finder")

_OZET_BASLIGI = "## Projelerin Listesi"


def _ozet_uzunlugu() -> int:
    """Özet bölümünün karakter uzunluğu — eşiğin dayanağı sabit değil, korpus."""
    metin = (Path(__file__).resolve().parents[1] / "data" / "projeler.md").read_text("utf-8")
    bas = metin.index(_OZET_BASLIGI)
    son = metin.index("\n## ", bas + len(_OZET_BASLIGI))
    return len(metin[bas:son].strip())


async def _vaka(soru: str, sem: asyncio.Semaphore, esik: int) -> dict:
    async with sem:
        cevap, chunklar = await _cevapla(soru)
    eksik = [m for m in MADDELER if m.lower() not in cevap.lower()]
    return {"soru": soru, "uzunluk": len(cevap), "chunk": len(chunklar), "eksik": eksik,
            "gecti": len(cevap) >= esik and not eksik}


async def _main(tekrar: int, eszaman: int, oran: float) -> int:
    ozet = _ozet_uzunlugu()
    esik = int(ozet * oran)
    print(f"Özet bölümü {ozet} karakter → eşik {esik} ({oran}×), {tekrar} tekrar\n")

    sem = asyncio.Semaphore(eszaman)
    sonuclar = await asyncio.gather(
        *[_vaka(s, sem, esik) for s in SORULAR for _ in range(tekrar)])

    for soru in SORULAR:
        grup = [r for r in sonuclar if r["soru"] == soru]
        u = [r["uzunluk"] for r in grup]
        gecen = sum(r["gecti"] for r in grup)
        isaret = "✓" if gecen == len(grup) else "✗"
        print(f"{isaret} {soru!r}\n    {u}  medyan {statistics.median(u):.0f}  "
              f"geçen {gecen}/{len(grup)}")

    hatalar = [r for r in sonuclar if not r["gecti"]]
    if hatalar:
        print("\n=== BAŞARISIZ ===")
        for r in hatalar:
            neden = f"eksik madde: {r['eksik']}" if r["eksik"] else f"kısa ({r['uzunluk']} kr)"
            print(f"  {r['soru']!r} → {neden}")

    toplam = len(sonuclar)
    print(f"\nGeçen: {toplam - len(hatalar)}/{toplam}")
    return 0 if not hatalar else 1


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Kapsayıcı soruda cevap bütünlüğü")
    ap.add_argument("--tekrar", type=int, default=3, help="ifade başına örnek sayısı")
    ap.add_argument("--eszaman", type=int, default=3, help="paralel istek sayısı")
    ap.add_argument("--oran", type=float, default=1.5,
                    help="cevap, özet bölümünün kaç katından uzun olmalı")
    a = ap.parse_args()
    sys.exit(asyncio.run(_main(a.tekrar, a.eszaman, a.oran)))
