from langchain_ollama import ChatOllama
from langgraph.graph import MessagesState, START, StateGraph
from langgraph.prebuilt import tools_condition
from dotenv import load_dotenv
from redis import asyncio as aioredis
from langgraph.checkpoint.memory import InMemorySaver
from langchain.messages import HumanMessage, SystemMessage, ToolMessage
from pydantic import BaseModel
from langchain_core.tools import StructuredTool
import os

# === Настройка окружения ===
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
dotenv_path = os.path.join(BASE_DIR, ".env")
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path)

REDIS_URL = os.getenv("REDIS_URL")
redis = aioredis.from_url(REDIS_URL, decode_responses=True)


# === Состояние агента ===
class AgentState(MessagesState):
    user_id: str


# === TOOL: Получить текст вакансии ===
async def _get_vacancy_text(user_id: str) -> str:
    """Возвращает текст вакансии из Redis."""
    job_text = await redis.get(f"job:{user_id}")
    return job_text or "Вакансия не была прислана"


class VacancyText(BaseModel):
    """Пустая schema — инструменту не нужны входные аргументы.
    user_id будет автоматически подставлен."""
    pass


llm_tools = [
    StructuredTool.from_function(
        func=_get_vacancy_text,
        coroutine=_get_vacancy_text,
        name="VacancyText",
        args_schema=VacancyText,
        description="Получение актуального текста вакансии"
    )
]

# Mаппинг для кастомного исполнителя
tool_map = {
    "VacancyText": _get_vacancy_text,
}


# === Исполнитель инструментов ===
async def tool_executor(state: AgentState) -> dict:
    tool_calls = state["messages"][-1].tool_calls
    tool_messages = []

    user_id = state['user_id']

    for call in tool_calls:
        tool_name = call["name"]
        tool_func = tool_map[tool_name]

        # Функция не требуют аргументов кроме user_id
        response = await tool_func(user_id=user_id)

        tool_messages.append(
            ToolMessage(
                content=str(response),
                tool_call_id=call["id"],
            )
        )

    return {"messages": tool_messages}


# === LLM ===
model_name = os.getenv("OLLAMA_MODEL")
llm = ChatOllama(model=model_name, base_url=os.getenv("OLLAMA_BASE_URL"))
llm_with_tools = llm.bind_tools(llm_tools)


# === System Prompt ===
SYSTEM_PROMPT = SystemMessage(content="""
Ты — карьерный ассистент, создающий короткие аккуратные ответы для Telegram.
Строго соблюдай формат. Не используй Markdown, HTML, кавычки и знак *.
Не придумывай новых фактов, имён, навыков или компаний.
Работай только с текстами, которые даёт пользователь. Не превышай 1000 символов.
Если в резюме есть имя, используй его. Если нет — не выдумывай.
Не добавляй новых блоков и не меняй структуру.
Не подбирай вакансии и не отправляй ссылки.
Для получения актуального текста вакансии используй VacancyText.
""")


# === Node Reasoner ===
def reasoner(state: AgentState):
    return {
        "messages": [llm_with_tools.invoke([SYSTEM_PROMPT] + state["messages"])],
    }


# === Строим граф ===
builder = StateGraph(AgentState)

builder.add_node("reasoner", reasoner)
builder.add_node("tools", tool_executor)

builder.add_edge(START, "reasoner")
builder.add_conditional_edges("reasoner", tools_condition)
builder.add_edge("tools", "reasoner")

react_graph = builder.compile(InMemorySaver())


# === API-функции ===
async def analyze_resume(resume_text: str, user_id: int) -> str:
    hm = HumanMessage(f"""
Перед тем как что-либо делать, обязательно вызови инструмент VacancyText,
чтобы получить текст вакансии.
Не продолжай работу, пока не получишь текст вакансии.
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

    result = await react_graph.ainvoke(
        {"messages": [hm], "user_id": str(user_id)},
        {"configurable": {"thread_id": str(user_id)}}
    )

    return result["messages"][-1].content


async def analyze_message(resume_text: str, user_id: int, question: str) -> str:
    hm = HumanMessage(f"""
Отвечай кратко, понятно и не длиннее 1250 символов.
Перед ответом вызови инструмент VacancyText.

Резюме:
{resume_text}

Вопрос:
{question}

Теперь дай ответ.
""")

    result = await react_graph.ainvoke(
        {"messages": [hm], "user_id": str(user_id)},
        {"configurable": {"thread_id": str(user_id)}}
    )

    return result["messages"][-1].content
