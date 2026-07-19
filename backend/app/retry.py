"""Retry policy for external calls (OpenAI embeddings, Cohere, Supabase REST).

LLM chat çağrılarına uygulanmaz — OpenAI SDK'sı kendi retry'ını yapıyor.
"""
from tenacity import retry, stop_after_attempt, wait_exponential

external_retry = retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=0.5, max=4),
    reraise=True,
)
