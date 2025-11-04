import os
import pdfplumber
import docx
import requests
from bs4 import BeautifulSoup
import re

def extract_text_from_pdf(file_path: str) -> str:
    """Извлекает текст из PDF файла"""
    text = ""
    try:
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                text += page.extract_text() or ""
    except Exception as e:
        print(f"[PDF ERROR] Не удалось прочитать {file_path}: {e}")
    return text.strip()

def extract_text_from_docx(file_path: str) -> str:
    """Извлекает текст из DOCX файла"""
    text = ""
    try:
        doc = docx.Document(file_path)
        for para in doc.paragraphs:
            text += para.text + "\n"
    except Exception as e:
        print(f"[DOCX ERROR] Не удалось прочитать {file_path}: {e}")
    return text.strip()

def parse_resume(file_path: str) -> str:
    """Определяет тип файла и возвращает текст"""
    ext = os.path.splitext(file_path)[-1].lower()
    if ext == ".pdf":
        return extract_text_from_pdf(file_path)
    elif ext == ".docx":
        return extract_text_from_docx(file_path)
    else:
        raise ValueError("Неподдерживаемый формат файла")


def job_description_from_link(url: str) -> str:
    """
    Получает и возвращает текст описания вакансии по ссылке (hh.ru или linkedin.com).
    Возвращает уже очищенный, читаемый текст.
    """
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/118.0.5993.90 Safari/537.36"
        )
    }

    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
    except requests.RequestException as e:
        return f"⚠️ Ошибка запроса: {e}"

    soup = BeautifulSoup(response.text, "html.parser")

    text = None

    # --- HH.RU ---
    if "hh.ru" in url:
        desc_block = soup.find("div", {"data-qa": "vacancy-description"})
        if desc_block:
            text = desc_block.get_text(separator="\n", strip=True)

    # --- LINKEDIN ---
    elif "linkedin.com" in url:
        desc_block = soup.find("div", class_=re.compile(r"show-more-less-html__markup"))
        if desc_block:
            text = desc_block.get_text(separator="\n", strip=True)

    # --- Неизвестный сайт ---
    else:
        return "⚠️ Неизвестный источник вакансии. Поддерживаются hh.ru и linkedin.com."

    if not text:
        return "⚠️ Не удалось извлечь описание вакансии (страница может требовать авторизацию)."

    # Очистка текста
    text = _clean_text(text)
    return text


def _clean_text(text: str) -> str:
    """Удаляет лишние пробелы, ссылки и спецсимволы из описания"""
    text = re.sub(r"http\S+", "", text)  # убрать URL
    text = re.sub(r"\s+", " ", text).strip()
    text = re.sub(r"[\u200b\u200c\u200d\uFEFF]", "", text)  # невидимые символы
    return text