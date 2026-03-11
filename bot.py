import os
import asyncio
import logging
import traceback
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
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Переменные окружения
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("❌ BOT_TOKEN не задан в переменных окружения")

RENDER_URL = os.getenv("RENDER_EXTERNAL_URL")
PORT = int(os.getenv("PORT", 8000))

# Инициализация бота и диспетчера
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# Подключаем мидлвари и роутеры
dp.message.middleware(AccessMiddleware())
dp.callback_query.middleware(CallbackAccessMiddleware())
dp.include_router(common.router)
dp.include_router(expense.router)
dp.include_router(income.router)
dp.include_router(analytics.router)
dp.include_router(general.router)

# --- Веб-сервер Starlette ---

async def telegram_webhook(request: Request) -> Response:
    logger.info("Получен POST-запрос на /telegram")
    try:
        # Проверим, что база данных доступна (опционально)
        if not db.pool:
            logger.error("Пул базы данных не инициализирован!")
            return Response(status_code=500)

        # Получаем JSON из запроса
        update_data = await request.json()
        logger.debug(f"Получен update: {update_data}")

        # Преобразуем в объект Update
        update = types.Update(**update_data)

        # Передаём в диспетчер
        await dp.feed_update(bot, update)
        logger.info("Update успешно обработан")
        return Response(status_code=200)

    except Exception as e:
        # Логируем полную информацию об ошибке
        logger.error(f"Ошибка при обработке веб-хука: {e}")
        logger.error(traceback.format_exc())
        return Response(status_code=500)

async def health_check(request: Request) -> PlainTextResponse:
    return PlainTextResponse("OK")

async def root(request: Request) -> PlainTextResponse:
    return PlainTextResponse("Bot is running. Webhook path: /telegram")

app = Starlette(routes=[
    Route("/", root, methods=["GET"]),
    Route("/telegram", telegram_webhook, methods=["POST"]),
    Route("/health", health_check, methods=["GET"]),
])

async def on_startup():
    logger.info("Запуск приложения...")
    await db.create_pool()
    webhook_url = f"{RENDER_URL}/telegram"
    logger.info(f"Установка веб-хука на {webhook_url}")

    # Проверим текущий веб-хук
    webhook_info = await bot.get_webhook_info()
    logger.info(f"Текущий веб-хук: {webhook_info.url}")

    if webhook_info.url != webhook_url:
        result = await bot.set_webhook(webhook_url)
        if result:
            logger.info(f"✅ Веб-хук успешно установлен на {webhook_url}")
        else:
            logger.error("❌ Не удалось установить веб-хук")
    else:
        logger.info("Веб-хук уже правильный")

async def on_shutdown():
    logger.info("Остановка приложения...")
    await bot.delete_webhook()
    await bot.session.close()

app.add_event_handler("startup", on_startup)
app.add_event_handler("shutdown", on_shutdown)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=PORT)
