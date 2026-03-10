import os

BOT_TOKEN = os.getenv("8258447024:AAG2qla6xWlSMPhOdX3klBGVhnP5fb2W2Pk")
ADMIN_ID = int(os.getenv("680001144", "0"))

if not BOT_TOKEN:
    raise ValueError("❌ BOT_TOKEN не задан в переменных окружения")
if ADMIN_ID == 0:
    raise ValueError("❌ ADMIN_ID не задан в переменных окружения")
