"""Ağ gerektirmeyen testler için sahte env — Settings zorunlu alanları doldurulur.

Sahte anahtarlar yalnızca .env YOKKEN yazılır: ortam değişkeni .env'den önce
geldiği için, .env varken bunları set etmek integration testlerinin gerçek
anahtarlarını ezip hepsini 401'e düşürür.
"""
import os
from pathlib import Path

if not (Path(__file__).parents[1] / ".env").exists():
    os.environ.setdefault("OPENAI_API_KEY", "test-key")
    os.environ.setdefault("COHERE_API_KEY", "test-key")
    os.environ.setdefault("SUPABASE_URL", "https://test.supabase.co")
    os.environ.setdefault("SUPABASE_SERVICE_KEY", "test-key")
    os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/test")
    os.environ.setdefault("ADMIN_API_KEY", "test-key")
