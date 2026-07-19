"""Ağ gerektirmeyen testler için sahte env — Settings zorunlu alanları doldurulur."""
import os

os.environ.setdefault("OPENAI_API_KEY", "test-key")
os.environ.setdefault("COHERE_API_KEY", "test-key")
os.environ.setdefault("SUPABASE_URL", "https://test.supabase.co")
os.environ.setdefault("SUPABASE_SERVICE_KEY", "test-key")
os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/test")
os.environ.setdefault("ADMIN_API_KEY", "test-key")
