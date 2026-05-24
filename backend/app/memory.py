from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, BaseMessage
from .db import pool


async def append_message(session_id: str, role: str, content: str) -> None:
    async with pool().acquire() as conn:
        await conn.execute(
            "INSERT INTO chat_messages (session_id, role, content) VALUES ($1, $2, $3)",
            session_id, role, content,
        )


async def get_history(session_id: str, limit: int) -> list[BaseMessage]:
    # ADIM 5: Bu session'ın son N mesajını DB'den al (DESC + reverse: "en yeni N" kronolojik sırada) ve LangChain mesaj objelerine dönüştür.
    async with pool().acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT role, content FROM chat_messages
            WHERE session_id = $1
            ORDER BY id DESC
            LIMIT $2
            """,
            session_id, limit,
        )
    rows.reverse()
    out: list[BaseMessage] = []
    for r in rows:
        role, content = r["role"], r["content"]
        if role == "user":
            out.append(HumanMessage(content=content))
        elif role == "assistant":
            out.append(AIMessage(content=content))
        elif role == "system":
            out.append(SystemMessage(content=content))
    return out
