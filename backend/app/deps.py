from functools import lru_cache
from supabase import create_client, Client
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_cohere import CohereRerank
from .config import get_settings


@lru_cache
def supabase_client() -> Client:
    s = get_settings()
    return create_client(s.SUPABASE_URL, s.SUPABASE_SERVICE_KEY)


@lru_cache
def embeddings() -> OpenAIEmbeddings:
    s = get_settings()
    return OpenAIEmbeddings(model=s.OPENAI_EMBED_MODEL, api_key=s.OPENAI_API_KEY)


@lru_cache
def chat_llm() -> ChatOpenAI:
    s = get_settings()
    return ChatOpenAI(model=s.OPENAI_CHAT_MODEL, temperature=0.2, api_key=s.OPENAI_API_KEY)


@lru_cache
def guard_llm() -> ChatOpenAI:
    s = get_settings()
    return ChatOpenAI(model=s.OPENAI_GUARD_MODEL, temperature=0.0, api_key=s.OPENAI_API_KEY)


@lru_cache
def cohere_reranker() -> CohereRerank:
    s = get_settings()
    return CohereRerank(
        model=s.COHERE_RERANK_MODEL,
        top_n=s.RERANK_TOP_N,
        cohere_api_key=s.COHERE_API_KEY,
    )
