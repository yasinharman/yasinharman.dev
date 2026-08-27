from functools import lru_cache

from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from supabase import Client, create_client

from .config import get_settings


@lru_cache
def supabase_client() -> Client:
    s = get_settings()
    return create_client(s.SUPABASE_URL, s.SUPABASE_SERVICE_KEY)


@lru_cache
def embeddings() -> OpenAIEmbeddings:
    s = get_settings()
    return OpenAIEmbeddings(model=s.OPENAI_EMBED_MODEL, api_key=s.OPENAI_API_KEY)


# Rol basina ayri LLM: router'in isi siniflandirma, cevap uretmek degil. Yaraticilik
# orada zarar: ayni soru her seferinde ayni kategoriye dusmeli, aksi halde eval'in
# olctugu sey kararsiz olur. Generation tarafinda 0.2 bilerek korunuyor.
@lru_cache
def chat_llm() -> ChatOpenAI:
    s = get_settings()
    return ChatOpenAI(model=s.OPENAI_CHAT_MODEL, temperature=0.2, api_key=s.OPENAI_API_KEY)


@lru_cache
def router_llm() -> ChatOpenAI:
    s = get_settings()
    return ChatOpenAI(model=s.OPENAI_ROUTER_MODEL, temperature=0, api_key=s.OPENAI_API_KEY)


