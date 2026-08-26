from typing import Literal

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=1000)
    session_id: str = Field(min_length=1, max_length=128)
    # Cevabin yazilacagi dil. Bilgi tabani Turkce oldugu icin retrieval her
    # zaman Turkce yapilir; bu alan yalnizca cikti dilini degistirir.
    lang: Literal["tr", "en"] = "tr"


class ChatResponse(BaseModel):
    response: str
    blocked: bool = False


class IngestPathRequest(BaseModel):
    # Yalnizca backend/data/ altindaki yollar kabul edilir (routes/admin.py).
    # wipe alani bilerek YOK: tum korpusu silmek yalnizca CLI'dan yapilabilir
    # (python -m app.ingest ... --wipe), yani sunucu erisimi gerektirir.
    path: str
    source: str | None = None
