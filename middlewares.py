from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery
from typing import Callable, Dict, Any, Awaitable
from config import ADMIN_ID

class AccessMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: Dict[str, Any]
    ) -> Any:
        if event.from_user.id != ADMIN_ID:
            await event.answer("⛔ У вас нет доступа к этому боту.")
            return
        return await handler(event, data)

class CallbackAccessMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[CallbackQuery, Dict[str, Any]], Awaitable[Any]],
        event: CallbackQuery,
        data: Dict[str, Any]
    ) -> Any:
        if event.from_user.id != ADMIN_ID:
            await event.answer("У вас нет доступа", show_alert=True)
            return
        return await handler(event, data)
