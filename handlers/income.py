from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
import keyboards as kb
from states import AddIncome, EditIncome, DeleteIncome
from database import add_transaction, get_recent_transactions, delete_transaction, update_transaction
from calendar_utils import generate_calendar, process_calendar_callback, generate_year_selector
from datetime import datetime
from database import db
import utils

router = Router()

# Меню доходов
@router.message(lambda msg: msg.text == "💵 Доход")
async def income_menu(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("Меню доходов", reply_markup=kb.income_submenu)

# Добавление зарплаты
@router.message(lambda msg: msg.text == "💼 Зарплата")
async def add_salary_start(message: types.Message, state: FSMContext):
    await state.update_data(income_type="зарплата", user_id=message.from_user.id)
    today = datetime.now()
    calendar = await generate_calendar(today.year, today.month)
    await state.set_state(AddIncome.date)
    await message.answer("Выберите дату получения зарплаты:", reply_markup=calendar)

# Добавление заработка
@router.message(lambda msg: msg.text == "💸 Заработок")
async def add_earning_start(message: types.Message, state: FSMContext):
    await state.update_data(income_type="заработок", user_id=message.from_user.id)
    today = datetime.now()
    calendar = await generate_calendar(today.year, today.month)
    await state.set_state(AddIncome.date)
    await message.answer("Выберите дату заработка:", reply_markup=calendar)

# Обработка календаря для доходов
@router.callback_query(AddIncome.date)
async def process_income_calendar(callback: CallbackQuery, state: FSMContext):
    result = process_calendar_callback(callback.data)
    if result is None:
        await callback.answer()
        return

    action = result[0]
    if action == "navigate":
        year, month = result[1], result[2]
        calendar = await generate_calendar(year, month)
        await callback.message.edit_text("Выберите дату:", reply_markup=calendar)
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
        await callback.message.edit_text("Добавление отменено.")
        await callback.message.answer("Главное меню", reply_markup=kb.main_menu)
        await callback.answer()
        return
    elif action == "date":
        selected_date = result[1]
        await state.update_data(date=selected_date.isoformat())
        await state.set_state(AddIncome.amount)
        await callback.message.delete()
        await callback.message.answer("Введите сумму в AZN:")
        await callback.answer()
    else:
        await callback.answer()

# Ввод суммы
@router.message(AddIncome.amount)
async def process_income_amount(message: types.Message, state: FSMContext):
    try:
        amount = float(message.text.replace(',', '.'))
        if amount <= 0:
            await message.answer("Сумма должна быть положительной.")
            return
        await state.update_data(amount=amount)
        data = await state.get_data()
        if data['income_type'] == "зарплата":
            await finish_income(message, state, "")
        else:
            await state.set_state(AddIncome.description)
            await message.answer("Введите комментарий к заработку (или пропустите):",
                                 reply_markup=kb.skip_keyboard)
    except ValueError:
        await message.answer("Пожалуйста, введите число.")

# Обработчик кнопки "Пропустить"
@router.callback_query(AddIncome.description, F.data == "skip_comment")
async def skip_income_comment(callback: CallbackQuery, state: FSMContext):
    print("skip_income_comment вызван")
    await finish_income(callback.message, state, "")
    await callback.answer()

# Ввод комментария
@router.message(AddIncome.description)
async def process_income_comment(message: types.Message, state: FSMContext):
    await finish_income(message, state, message.text.strip())

async def finish_income(message_or_chat, state: FSMContext, comment: str):
    data = await state.get_data()
    user_id = data.get('user_id')
    if not user_id:
        user_id = message_or_chat.from_user.id
        print(f"Warning: user_id not in state, using {user_id}")

    print(f"finish_income: user_id={user_id}, comment='{comment}'")

    if not data.get('date') or not data.get('amount') or not data.get('income_type'):
        print("Ошибка: не хватает данных в состоянии")
        await message_or_chat.answer("❌ Ошибка: данные не найдены. Попробуйте снова.")
        await state.clear()
        return

    add_transaction(
        user_id=user_id,
        t_type='income',
        amount=data['amount'],
        category=data['income_type'],
        description=comment,
        date=data['date']
    )
    print(f"Добавлен доход: user_id={user_id}, amount={data['amount']}, date={data['date']}")

    await state.clear()
    await message_or_chat.answer(
        f"✅ {data['income_type'].capitalize()} добавлен(а)!\n"
        f"Сумма: {data['amount']} AZN\n"
        f"Дата: {utils.format_date_ru(data['date'])}\n"
        f"Комментарий: {comment}",
        reply_markup=kb.income_submenu
    )

# Изменение дохода (без изменений)
@router.message(lambda msg: msg.text == "✏️ Изменить доход")
async def edit_income_start(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    transactions = get_recent_transactions(user_id, t_type='income', limit=10)
    if not transactions:
        await message.answer("У вас нет доходов для изменения.")
        return

    builder = InlineKeyboardBuilder()
    for t in transactions:
        t_id, _, amount, category, desc, date_iso = t
        btn_text = f"{utils.format_date_ru(date_iso)} – {amount} AZN – {category}"
        if desc:
            btn_text += f" ({desc})"
        builder.row(InlineKeyboardButton(text=btn_text, callback_data=f"edit_inc_{t_id}"))
    builder.row(InlineKeyboardButton(text="❌ Отмена", callback_data="edit_cancel"))
    await message.answer("Выберите доход для изменения:", reply_markup=builder.as_markup())
    await state.set_state(EditIncome.choosing_transaction)

@router.callback_query(EditIncome.choosing_transaction)
async def edit_income_choose(callback: CallbackQuery, state: FSMContext):
    if callback.data == "edit_cancel":
        await state.clear()
        await callback.message.delete()
        await callback.message.answer("Главное меню", reply_markup=kb.main_menu)
        await callback.answer()
        return

    if callback.data.startswith("edit_inc_"):
        t_id = int(callback.data.split("_")[2])
        await state.update_data(transaction_id=t_id)
        field_kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💰 Сумма", callback_data="edit_field_amount"),
             InlineKeyboardButton(text="📂 Категория", callback_data="edit_field_category")],
            [InlineKeyboardButton(text="📝 Описание", callback_data="edit_field_description"),
             InlineKeyboardButton(text="📅 Дата", callback_data="edit_field_date")],
            [InlineKeyboardButton(text="❌ Отмена", callback_data="edit_cancel")]
        ])
        await callback.message.edit_text("Что хотите изменить?", reply_markup=field_kb)
        await state.set_state(EditIncome.choosing_field)
        await callback.answer()

@router.callback_query(EditIncome.choosing_field, F.data.startswith("edit_field_"))
async def edit_income_field(callback: CallbackQuery, state: FSMContext):
    field = callback.data.replace("edit_field_", "")
    await state.update_data(field=field)
    await state.set_state(EditIncome.new_value)
    prompts = {
        "amount": "Введите новую сумму (число):",
        "category": "Введите новую категорию (текст):",
        "description": "Введите новый комментарий:",
        "date": "Введите новую дату в формате ДД.ММ.ГГГГ:"
    }
    await callback.message.edit_text(prompts.get(field, "Введите новое значение:"))
    await callback.answer()

@router.message(EditIncome.new_value)
async def edit_income_value(message: types.Message, state: FSMContext):
    data = await state.get_data()
    t_id = data['transaction_id']
    field = data['field']
    new_val = message.text.strip()
    user_id = message.from_user.id

    success = update_transaction(t_id, user_id, field, new_val)
    if success:
        await message.answer("✅ Доход успешно обновлён!")
    else:
        await message.answer("❌ Ошибка при обновлении. Попробуйте позже.")
    await state.clear()
    await message.answer("Главное меню", reply_markup=kb.main_menu)

# Удаление дохода
@router.message(lambda msg: msg.text == "❌ Удалить доход")
async def delete_income_start(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    transactions = get_recent_transactions(user_id, t_type='income', limit=10)
    if not transactions:
        await message.answer("У вас нет доходов для удаления.")
        return

    builder = InlineKeyboardBuilder()
    for t in transactions:
        t_id, _, amount, category, desc, date_iso = t
        btn_text = f"{utils.format_date_ru(date_iso)} – {amount} AZN – {category}"
        if desc:
            btn_text += f" ({desc})"
        builder.row(InlineKeyboardButton(text=btn_text, callback_data=f"del_inc_{t_id}"))
    builder.row(InlineKeyboardButton(text="❌ Отмена", callback_data="delete_cancel"))
    await message.answer("Выберите доход для удаления:", reply_markup=builder.as_markup())
    await state.set_state(DeleteIncome.confirming)

@router.callback_query(DeleteIncome.confirming)
async def delete_income_confirm(callback: CallbackQuery, state: FSMContext):
    if callback.data == "delete_cancel":
        await state.clear()
        await callback.message.delete()
        await callback.message.answer("Главное меню", reply_markup=kb.main_menu)
        await callback.answer()
        return

    if callback.data.startswith("del_inc_"):
        t_id = int(callback.data.split("_")[2])
        confirm_kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Да, удалить", callback_data=f"confirm_del_inc_{t_id}"),
             InlineKeyboardButton(text="❌ Нет", callback_data="delete_cancel")]
        ])
        await callback.message.edit_text("Вы уверены, что хотите удалить этот доход?", reply_markup=confirm_kb)
        await callback.answer()

@router.callback_query(F.data.startswith("confirm_del_inc_"))
async def delete_income_execute(callback: CallbackQuery, state: FSMContext):
    t_id = int(callback.data.split("_")[3])
    user_id = callback.from_user.id
    success = delete_transaction(t_id, user_id)
    if success:
        await callback.message.edit_text("✅ Доход удалён.")
    else:
        await callback.message.edit_text("❌ Ошибка при удалении.")
    await state.clear()
    await callback.message.answer("Главное меню", reply_markup=kb.main_menu)

    await callback.answer()
