from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
import keyboards as kb
from states import GeneralChoice
from database import db
from calendar_utils import generate_calendar, process_calendar_callback, generate_year_selector
from datetime import datetime, timedelta
import utils

router = Router()

@router.message(lambda msg: msg.text == "📅 Общий")
async def general_main(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    balance, total_income, total_expense = await db.get_balance(user_id)
    earnings = await db.get_total_by_category(user_id, 'income', 'заработок')

    text = (
        f"💰 *Основной баланс:*\n"
        f"*{balance:.2f} AZN*\n\n"
        f"📉 Расходы: {total_expense:.2f} AZN\n"
        f"📈 Доходы: {total_income:.2f} AZN\n"
        f"💸 Заработок: {earnings:.2f} AZN"
    )

    period_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📅 День", callback_data="gen_day"),
         InlineKeyboardButton(text="📅 Месяц", callback_data="gen_month")],
        [InlineKeyboardButton(text="📅 Год", callback_data="gen_year"),
         InlineKeyboardButton(text="🕒 Последние 10", callback_data="gen_recent")],
        [InlineKeyboardButton(text="❌ Закрыть", callback_data="gen_cancel")]
    ])

    await message.answer(text, parse_mode="Markdown", reply_markup=period_kb)

@router.callback_query(F.data.startswith("gen_"))
async def general_choice_callback(callback: CallbackQuery, state: FSMContext):
    action = callback.data.replace("gen_", "")
    if action == "cancel":
        await state.clear()
        await callback.message.delete()
        await callback.message.answer("Главное меню", reply_markup=kb.main_menu)
        await callback.answer()
        return
    elif action == "recent":
        await show_recent(callback.message)
        await callback.answer()
        return

    await state.update_data(period_type=action)
    await state.set_state(GeneralChoice.choosing)

    today = datetime.now()
    calendar = await generate_calendar(today.year, today.month)
    if action == "day":
        await callback.message.edit_text("Выберите день:", reply_markup=calendar)
    elif action == "month":
        await callback.message.edit_text("Выберите любой день в нужном месяце:", reply_markup=calendar)
    elif action == "year":
        await callback.message.edit_text("Выберите любой день в нужном году:", reply_markup=calendar)
    await callback.answer()

@router.callback_query(GeneralChoice.choosing)
async def process_general_calendar(callback: CallbackQuery, state: FSMContext):
    result = process_calendar_callback(callback.data)
    if result is None:
        await callback.answer()
        return

    action = result[0]
    if action == "navigate":
        year, month = result[1], result[2]
        calendar = await generate_calendar(year, month)
        await callback.message.edit_reply_markup(reply_markup=calendar)
        await callback.answer()
        return
    elif action == "select_year":
        year, month = result[1], result[2]
        year_selector = await generate_year_selector(year, month)
        await callback.message.edit_text("Выберите год:", reply_markup=year_selector)
        await callback.answer()
        return
    elif action == "year_selected":
        year, month = result[1], result[2]
        calendar = await generate_calendar(year, month)
        await callback.message.edit_text("Выберите дату:", reply_markup=calendar)
        await callback.answer()
        return
    elif action == "cancel":
        await state.clear()
        await callback.message.delete()
        await callback.message.answer("Главное меню", reply_markup=kb.main_menu)
        await callback.answer()
        return
    elif action == "date":
        selected_date = result[1]
        data = await state.get_data()
        period_type = data['period_type']

        if period_type == "day":
            start_date = end_date = selected_date.isoformat()
            period_name = selected_date.strftime("%d.%m.%Y")
        elif period_type == "month":
            start_date = selected_date.replace(day=1).isoformat()
            next_month = selected_date.replace(day=28) + timedelta(days=4)
            end_date = (next_month - timedelta(days=next_month.day)).isoformat()
            period_name = selected_date.strftime("%B %Y")
        elif period_type == "year":
            year = selected_date.year
            start_date = f"{year}-01-01"
            end_date = f"{year}-12-31"
            period_name = str(year)
        else:
            await callback.answer("Ошибка")
            return

        await show_period_operations(callback.message, state, start_date, end_date, period_name)
        await callback.answer()
    else:
        await callback.answer()

async def show_period_operations(message: types.Message, state: FSMContext, start, end, period_name):
    user_id = message.chat.id
    transactions = await db.get_transactions_by_period(user_id, start, end)
    if not transactions:
        text = f"📋 За период {period_name} нет операций."
    else:
        text = f"📋 Операции за {period_name}:\n\n"
        for t in transactions:
            sign = "+" if t[0]=='income' else "-"
            text += f"{sign} {t[1]} AZN – {t[2]}"
            if t[3]:
                text += f" ({t[3]})"
            text += f" – {utils.format_date_ru(t[4])}\n"
    await message.answer(text)
    await state.clear()

async def show_recent(message: types.Message):
    user_id = message.chat.id
    end = datetime.now().date().isoformat()
    start = (datetime.now() - timedelta(days=365)).date().isoformat()
    transactions = await db.get_transactions_by_period(user_id, start, end)
    recent = sorted(transactions, key=lambda x: x[4], reverse=True)[:10]
    if not recent:
        text = "🕒 Нет операций."
    else:
        text = "🕒 Последние 10 операций:\n\n"
        for t in recent:
            sign = "+" if t[0]=='income' else "-"
            text += f"{sign} {t[1]} AZN – {t[2]}"
            if t[3]:
                text += f" ({t[3]})"
            text += f" – {utils.format_date_ru(t[4])}\n"
    await message.answer(text)
