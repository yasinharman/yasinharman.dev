from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    session_id: str = Field(min_length=1, max_length=128)


class ChatResponse(BaseModel):
    response: str
    blocked: bool = False


class IngestPathRequest(BaseModel):
    path: str
    source: str | None = None
