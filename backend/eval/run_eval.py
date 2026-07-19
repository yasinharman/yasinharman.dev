"""Retrieval eval: golden.yaml'daki soruları retriever.search'e verir, hit@K raporlar.

Gerçek API anahtarları ve canlı Supabase ister (backend/.env).

Kullanım:
    cd backend
    python -m eval.run_eval [--min-rate 0.85]
"""
from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.retriever import search  # noqa: E402


def load_golden() -> list[dict]:
    path = Path(__file__).parent / "golden.yaml"
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def is_hit(entry: dict, docs) -> bool:
    if entry.get("negative"):
        return len(docs) == 0
    sources = {d.metadata.get("source") for d in docs}
    if any(s in sources for s in entry.get("expected_sources", [])):
        return True
    blob = "\n".join(d.page_content for d in docs)
    return any(sub.lower() in blob.lower() for sub in entry.get("expected_substrings", []))


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


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--min-rate", type=float, default=0.85)
    args = parser.parse_args()
    sys.exit(asyncio.run(run(args.min_rate)))


if __name__ == "__main__":
    main()
