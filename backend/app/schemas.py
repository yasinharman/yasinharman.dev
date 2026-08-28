from typing import Literal

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    # Semadaki sinir MAX_INPUT_LENGTH'ten (1000) bilerek genis: ikisi esitken
    # 1000'i asan her mesaj FastAPI dogrulamasinda 422 oluyordu, yani route'a hic
    # girmiyordu. Sonuc: input_guard'in too_long dali OLU kod, olay chat_logs'a
    # HIC yazilmiyor ve kullanici "tekrar deneyin" diyen yanlis bir mesaj aliyordu.
    # Artik 1000-4000 arasi guard'in isi: dogru mesaj + loglanan bir satir.
    # 4000 ustu yine 422 — govde boyutu icin bir tavan gerekiyor.
    message: str = Field(min_length=1, max_length=4000)
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
