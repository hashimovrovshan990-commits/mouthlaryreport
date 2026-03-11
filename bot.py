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

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("❌ BOT_TOKEN не задан в переменных окружения")

# TeleBotHost предоставляет внешний URL через переменную APP_URL или подобную
# Уточните в документации TeleBotHost, но часто можно использовать PUBLIC_URL
# Если такой переменной нет, то webhook нужно будет установить вручную после деплоя.
# Пока оставим как было для Render, но можно заменить на os.getenv("PUBLIC_URL")
RENDER_URL = os.getenv("RENDER_EXTERNAL_URL")  # TeleBotHost может использовать другую переменную
# Для безопасности сделаем так: если PUBLIC_URL есть, используем его, иначе берём из переменной.
PUBLIC_URL = os.getenv("PUBLIC_URL", os.getenv("RENDER_EXTERNAL_URL"))
if not PUBLIC_URL:
    raise ValueError("❌ PUBLIC_URL (или RENDER_EXTERNAL_URL) не задан в переменных окружения")

PORT = int(os.getenv("PORT", 10000))

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

dp.message.middleware(AccessMiddleware())
dp.callback_query.middleware(CallbackAccessMiddleware())
dp.include_router(common.router)
dp.include_router(expense.router)
dp.include_router(income.router)
dp.include_router(analytics.router)
dp.include_router(general.router)

async def telegram_webhook(request: Request) -> Response:
    logger.info("Получен POST-запрос на /telegram")
    try:
        if not db.pool:
            logger.error("Пул базы данных не инициализирован!")
            return Response(status_code=500)

        update_data = await request.json()
        update = types.Update(**update_data)
        await dp.feed_update(bot, update)
        logger.info("Update успешно обработан")
        return Response(status_code=200)

    except Exception as e:
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
    # Подключение к БД с повторными попытками
    max_retries = 3
    for attempt in range(max_retries):
        try:
            await db.create_pool()
            logger.info("✅ База данных PostgreSQL подключена")
            break
        except Exception as e:
            if attempt == max_retries - 1:
                logger.error(f"❌ Не удалось подключиться к БД после {max_retries} попыток: {e}")
                raise
            logger.warning(f"⚠️ Попытка {attempt+1}/{max_retries} подключения к БД не удалась, повтор через 2с")
            await asyncio.sleep(2)

    # Установка веб-хука
    webhook_url = f"{PUBLIC_URL}/telegram"
    logger.info(f"Установка веб-хука на {webhook_url}")

    try:
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
    except Exception as e:
        logger.error(f"Ошибка при установке веб-хука: {e}")
        logger.error(traceback.format_exc())

async def on_shutdown():
    logger.info("Остановка приложения...")
    try:
        await bot.delete_webhook()
        await bot.session.close()
    except Exception as e:
        logger.error(f"Ошибка при завершении: {e}")

app.add_event_handler("startup", on_startup)
app.add_event_handler("shutdown", on_shutdown)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=PORT)import os
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

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("❌ BOT_TOKEN не задан в переменных окружения")

RENDER_URL = os.getenv("RENDER_EXTERNAL_URL")
PORT = int(os.getenv("PORT", 10000))

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

dp.message.middleware(AccessMiddleware())
dp.callback_query.middleware(CallbackAccessMiddleware())
dp.include_router(common.router)
dp.include_router(expense.router)
dp.include_router(income.router)
dp.include_router(analytics.router)
dp.include_router(general.router)

async def telegram_webhook(request: Request) -> Response:
    logger.info("Получен POST-запрос на /telegram")
    try:
        if not db.pool:
            logger.error("Пул базы данных не инициализирован!")
            return Response(status_code=500)

        update_data = await request.json()
        logger.debug(f"Получен update: {update_data}")

        update = types.Update(**update_data)
        await dp.feed_update(bot, update)
        logger.info("Update успешно обработан")
        return Response(status_code=200)

    except Exception as e:
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
    max_retries = 3
    for attempt in range(max_retries):
        try:
            await db.create_pool()
            logger.info("✅ База данных PostgreSQL подключена")
            break
        except Exception as e:
            if attempt == max_retries - 1:
                logger.error(f"❌ Не удалось подключиться к БД после {max_retries} попыток: {e}")
                raise
            logger.warning(f"⚠️ Попытка {attempt+1}/{max_retries} подключения к БД не удалась, повтор через 2с")
            await asyncio.sleep(2)

    webhook_url = f"{RENDER_URL}/telegram"
    logger.info(f"Установка веб-хука на {webhook_url}")

    try:
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
    except Exception as e:
        logger.error(f"Ошибка при установке веб-хука: {e}")
        logger.error(traceback.format_exc())

async def on_shutdown():
    logger.info("Остановка приложения...")
    try:
        await bot.delete_webhook()
        await bot.session.close()
    except Exception as e:
        logger.error(f"Ошибка при завершении: {e}")

app.add_event_handler("startup", on_startup)
app.add_event_handler("shutdown", on_shutdown)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=PORT)

