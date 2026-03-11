import os

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
DATABASE_URL = os.getenv("DATABASE_URL")

if not BOT_TOKEN:
    raise ValueError("❌ BOT_TOKEN не задан в переменных окружения")
if ADMIN_ID == 0:
    raise ValueError("❌ ADMIN_ID не задан в переменных окружения")
if not DATABASE_URL:
    raise ValueError("❌ DATABASE_URL не задан в переменных окружения")
