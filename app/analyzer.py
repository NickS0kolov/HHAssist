from langchain_ollama.llms import OllamaLLM
from langchain_core.prompts import ChatPromptTemplate
from dotenv import load_dotenv
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
dotenv_path = os.path.join(BASE_DIR, ".env")
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path)

model_name = os.getenv("OLLAMA_MODEL")
model = OllamaLLM(model=model_name, base_url=os.getenv("OLLAMA_BASE_URL"))

# === Анализ резюме ===
async def analyze_resume(resume_text: str, job_description: str) -> str:
    prompt = ChatPromptTemplate.from_messages([
        ("system", """
Ты — карьерный ассистент, создающий короткие аккуратные ответы для Telegram.
Строго соблюдай формат. Не используй Markdown, HTML, кавычки и знак *.
Не придумывай новых фактов, имён, навыков или компаний.
Работай только с текстами, которые даёт пользователь. Не превышай 1000 символов.
Если в резюме есть имя, используй его. Если нет — не выдумывай.
Не добавляй новых блоков и не меняй структуру.
"""),

        ("human", """
Оцени соответствие резюме вакансии и выдай ответ строго по форме:

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

Вакансия:
{job_description}
""")
    ])

    chain = prompt | model
    result = await chain.ainvoke({
        "resume_text": resume_text,
        "job_description": job_description
    })
    return result

# === Ответ на вопрос кандидата ===
async def analyze_message(resume_text: str, job_description: str, question: str) -> str:
    prompt = ChatPromptTemplate.from_messages([
        ("system", """
Ты — помощник по поиску работы. Отвечай строго по тексту резюме, вакансии и вопроса.
Не используй Markdown, HTML, кавычки и знак *. Не придумывай факты, имена или навыки.
Не подбирай вакансии и не отправляй ссылки.
"""),

        ("human", """
Отвечай кратко, понятно и не длиннее 1250 символов.

Резюме:
{resume_text}

Вакансия:
{job_description}

Вопрос:
{question}

Теперь дай ответ.
""")
    ])

    chain = prompt | model
    result = await chain.ainvoke({
        "resume_text": resume_text,
        "job_description": job_description,
        "question": question
    })
    return result