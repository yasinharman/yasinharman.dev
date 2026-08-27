"""Retrieval eval: golden.yaml'daki soruları retriever.search'e verir, hit@K raporlar.

Gerçek API anahtarları ve canlı Supabase ister (backend/.env).

Kullanım:
    cd backend
    python -m eval.run_eval [--min-rate 0.85]
    python -m eval.run_eval --denetim     # vakaların kendisini denetle
"""
from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.retriever import search


def load_golden() -> list[dict]:
    path = Path(__file__).parent / "golden.yaml"
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def is_hit(entry: dict, docs) -> bool:
    if entry.get("negative"):
        return len(docs) == 0
    blob = "\n".join(d.page_content for d in docs).lower()

    # expected_all: parcalarin hepsi AYNI chunk'ta bulunmali. Digerlerinin aksine
    # bu, belirli bir chunk'in sonucta HAYATTA KALDIGINI garanti eder.
    #
    # Gerekcesi olculdu (2026-08-27): yetenekler.md 5 chunk'a bolunuyor ve
    # "kaynak yetenekler.md mi" testi, dogru chunk elenmisken bile yesil kaliyordu —
    # bulgu B tam bu yuzden 30/30'luk golden set'ten kacti.
    #
    # "Ayni chunk" sarti da olculdu: ilk surum parcalari birlesik metinde ariyordu
    # ve ["Docker", "containerization"] beklentisi iki AYRI chunk'tan karsilanip
    # yesil donuyordu. tests/test_corpus_health.py her expected_all'in korpusta
    # tam olarak bir chunk'i sabitledigini dogrular.
    if gerekli := entry.get("expected_all"):
        return any(
            all(sub.lower() in d.page_content.lower() for sub in gerekli) for d in docs
        )

    sources = {d.metadata.get("source") for d in docs}
    if any(s in sources for s in entry.get("expected_sources", [])):
        return True
    return any(sub.lower() in blob for sub in entry.get("expected_substrings", []))


async def run(min_rate: float) -> int:
    golden = load_golden()
    results: list[tuple[dict, bool, list]] = []
    for entry in golden:
        docs = await search(entry["question"])
        results.append((entry, is_hit(entry, docs), docs))

    hits = sum(1 for _, hit, _ in results if hit)
    rate = hits / len(results)

    print(f"{'ID':<22} {'SONUÇ':<6} {'top kaynak / skor'}")
    print("-" * 70)
    for entry, hit, docs in results:
        top = (f"{docs[0].metadata.get('source')} "
               f"(rerank={docs[0].metadata.get('rerank_score', 0):.3f})") if docs else "(boş)"
        print(f"{entry['id']:<22} {'PASS' if hit else 'FAIL':<6} {top}")
    print("-" * 70)
    print(f"Hit rate: {hits}/{len(results)} = {rate:.1%}  (eşik: {min_rate:.0%})")

    return 0 if rate >= min_rate else 1


async def denetle() -> int:
    """Vakaların kendisini ölç: bir vaka, dönen sonuçtaki birden fazla chunk
    tarafından tek başına karşılanıyorsa GEVŞEKTİR — doğru chunk elenmiş olsa
    bile yeşil kalır. 2026-08-27'de 28 pozitif vakanın 12'si böyleydi ve canlıdaki
    bir retrieval bug'ı (bulgu B) tam bu boşluktan geçti.

    Rapor amaçlı: exit kodu her zaman 0. "Gevşek" otomatik olarak "yanlış" demek
    değil — bazı sorular gerçekten birden fazla chunk'tan cevaplanabilir. Karar
    insanın; bu sadece kararın görünür olmasını sağlıyor.
    """
    gevsek, siki = [], []
    for entry in load_golden():
        if entry.get("negative"):
            continue
        docs = await search(entry["question"])
        tekil = [d for d in docs if is_hit(entry, [d])]
        (gevsek if len(tekil) > 1 else siki).append((entry["id"], tekil))

    print(f"GEVŞEK — birden fazla chunk tek başına yetiyor ({len(gevsek)})")
    for vid, docs in gevsek:
        print(f"  {vid}  ({len(docs)} chunk)")
        for d in docs:
            print(f"       - {d.page_content.split(chr(10), 1)[0].strip()[:64]}")
    print(f"\nSABİTLİ — tek chunk ({len(siki)})")
    for vid, docs in siki:
        ilk = docs[0].page_content.split(chr(10), 1)[0].strip()[:64] if docs else "(eşleşme yok!)"
        print(f"  {vid:30} {ilk}")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--min-rate", type=float, default=0.85)
    parser.add_argument("--denetim", action="store_true",
                        help="hit rate yerine vakaların sıkılığını raporla")
    args = parser.parse_args()
    if args.denetim:
        sys.exit(asyncio.run(denetle()))
    sys.exit(asyncio.run(run(args.min_rate)))


if __name__ == "__main__":
    main()
