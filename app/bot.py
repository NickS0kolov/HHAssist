import os
import asyncio
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message
from aiogram.fsm.storage.redis import RedisStorage
from redis import asyncio as aioredis
from dotenv import load_dotenv

from app.parser import parse_resume
from app.analyzer import analyze_resume


# === Настройки ===
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

# === Загружаем .env ===
dotenv_path = os.path.join(BASE_DIR, ".env")
if os.path.exists(dotenv_path):
    print(f"Загружаем переменные окружения из {dotenv_path}")
    load_dotenv(dotenv_path)
else:
    print("⚠️ .env файл не найден!")

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("❌ TELEGRAM_BOT_TOKEN не найден в .env")

# === Redis (асинхронный) ===
# Если бот запущен на ПК, а Redis в Docker — оставь localhost
# Если оба в Docker — используй host="redis"
REDIS_URL = os.getenv("REDIS_URL")
redis = aioredis.from_url(REDIS_URL, decode_responses=True)
storage = RedisStorage(redis)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=storage)


# === Обработка файлов ===
@dp.message(F.document)
async def handle_resume(message: Message):
    document = message.document

    if not document.file_name.lower().endswith((".pdf", ".docx")):
        await message.reply("⚠️ Поддерживаются только файлы PDF или DOCX.")
        return

    file_path = os.path.join(UPLOAD_DIR, document.file_name)
    await bot.download(document, destination=file_path)
    await message.reply("📄 Файл загружен, начинаю обработку...")

    text = parse_resume(file_path)
    if not text:
        await message.reply("❌ Не удалось извлечь текст из резюме.")
        return

    user_key = f"resume:{message.from_user.id}"
    await redis.setex(user_key, 172800, text)

    await message.reply("✅ Резюме успешно обработано и сохранено.")
    
    
@dp.message(F.text)
async def handle_job_link(message: Message):
    job_description = message.text

    # Получаем текст резюме из Redis
    user_key = f"resume:{message.from_user.id}"
    resume_text = await redis.get(user_key)

    if not resume_text:
        await message.reply("⚠️ Резюме не найдено. Сначала отправьте своё резюме.")
        return

    await message.reply("🔍 Анализирую резюме и вакансию... это займёт пару минут.")
    
    result = analyze_resume(resume_text, job_description)

    await message.reply(f"📊 Результаты анализа:\n\n{result}")



# === Точка входа ===
async def main():
    print("🤖 Бот запущен...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
