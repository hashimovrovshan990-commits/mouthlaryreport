import os

BOT_TOKEN = os.getenv("8258447024:AAG2qla6xWlSMPhOdX3klBGVhnP5fb2W2Pk")
ADMIN_ID = int(os.getenv("680001144", "0"))
DATABASE_URL = os.getenv("postgresql://finorra_bot_db_user:YlWveh7SCmzwO8MhgJMcEBLGBxNNP2Mr@dpg-d6o8s46a2pns73bmr0pg-a.oregon-postgres.render.com/finorra_bot_db")

if not BOT_TOKEN:
    raise ValueError("❌ BOT_TOKEN не задан в переменных окружения")
if ADMIN_ID == 0:
    raise ValueError("❌ ADMIN_ID не задан в переменных окружения")
if not DATABASE_URL:
    raise ValueError("❌ DATABASE_URL не задан в переменных окружения")
