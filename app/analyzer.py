from langchain_ollama import ChatOllama
from langchain.agents import create_agent
from langchain.tools import tool, ToolRuntime
from dotenv import load_dotenv
from redis import asyncio as aioredis
from langgraph.checkpoint.memory import InMemorySaver
from dataclasses import dataclass
from langchain.messages import HumanMessage
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
dotenv_path = os.path.join(BASE_DIR, ".env")
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path)

REDIS_URL = os.getenv("REDIS_URL")
redis = aioredis.from_url(REDIS_URL, decode_responses=True)

@dataclass
class Context:
    user_id: str

@tool
async def get_vacancy_text(runtime: ToolRuntime[Context]) -> str:
    """
    Используется для получения актуального текста вакансии используя Runtime Context
    """
    user_id = runtime.context.user_id
    job_text = await redis.get(f"job:{user_id}") or "Вакансия не была прислана"
    return job_text


SYSTEM_PROMPT = """
Ты — карьерный ассистент, создающий короткие аккуратные ответы для Telegram.
Строго соблюдай формат. Не используй Markdown, HTML, кавычки и знак *.
Не придумывай новых фактов, имён, навыков или компаний.
Работай только с текстами, которые даёт пользователь. Не превышай 1000 символов.
Если в резюме есть имя, используй его. Если нет — не выдумывай.
Не добавляй новых блоков и не меняй структуру.
Не подбирай вакансии и не отправляй ссылки.
Для получения актуального текста вакансии используй get_vacancy_text
"""

model_name = os.getenv("OLLAMA_MODEL")
agent = create_agent(
    model = ChatOllama(model=model_name, base_url=os.getenv("OLLAMA_BASE_URL")),
    tools=[get_vacancy_text],
    system_prompt=SYSTEM_PROMPT,
    context_schema=Context,
    checkpointer = InMemorySaver()
)

# === Анализ резюме ===
async def analyze_resume(resume_text: str, user_id: int) -> str:
    human_message = HumanMessage(f"""
Перед тем как что-либо делать, обязательно вызови инструмент get_vacancy_text,
чтобы получить текст вакансии. Не продолжай работу, пока не получишь текст вакансии.
Оцени соответствие резюме и вакансии и выдай ответ строго по форме:

📋 Совпадения:
(2–3 коротких пункта)

⚠️ Недостает:
(2–3 коротких пункта)

🎯 Вероятность успеха: XX%

💡 Советы:
(нумерованный список из 3–4 рекомендаций)

✉️ Сопроводительное письмо:
(2–3 коротких абзаца, дружелюбно и профессионально)

Резюме:
{resume_text}
""")
    
    result = await agent.ainvoke(
        {"messages": [human_message]},
        {"configurable": {"thread_id": str(user_id)}},
        context=Context(
            user_id=user_id
        )
    )
    return result["messages"][-1].content

# === Ответ на вопрос кандидата ===
async def analyze_message(resume_text: str, user_id:int, question: str) -> str:
    human_message = HumanMessage(f"""
Отвечай кратко, понятно и не длиннее 1250 символов.
Вызови инструмент get_vacancy_text, чтобы получить текст актуальной вакансии.
Всегда вызывай инструмент get_vacancy_text перед ответом, если вопрос связан с вакансией.

Резюме:
{resume_text}

Вопрос:
{question}

Теперь дай ответ.
""")
    
    result = await agent.ainvoke(
        {"messages": [human_message]},
        {"configurable": {"thread_id": str(user_id)}},
        context=Context(
            user_id=user_id
        )
    )
    return result["messages"][-1].content