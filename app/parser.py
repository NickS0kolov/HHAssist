import os
import pdfplumber
import docx

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
