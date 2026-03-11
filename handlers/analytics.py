from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from states import AnalyticsPeriod
from database import db
from calendar_utils import generate_calendar, process_calendar_callback, generate_year_selector
from datetime import datetime, timedelta
import utils
import keyboards as kb

router = Router()

@router.message(lambda msg: msg.text == "📊 Аналитика")
async def analytics_start(message: types.Message, state: FSMContext):
    period_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📅 День", callback_data="analytics_day"),
         InlineKeyboardButton(text="📅 Месяц", callback_data="analytics_month")],
        [InlineKeyboardButton(text="📅 Год", callback_data="analytics_year"),
         InlineKeyboardButton(text="❌ Отмена", callback_data="analytics_cancel")]
    ])
    await message.answer("Выберите период для аналитики:", reply_markup=period_kb)

@router.callback_query(F.data.startswith("analytics_"))
async def choose_analytics_period(callback: CallbackQuery, state: FSMContext):
    action = callback.data.replace("analytics_", "")
    if action == "cancel":
        await state.clear()
        await callback.message.delete()
        await callback.message.answer("Главное меню", reply_markup=kb.main_menu)
        await callback.answer()
        return

    await state.update_data(period_type=action)
    await state.set_state(AnalyticsPeriod.choosing)

    today = datetime.now()
    calendar = await generate_calendar(today.year, today.month)
    if action == "day":
        await callback.message.edit_text("Выберите день:", reply_markup=calendar)
    elif action == "month":
        await callback.message.edit_text("Выберите любой день в нужном месяце:", reply_markup=calendar)
    elif action == "year":
        await callback.message.edit_text("Выберите любой день в нужном году:", reply_markup=calendar)
    await callback.answer()

@router.callback_query(AnalyticsPeriod.choosing)
async def process_analytics_calendar(callback: CallbackQuery, state: FSMContext):
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
        user_id = callback.from_user.id

        if period_type == "day":
            transactions = await db.get_transactions_by_day(user_id, selected_date.isoformat())
            period_name = selected_date.strftime("%d.%m.%Y")
            start_date = end_date = selected_date.isoformat()
        elif period_type == "month":
            start_date = selected_date.replace(day=1).isoformat()
            next_month = selected_date.replace(day=28) + timedelta(days=4)
            end_date = (next_month - timedelta(days=next_month.day)).isoformat()
            transactions = await db.get_transactions_by_period(user_id, start_date, end_date)
            period_name = selected_date.strftime("%B %Y")
        elif period_type == "year":
            year = selected_date.year
            start_date = f"{year}-01-01"
            end_date = f"{year}-12-31"
            transactions = await db.get_transactions_by_period(user_id, start_date, end_date)
            period_name = str(year)
        else:
            await callback.answer("Ошибка")
            return

        await show_analytics(callback.message, state, transactions, period_name, period_type, start_date, end_date)
        await callback.answer()
    else:
        await callback.answer()

async def show_analytics(message: types.Message, state: FSMContext, transactions, period_name, period_type, start_date, end_date):
    if not transactions:
        text = f"📊 За период {period_name} нет операций."
    else:
        expenses = [t for t in transactions if t[0] == 'expense']
        incomes = [t for t in transactions if t[0] == 'income']
        text = f"📊 Аналитика за {period_name}\n\n"
        if incomes:
            total_income = sum(t[1] for t in incomes)
            text += f"💰 Доходы: {total_income} AZN\n"
            for t in incomes:
                text += f"  + {t[1]} – {t[2]}"
                if t[3]:
                    text += f" ({t[3]})"
                text += f" – {utils.format_date_ru(t[4])}\n"
        else:
            text += "💰 Доходов нет.\n"
        if expenses:
            total_expense = sum(t[1] for t in expenses)
            text += f"\n💸 Расходы: {total_expense} AZN\n"
            for t in expenses:
                text += f"  - {t[1]} – {t[2]}"
                if t[3]:
                    text += f" ({t[3]})"
                text += f" – {utils.format_date_ru(t[4])}\n"
            if period_type != "day":
                cat_expenses = await db.get_expenses_by_category(message.chat.id, start_date, end_date)
                if cat_expenses:
                    text += "\nКрупные траты по категориям:\n"
                    for cat, total in cat_expenses:
                        if period_type == "month" and total > 50:
                            text += f"  {cat}: {total} AZN\n"
                        elif period_type == "year" and total > 100:
                            text += f"  {cat}: {total} AZN\n"
        else:
            text += "\n💸 Расходов нет."
    await message.answer(text)
    await state.clear()
