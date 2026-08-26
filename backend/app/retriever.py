"""Direct Supabase RPC + Cohere rerank retriever.

Bypasses langchain_community.SupabaseVectorStore (which is incompatible with
newer postgrest-py). Calls the `match_documents` RPC directly, then reranks
with Cohere and filters by a minimum rerank score.

`retrieval_trace` ContextVar: /chat route'u istek başına boş liste set eder;
her search() çağrısı buraya sorgu + sonuç özetini ekler (chat_logs.retrieval'a
yazılır). Set edilmemişse (CLI, eval) hiçbir şey kaydedilmez.
"""
import asyncio
from contextvars import ContextVar
from functools import lru_cache

import cohere
import structlog
from langchain_core.documents import Document

from .config import Settings, get_settings
from .deps import supabase_client, embeddings
from .retry import external_retry

retrieval_trace: ContextVar[list[dict] | None] = ContextVar("retrieval_trace", default=None)


@lru_cache
def _cohere() -> cohere.Client:
    s = get_settings()
    return cohere.Client(s.COHERE_API_KEY)


@external_retry
async def _embed(query: str) -> list[float]:
    return await embeddings().aembed_query(query)


@external_retry
def _rpc_call(query_name: str, params: dict):
    return supabase_client().rpc(query_name, params).execute()


async def _vector_search(query: str, k: int) -> list[Document]:
    s = get_settings()
    vec = await _embed(query)
    params: dict = {"query_embedding": vec, "match_count": k, "filter": {}}
    # 0.0 iken gönderilmez: eski 3-arg RPC ile geriye uyumlu kalır.
    if s.MATCH_THRESHOLD > 0:
        params["match_threshold"] = s.MATCH_THRESHOLD
    resp = await asyncio.to_thread(_rpc_call, s.SUPABASE_QUERY_NAME, params)
    docs: list[Document] = []
    for row in (resp.data or []):
        content = row.get("content") or ""
        metadata = row.get("metadata") or {}
        if "similarity" in row:
            metadata["similarity"] = row["similarity"]
        docs.append(Document(page_content=content, metadata=metadata))
    return docs


@external_retry
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


_OVERVIEW_SUFFIX = "Listesi"


def _is_overview(doc: Document) -> bool:
    """Korpus konvansiyonu: '... Listesi' başlıklı bölümler yalnızca başlıkları sayar."""
    return any(str(h).strip().endswith(_OVERVIEW_SUFFIX)
               for h in (doc.metadata.get("headers") or []))


@external_retry
def _fetch_source(source: str) -> list[Document]:
    s = get_settings()
    resp = (supabase_client().table(s.SUPABASE_TABLE)
            .select("content, metadata")
            .eq("metadata->>source", source)
            .execute())
    docs = [Document(page_content=r.get("content") or "", metadata=r.get("metadata") or {})
            for r in (resp.data or [])]
    docs.sort(key=lambda d: d.metadata.get("chunk_index", 0))
    return docs


async def _expand_overviews(kept: list[Document]) -> list[Document]:
    """Özet chunk'ı geçtiyse aynı kaynağın tüm bölümlerini de ekler.

    Enumeration sorularında ("iş tecrübelerinden bahset") rerank yalnızca özet
    bölümü üst sıraya taşır; detay bölümleri eşiğin altında kalır ve cevap tek
    satırlık başlık tekrarına düşer. Modelin takip sorgusu atmasına güvenmek
    gpt-4o-mini ile güvenilir olmadığı için genişletme burada deterministik yapılır.
    """
    sources = {d.metadata.get("source") for d in kept if _is_overview(d)}
    sources.discard(None)
    if not sources:
        return kept

    seen = {(d.metadata.get("source"), d.metadata.get("chunk_index")) for d in kept}
    expanded = list(kept)
    for source in sorted(sources):
        for doc in await asyncio.to_thread(_fetch_source, source):
            key = (doc.metadata.get("source"), doc.metadata.get("chunk_index"))
            if key not in seen:
                seen.add(key)
                expanded.append(doc)
    return expanded


def _apply_cutoff(reranked: list[Document], s: Settings) -> tuple[list[Document], float]:
    """Esigin altindaki chunk'lari eler; (kept, cutoff) doner.

    HICBIR SEY GECEMEZSE BOS DONER — bu bilincli. Bir ara bos yerine en iyi 3 chunk
    donduruluyordu ("sessiz basarisizlik" korkusuyla) ve iki olcum bunun yanlis
    oldugunu gosterdi: canli veride hic tetiklenmedi (31 aramanin 0'i), buna karsilik
    golden.yaml'daki dort negatif vakayi birden kiriyordu. Kapsam disi bir soruya
    alakasiz chunk vermek halusinasyon yuzeyi acar; portfolyo asistaninda en pahali
    hata budur.

    "Kac aramada 0 chunk dondu" sorusu chat_logs.retrieval -> kept=0 ile sorgulanir.
    """
    if not reranked:
        return [], 0.0
    cutoff = s.RERANK_SCORE_THRESHOLD
    return [d for d in reranked if d.metadata.get("rerank_score", 0.0) >= cutoff], cutoff


def _record_trace(query: str, reranked: list[Document], kept: list[Document],
                  cutoff: float) -> None:
    trace = retrieval_trace.get()
    if trace is None:
        return
    trace.append({
        "query": query,
        "results": [
            {
                "source": d.metadata.get("source"),
                "headers": d.metadata.get("headers"),
                "similarity": d.metadata.get("similarity"),
                "rerank_score": d.metadata.get("rerank_score"),
                "preview": d.page_content[:120],
            }
            for d in reranked
        ],
        "kept": len(kept),
        "cutoff": round(cutoff, 4),
    })


async def search(query: str) -> list[Document]:
    s = get_settings()
    docs = await _vector_search(query, k=s.RETRIEVER_K)
    cutoff = 0.0
    try:
        reranked = await asyncio.to_thread(_rerank, query, docs, s.RERANK_TOP_N)
        kept, cutoff = _apply_cutoff(reranked, s)
    except Exception:
        # Cohere erişilemezse tamamen kör kalma: similarity sırasıyla devam et.
        # Degraded mod — rerank floor uygulanamaz, alakasız chunk sızabilir.
        structlog.get_logger().warning("rerank_failed_fallback", query=query[:80])
        reranked = kept = docs[: s.RERANK_TOP_N]
    kept = await _expand_overviews(kept)
    _record_trace(query, reranked, kept, cutoff)
    return kept
