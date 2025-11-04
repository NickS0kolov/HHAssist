from langchain_ollama.llms import OllamaLLM
from langchain_core.prompts import ChatPromptTemplate
from dotenv import load_dotenv
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
dotenv_path = os.path.join(BASE_DIR, ".env")
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path)

model_name = os.getenv("OLLAMA_MODEL")

model = OllamaLLM(model=model_name)

def analyze_resume(resume_text: str, job_description: str) -> str:
    prompt = f"""
    Ты помощник для поиска работы, тебе пишет кандидат, оцени резюме к вакансии.
    
    Резюме:
    {resume_text}
    
    Вакансия:
    {job_description}

    
    Задачи:
    1. Перечисли совпадающие навыки и опыт.
    2. Перечисли недостающие навыки.
    3. Дай оценку вероятности успешного отклика (в процентах).
    4. Дай советы для улучшения совместимости.
    4. Напиши короткое сопроводительное письмо, которое сможет использовать кандидат, откликаясь на вакансию.
    Сделай это основываясь на резюме и вакансии.
        
    Ответь только по пунктам Заданным пунктам, ответ должен быть короткий и структурированный.
    """
    
    prompt = ChatPromptTemplate.from_template(prompt)
    chain = prompt | model
    
    result = chain.invoke({"resume_text":resume_text, "job_description": job_description})
    return result

def analyze_message(resume_text: str, job_description: str, question: str):
    prompt = '''
    Ты омощник для поиска работы, тебе пишет кандидат который ищет работу, твоя задача ответить на вопрос кандидата, основываясь на его резюме.
    Если присутствует текст вакансии ты должен учитывать вакансию.

    Резюме:
    {resume_text}
    
    Вакансия:
    {job_description}

    Вопрос:
    {question}

    Ответь на вопрос кандидата коротко и структурированно, при необходимости попроси прислать вакансию для лучшего ответа. 
    Если недостаточно данных для ответа на заданный вопрос, спрашивай уточняющие вопросы.
    '''

    prompt = ChatPromptTemplate.from_template(prompt)
    chain = prompt | model
    
    result = chain.invoke({"resume_text":resume_text, "job_description": job_description, "question":question})
    return result