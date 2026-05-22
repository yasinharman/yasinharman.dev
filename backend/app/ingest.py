"""Document ingestion pipeline: load → split → embed → upsert into Supabase.

CLI: python -m app.ingest <file_or_dir> [--source <label>]
"""
from __future__ import annotations

import argparse
import asyncio
import os
from pathlib import Path
from typing import Iterable

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from .retriever import vector_store


def _read_pdf(path: Path) -> str:
    from pypdf import PdfReader
    reader = PdfReader(str(path))
    return "\n".join((p.extract_text() or "") for p in reader.pages)


def _read_docx(path: Path) -> str:
    import docx
    d = docx.Document(str(path))
    return "\n".join(p.text for p in d.paragraphs)


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def _load(path: Path) -> str:
    ext = path.suffix.lower()
    if ext == ".pdf":
        return _read_pdf(path)
    if ext in {".docx"}:
        return _read_docx(path)
    if ext in {".txt", ".md", ".markdown", ".html", ".htm"}:
        return _read_text(path)
    raise ValueError(f"Unsupported file type: {ext}")


def _iter_files(root: Path) -> Iterable[Path]:
    if root.is_file():
        yield root
        return
    for p in root.rglob("*"):
        if p.is_file() and p.suffix.lower() in {".pdf", ".docx", ".txt", ".md", ".markdown", ".html", ".htm"}:
            yield p


def chunk(text: str, source: str) -> list[Document]:
    splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=150)
    return [Document(page_content=c, metadata={"source": source}) for c in splitter.split_text(text)]


async def ingest_path(target: str, source_label: str | None = None) -> int:
    root = Path(target)
    if not root.exists():
        raise FileNotFoundError(target)

    docs: list[Document] = []
    for f in _iter_files(root):
        text = _load(f)
        if not text.strip():
            continue
        source = source_label or os.path.relpath(str(f), start=str(root.parent if root.is_file() else root))
        docs.extend(chunk(text, source=source))

    if not docs:
        return 0

    vs = vector_store()
    await asyncio.to_thread(vs.add_documents, docs)
    return len(docs)


def _main() -> None:
    parser = argparse.ArgumentParser(description="Ingest documents into Supabase vector store")
    parser.add_argument("path", help="File or directory")
    parser.add_argument("--source", help="Optional source label", default=None)
    args = parser.parse_args()
    n = asyncio.run(ingest_path(args.path, args.source))
    print(f"Ingested {n} chunks from {args.path}")


if __name__ == "__main__":
    _main()
