from functools import lru_cache
from langchain_community.vectorstores import SupabaseVectorStore
from langchain.retrievers import ContextualCompressionRetriever
from .config import get_settings
from .deps import supabase_client, embeddings, cohere_reranker


@lru_cache
def vector_store() -> SupabaseVectorStore:
    s = get_settings()
    return SupabaseVectorStore(
        client=supabase_client(),
        embedding=embeddings(),
        table_name=s.SUPABASE_TABLE,
        query_name=s.SUPABASE_QUERY_NAME,
    )


@lru_cache
def retriever() -> ContextualCompressionRetriever:
    s = get_settings()
    base = vector_store().as_retriever(search_kwargs={"k": s.RETRIEVER_K})
    return ContextualCompressionRetriever(base_compressor=cohere_reranker(), base_retriever=base)
