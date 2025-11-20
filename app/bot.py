import os
import asyncio
import logging
from typing import Dict, Any
from pathlib import Path
import re

from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, Document
from aiogram.filters import Command
from aiogram.fsm.storage.redis import RedisStorage
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from redis import asyncio as aioredis
from dotenv import load_dotenv

# === Импорты из проекта ===
from .parser import parse_resume, job_description_from_link
from .analyzer import analyze_resume, analyze_message

# === Логирование ===
logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

# === Настройки ===
BASE_DIR = Path(__file__).parent.parent
UPLOAD_DIR = BASE_DIR / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

load_dotenv(BASE_DIR / ".env")
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN не найден в .env")

REDIS_URL = os.getenv("REDIS_URL")
redis = aioredis.from_url(REDIS_URL, decode_responses=True)
storage = RedisStorage(redis)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=storage)

# === FSM ===
class BotStates(StatesGroup):
    idle = State()

# === Очередь задач ===
task_queue: asyncio.Queue[Dict[str, Any]] = asyncio.Queue(maxsize=50)

# === Регулярка для URL ===
URL_REGEX = re.compile(r"(https?://[^\s]+)")

# === Безопасная отправка сообщений ===
async def safe_send(user_id: int, text: str):
    try:
        await bot.send_message(user_id, text)
    except Exception as e:
        log.warning(f"Не удалось отправить сообщение пользователю {user_id}: {e}")

# === Воркеры для обработки очереди ===
async def worker_loop(worker_id: int):
    while True:
        task = await task_queue.get()
        user_id = task["user_id"]
        task_type = task["type"]

        try:
            if task_type == "resume":
                await process_resume(task)
            elif task_type == "link":
                await process_link(task)
            elif task_type == "message":
                await process_message(task)
        except Exception as e:
            log.error(f"[Worker {worker_id}] Ошибка при обработке {task_type} для {user_id}: {e}")
            await safe_send(user_id, "❌ Произошла ошибка при обработке. Попробуйте позже.")
        finally:
            task_queue.task_done()

# === Обработка резюме ===
async def process_resume(task: Dict):
    user_id = task["user_id"]
    file_id = task["file_id"]
    file_name = task["file_name"]

    await safe_send(user_id, "📄 Скачиваю и обрабатываю резюме...")

    file = await bot.get_file(file_id)
    temp_path = UPLOAD_DIR / f"{user_id}_{file_name}"

    try:
        await bot.download_file(file.file_path, temp_path)

        # Парсим резюме в отдельном потоке (тяжёлая операция)
        loop = asyncio.get_running_loop()
        text = await loop.run_in_executor(None, parse_resume, str(temp_path))

        if not text or text.strip() == "":
            await safe_send(user_id, "❌ Не удалось извлечь текст из резюме.")
            return

        await redis.setex(f"resume:{user_id}", 172800, text)
        await safe_send(user_id, "✅ Резюме успешно обработано и сохранено!")

    finally:
        temp_path.unlink(missing_ok=True)

# === Обработка ссылки ===
async def process_link(task: Dict):
    user_id = task["user_id"]
    url = task["url"]

    await safe_send(user_id, "🌐 Получаю описание вакансии...")

    loop = asyncio.get_running_loop()
    job_text = await loop.run_in_executor(None, job_description_from_link, url)

    if job_text == 'NotHH':
        await safe_send(user_id, "⚠️ Неизвестный источник вакансии. Поддерживаются hh.ru")
        return

    if job_text == 'Ошибка_запроса':
        await safe_send(user_id, "⚠️ Не удалось сделать запрос.")
        return

    if not job_text:
        await safe_send(user_id, "❌ Не удалось извлечь текст вакансии.")
        return

    await redis.setex(f"job:{user_id}", 172800, job_text)
    await safe_send(user_id, "✅ Вакансия сохранена!")

    resume_text = await redis.get(f"resume:{user_id}")
    if resume_text:
        await safe_send(user_id, "🤖 Анализирую соответствие резюме и вакансии...")
        result = await analyze_resume(resume_text, user_id)
        await safe_send(user_id, f"🏁 Результат анализа:\n\n{result}")

# === Обработка текстовых сообщений ===
async def process_message(task: Dict):
    user_id = task["user_id"]
    message_text = task["text"]

    await safe_send(user_id, "💬 Анализирую ваш вопрос...")

    resume_text = await redis.get(f"resume:{user_id}")

    if not resume_text:
        await safe_send(user_id, "📎 Резюме не найдено. Пожалуйста, сначала загрузите его.")
        return

    result = await analyze_message(resume_text, user_id, message_text)
    await safe_send(user_id, f"Ответ:\n\n{result}")

# === Хендлеры ===
@dp.message(Command("start"))
async def start(message: Message, state: FSMContext):
    await state.set_state(BotStates.idle)
    await message.answer(
        "Привет! 👋 Я HR-бот.\n\n"
        "Отправь мне резюме (PDF/DOCX), потом ссылку на вакансию или просто вопрос."
    )

@dp.message(F.document)
async def handle_document(message: Message, state: FSMContext):
    document: Document = message.document
    user_id = message.from_user.id

    if not document.file_name.lower().endswith((".pdf", ".docx")):
        await message.reply("❌ Поддерживаются только файлы форматов PDF и DOCX.")
        return

    await message.reply("📥 Файл получен! Добавляю в очередь на обработку...")

    task_data = {
        "user_id": user_id,
        "type": "resume",
        "file_id": document.file_id,
        "file_name": document.file_name
    }
    await task_queue.put(task_data)

@dp.message(F.text.regexp(URL_REGEX))
async def handle_url(message: Message):
    url = message.text.strip()
    user_id = message.from_user.id

    resume_text = await redis.get(f"resume:{user_id}")
    if not resume_text:
        await message.reply("❌ Сначала отправьте резюме.")
        return

    await message.reply("🔗 Обрабатываю ссылку на вакансию...")

    task_data = {
        "user_id": user_id,
        "type": "link",
        "url": url
    }
    await task_queue.put(task_data)

@dp.message(F.text)
async def handle_text(message: Message):
    user_id = message.from_user.id
    task_data = {
        "user_id": user_id,
        "type": "message",
        "text": message.text
    }
    await task_queue.put(task_data)
    await message.reply("🧠 Ваш запрос добавлен в очередь!")

# === Запуск ===
async def on_startup():
    num_workers = 3
    for i in range(num_workers):
        asyncio.create_task(worker_loop(i))
    log.info(f"Бот запущен, запущено {num_workers} воркеров.")

async def main():
    await on_startup()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())