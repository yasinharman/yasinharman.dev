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
    path: str
    source: str | None = None
    wipe: bool = False
