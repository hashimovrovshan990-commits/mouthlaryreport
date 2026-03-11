import os
import asyncio
import logging
from starlette.applications import Starlette
from starlette.responses import Response, PlainTextResponse
from starlette.requests import Request
from starlette.routing import Route
import uvicorn
from aiogram import Bot, Dispatcher, types
from aiogram.fsm.storage.memory import MemoryStorage
from middlewares import AccessMiddleware, CallbackAccessMiddleware
from handlers import common, expense, income, analytics, general
from database import db

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# Переменные окружения
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("❌ BOT_TOKEN не задан в переменных окружения")

# URL вашего сервиса на Render (он сам подставится)
RENDER_URL = os.getenv("RENDER_EXTERNAL_URL")
PORT = int(os.getenv("PORT", 8000))

# Инициализация бота и диспетчера
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# Подключаем мидлвари и роутеры (как и раньше)
dp.message.middleware(AccessMiddleware())
dp.callback_query.middleware(CallbackAccessMiddleware())
dp.include_router(common.router)
dp.include_router(expense.router)
dp.include_router(income.router)
dp.include_router(analytics.router)
dp.include_router(general.router)

# --- Веб-сервер Starlette для приёма веб-хуков ---

async def telegram_webhook(request: Request) -> Response:
    """Обрабатывает входящие запросы от Telegram."""
    try:
        update_data = await request.json()
        update = types.Update(**update_data)
        await dp.feed_update(bot, update)
        return Response(status_code=200)
    except Exception as e:
        logging.error(f"Ошибка при обработке веб-хука: {e}")
        return Response(status_code=500)

async def health_check(request: Request) -> PlainTextResponse:
    """Health check для Render. Если не ответить 200, Render решит, что сервис упал."""
    return PlainTextResponse("OK")

# Создаём Starlette приложение с двумя маршрутами
app = Starlette(routes=[
    Route("/telegram", telegram_webhook, methods=["POST"]),
    Route("/health", health_check, methods=["GET"]),
])

async def on_startup():
    """Действия при запуске: подключение к БД и установка веб-хука."""
    await db.create_pool()
    webhook_url = f"{RENDER_URL}/telegram"
    await bot.set_webhook(webhook_url)
    logging.info(f"Веб-хук установлен на {webhook_url}")

async def on_shutdown():
    """Действия при остановке: удаление веб-хука."""
    await bot.delete_webhook()
    await bot.session.close()

# Привязываем события к приложению Starlette
app.add_event_handler("startup", on_startup)
app.add_event_handler("shutdown", on_shutdown)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=PORT)
