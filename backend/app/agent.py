"""LangChain agent with portfolio knowledge-base tool.

NOTE: SYSTEM_PROMPT below is a placeholder — replace with the exact AI Agent
system prompt from the original n8n workflow before going to production.
"""
from functools import lru_cache
from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain.tools import Tool
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from .deps import chat_llm
from .retriever import retriever


SYSTEM_PROMPT = (
    "Sen Yasin Harman'ın portfolyo sitesindeki AI asistansın. Türkçe ve İngilizce sorulara cevap verirsin. "
    "Yasin'in projeleri, deneyimi, yetenekleri ve geçmişi hakkında bilgi verirsin. "
    "Cevap üretmeden önce mutlaka 'portfolio_kb' aracını kullanarak ilgili bilgiyi getir. "
    "Bilgi yoksa uydurma — bilmediğini dürüstçe söyle. Kısa, net ve samimi konuş."
)


def _format_docs(docs) -> str:
    return "\n\n---\n\n".join(d.page_content for d in docs) if docs else "Sonuç bulunamadı."


async def _kb_search(query: str) -> str:
    docs = await retriever().ainvoke(query)
    return _format_docs(docs)


def _kb_search_sync(query: str) -> str:
    docs = retriever().invoke(query)
    return _format_docs(docs)


@lru_cache
def agent_executor() -> AgentExecutor:
    kb_tool = Tool(
        name="portfolio_kb",
        description=(
            "Yasin Harman'ın projeleri, yetenekleri, iş deneyimi, eğitimi hakkında "
            "bilgi getirir. Kullanıcı sorusuyla ilgili anahtar kelimeleri sorgu olarak ver."
        ),
        func=_kb_search_sync,
        coroutine=_kb_search,
    )
    prompt = ChatPromptTemplate.from_messages([
        ("system", SYSTEM_PROMPT),
        MessagesPlaceholder("history", optional=True),
        ("human", "{input}"),
        MessagesPlaceholder("agent_scratchpad"),
    ])
    agent = create_openai_tools_agent(chat_llm(), [kb_tool], prompt)
    return AgentExecutor(agent=agent, tools=[kb_tool], verbose=False, max_iterations=4)
