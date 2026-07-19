"""Ağsız unit testler: chunklama davranışı ve metadata şeması."""
from app.config import get_settings
from app.ingest import chunk_generic, chunk_markdown

MD_FIXTURE = """# Projeler

## Business Data Finder

n8n tabanlı şirket iletişim bilgisi bulma aracı. SerpAPI ve GPT-4o-mini kullanır.

## Portfolio Sitesi

FastAPI ve LangChain tabanlı RAG backend'i olan kişisel site.

### Teknik Detay

Supabase pgvector üzerinde çalışır.
"""


def _settings():
    return get_settings()


def test_markdown_header_paths():
    docs = chunk_markdown(MD_FIXTURE, "projeler.md", _settings())
    header_paths = [d.metadata["headers"] for d in docs]
    assert ["Projeler", "Business Data Finder"] in header_paths
    assert ["Projeler", "Portfolio Sitesi", "Teknik Detay"] in header_paths


def test_markdown_breadcrumb_prefix():
    docs = chunk_markdown(MD_FIXTURE, "projeler.md", _settings())
    bdf = next(d for d in docs if d.metadata["headers"][-1:] == ["Business Data Finder"])
    assert bdf.page_content.startswith("Projeler > Business Data Finder\n\n")
    assert "SerpAPI" in bdf.page_content


def test_markdown_metadata_schema():
    docs = chunk_markdown(MD_FIXTURE, "projeler.md", _settings())
    for i, d in enumerate(docs):
        assert d.metadata["source"] == "projeler.md"
        assert d.metadata["chunk_index"] == i
        assert len(d.metadata["content_hash"]) == 16
        assert d.metadata["ingested_at"]
        assert isinstance(d.metadata["headers"], list)


def test_markdown_deterministic_hashes():
    a = chunk_markdown(MD_FIXTURE, "projeler.md", _settings())
    b = chunk_markdown(MD_FIXTURE, "projeler.md", _settings())
    assert [d.metadata["content_hash"] for d in a] == [d.metadata["content_hash"] for d in b]
    assert [d.page_content for d in a] == [d.page_content for d in b]


def test_markdown_oversize_section_splits():
    s = _settings()
    big = "# Başlık\n\n" + ("Uzun cümle tekrarı. " * 200)  # ~4000 karakter
    docs = chunk_markdown(big, "buyuk.md", s)
    assert len(docs) > 1
    for d in docs:
        # breadcrumb prefix'i CHUNK_SIZE üstüne binebilir; tolerans payı tanınır
        assert len(d.page_content) <= s.CHUNK_SIZE + len("Başlık\n\n") + s.CHUNK_OVERLAP


def test_generic_respects_chunk_size():
    s = _settings()
    text = "Kelime " * 1000
    docs = chunk_generic(text, "cv.pdf", s)
    assert len(docs) > 1
    for d in docs:
        assert len(d.page_content) <= s.CHUNK_SIZE
        assert d.metadata["headers"] == []
