import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from config import BOT_TOKEN
from database import init_db
from handlers import common, expense, income, analytics, general
from middlewares import AccessMiddleware, CallbackAccessMiddleware  # импорт

logging.basicConfig(level=logging.INFO)

async def main():
    init_db()
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())
    
    # Регистрируем мидлвари ДО подключения роутеров
    dp.message.middleware(AccessMiddleware())
    dp.callback_query.middleware(CallbackAccessMiddleware())
    
    dp.include_router(common.router)
    dp.include_router(expense.router)
    dp.include_router(income.router)
    dp.include_router(analytics.router)
    dp.include_router(general.router)
    
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())