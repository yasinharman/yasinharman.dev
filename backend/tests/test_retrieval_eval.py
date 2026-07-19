"""Integration eval: canlı Supabase + gerçek API anahtarları gerektirir.

Çalıştırma: pytest -m integration
Anahtarsız ortamda (CI) otomatik skip edilir.
"""
import os
from pathlib import Path

import pytest

_HAS_KEYS = bool(os.getenv("OPENAI_API_KEY")) or (Path(__file__).parents[1] / ".env").exists()

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(not _HAS_KEYS, reason="gerçek API anahtarları yok"),
]


def _golden():
    import yaml
    path = Path(__file__).parents[1] / "eval" / "golden.yaml"
    return yaml.safe_load(path.read_text(encoding="utf-8"))


@pytest.mark.parametrize("entry", _golden(), ids=lambda e: e["id"])
async def test_retrieval(entry):
    from app.retriever import search
    from eval.run_eval import is_hit

    docs = await search(entry["question"])
    assert is_hit(entry, docs), (
        f"{entry['id']}: beklenen {entry.get('expected_sources') or entry.get('expected_substrings') or 'boş sonuç'}, "
        f"gelen kaynaklar: {[d.metadata.get('source') for d in docs]}"
    )
