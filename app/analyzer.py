from langchain_ollama.llms import OllamaLLM
from langchain_core.prompts import ChatPromptTemplate

# Инициализация модели Ollama
model_name = "mistral"  # или любая другая скачанная модель
model = OllamaLLM(model=model_name)

def analyze_resume(resume_text: str, job_description: str) -> str:
    prompt = f"""
    Ты HR, оцени резюме и вакансию.
    
    Резюме:
    {resume_text}
    
    Вакансия:
    {job_description}
    """
    
    question = """
        Задачи:
        1. Перечисли совпадающие навыки и опыт.
        2. Перечисли недостающие навыки.
        3. Дай оценку вероятности успешного отклика (в процентах).
        4. Напиши короткое сопроводительное письмо, основанное на резюме и вакансии.
        
        Ответи структурированно, разделяя пункты.
        """
    
    prompt = ChatPromptTemplate.from_template(prompt)
    chain = prompt | model
    
    result = chain.invoke({"reviews":[], "question": question})
    return result