"""Direct Supabase RPC + Cohere rerank retriever.

Bypasses langchain_community.SupabaseVectorStore (which is incompatible with
newer postgrest-py). Calls the `match_documents` RPC directly, then reranks
with Cohere.
"""
from functools import lru_cache
from langchain_core.documents import Document
import cohere

from .config import get_settings
from .deps import supabase_client, embeddings


@lru_cache
def _cohere() -> cohere.Client:
    s = get_settings()
    return cohere.Client(s.COHERE_API_KEY)


async def _embed(query: str) -> list[float]:
    return await embeddings().aembed_query(query)


async def _vector_search(query: str, k: int) -> list[Document]:
    s = get_settings()
    vec = await _embed(query)
    resp = supabase_client().rpc(
        s.SUPABASE_QUERY_NAME,
        {"query_embedding": vec, "match_count": k, "filter": {}},
    ).execute()
    docs: list[Document] = []
    for row in (resp.data or []):
        content = row.get("content") or ""
        metadata = row.get("metadata") or {}
        if "similarity" in row:
            metadata["similarity"] = row["similarity"]
        docs.append(Document(page_content=content, metadata=metadata))
    return docs


def _rerank(query: str, docs: list[Document], top_n: int) -> list[Document]:
    if not docs:
        return docs
    s = get_settings()
    texts = [d.page_content for d in docs]
    result = _cohere().rerank(
        model=s.COHERE_RERANK_MODEL,
        query=query,
        documents=texts,
        top_n=min(top_n, len(texts)),
    )
    reranked: list[Document] = []
    for r in result.results:
        d = docs[r.index]
        d.metadata = {**d.metadata, "rerank_score": r.relevance_score}
        reranked.append(d)
    return reranked


async def search(query: str) -> list[Document]:
    s = get_settings()
    docs = await _vector_search(query, k=s.RETRIEVER_K)
    return _rerank(query, docs, top_n=s.RERANK_TOP_N)
