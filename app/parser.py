import os
import pdfplumber
import docx
import requests
from bs4 import BeautifulSoup
import re
from urllib.parse import urlparse

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
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/118.0.5993.90 Safari/537.36"
        )
    }

    domain = urlparse(url).netloc.lower()

    # Проверяем, что это именно hh.ru (и поддомены)
    if not (domain.endswith("hh.ru") or domain.endswith("hh.kz") or domain.endswith("hh.ua")):
        return "NotHH"

    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
    except requests.RequestException as e:
        return "Ошибка_запроса"

    soup = BeautifulSoup(response.text, "html.parser")

    desc_block = soup.find("div", {"data-qa": "vacancy-description"})
    if not desc_block:
        return None

    text = desc_block.get_text(separator="\n", strip=True)
    text = _clean_text(text)
    return text


def _clean_text(text: str) -> str:
    """Удаляет лишние пробелы, ссылки и спецсимволы из описания"""
    text = re.sub(r"http\S+", "", text)  # убрать URL
    text = re.sub(r"\s+", " ", text).strip()
    text = re.sub(r"[\u200b\u200c\u200d\uFEFF]", "", text)  # невидимые символы
    return text