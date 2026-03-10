from aiogram import Router, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
import keyboards as kb
from database import add_user, get_balance

router = Router()

@router.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()
    user = message.from_user
    add_user(user.id, user.username, user.first_name)
    await message.answer(
        f"Привет, {user.first_name}! Добро пожаловать в финансовый бот.\n"
        "Используй меню для учёта доходов и расходов.",
        reply_markup=kb.main_menu
    )

@router.message(lambda msg: msg.text == "💰 Баланс")
async def show_balance(message: types.Message):
    balance, income, expense = get_balance(message.from_user.id)
    text = (f"💰 Текущий баланс: *{balance:.2f} AZN*\n\n"
            f"📈 Доходы: {income:.2f} AZN\n"
            f"📉 Расходы: {expense:.2f} AZN")
    await message.answer(text, parse_mode="Markdown")

@router.message(lambda msg: msg.text == "◀️ Назад")
async def back_to_main(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("Главное меню", reply_markup=kb.main_menu)

@router.message(Command("myid"))
async def cmd_myid(message: types.Message):
    await message.answer(f"Ваш user_id: {message.from_user.id}")