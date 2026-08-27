"""Ağ gerektirmeyen testler için sahte env — Settings zorunlu alanları doldurulur.

Sahte anahtarlar yalnızca .env YOKKEN yazılır: ortam değişkeni .env'den önce
geldiği için, .env varken bunları set etmek integration testlerinin gerçek
anahtarlarını ezip hepsini 401'e düşürür.
"""
import os

from app.config import ENV_FILE

if not ENV_FILE.exists():
    os.environ.setdefault("OPENAI_API_KEY", "test-key")
    os.environ.setdefault("COHERE_API_KEY", "test-key")
    os.environ.setdefault("SUPABASE_URL", "https://test.supabase.co")
    os.environ.setdefault("SUPABASE_SERVICE_KEY", "test-key")
    os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/test")
    os.environ.setdefault("ADMIN_API_KEY", "test-key")


import pytest


@pytest.fixture(autouse=True)
def _temiz_rate_limiter():
    """Rate limiter süreç ömrü boyunca yaşayan bir singleton; her test kendi kotasıyla
    başlamazsa testler birbirinin kotasını tüketip sıraya bağımlı hale gelir."""
    from app.ratelimit import get_limiter
    get_limiter.cache_clear()
    yield
    get_limiter.cache_clear()
