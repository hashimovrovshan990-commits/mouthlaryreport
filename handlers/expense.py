from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
import keyboards as kb
from states import AddExpense, EditExpense, DeleteExpense
from database import add_transaction, get_recent_transactions, delete_transaction, update_transaction
from calendar_utils import generate_calendar, process_calendar_callback, generate_year_selector
from datetime import datetime
import utils

router = Router()

# Меню расходов
@router.message(lambda msg: msg.text == "➕ Расход")
async def expense_menu(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("Меню расходов", reply_markup=kb.expense_submenu)

# Добавление расхода
@router.message(lambda msg: msg.text == "➕ Добавить расход")
async def add_expense_start(message: types.Message, state: FSMContext):
    # Сохраняем user_id в состоянии
    await state.update_data(user_id=message.from_user.id)
    today = datetime.now()
    calendar = await generate_calendar(today.year, today.month)
    await state.set_state(AddExpense.date)
    await message.answer("Выберите дату расхода:", reply_markup=calendar)

@router.callback_query(AddExpense.date)
async def process_expense_calendar(callback: CallbackQuery, state: FSMContext):
    result = process_calendar_callback(callback.data)
    if result is None:
        await callback.answer()
        return

    action = result[0]
    if action == "navigate":
        year, month = result[1], result[2]
        calendar = await generate_calendar(year, month)
        await callback.message.edit_text("Выберите дату расхода:", reply_markup=calendar)
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
        await callback.message.edit_text("Выберите дату расхода:", reply_markup=calendar)
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
        await state.set_state(AddExpense.category)
        await callback.message.delete()
        await callback.message.answer("Выберите категорию расхода:", reply_markup=kb.expense_categories)
        await callback.answer()
    else:
        await callback.answer()

@router.callback_query(AddExpense.category)
async def process_expense_category(callback: CallbackQuery, state: FSMContext):
    if callback.data == "exp_cat_cancel":
        await state.clear()
        await callback.message.edit_text("Добавление отменено.")
        await callback.message.answer("Главное меню", reply_markup=kb.main_menu)
        return
    category = callback.data.replace("exp_cat_", "")
    await state.update_data(category=category)
    await state.set_state(AddExpense.amount)
    await callback.message.edit_text(f"Категория: {category}\nВведите сумму в AZN:")

@router.message(AddExpense.amount)
async def process_expense_amount(message: types.Message, state: FSMContext):
    try:
        amount = float(message.text.replace(',', '.'))
        if amount <= 0:
            await message.answer("Сумма должна быть положительной.")
            return
        await state.update_data(amount=amount)
        await state.set_state(AddExpense.description)
        await message.answer("Введите комментарий (или нажмите кнопку 'Пропустить'):",
                             reply_markup=kb.skip_keyboard)
    except ValueError:
        await message.answer("Пожалуйста, введите число.")

# Обработчик кнопки "Пропустить" – теперь user_id берётся из состояния
@router.callback_query(AddExpense.description, F.data == "skip_comment")
async def skip_expense_comment(callback: CallbackQuery, state: FSMContext):
    print("skip_expense_comment вызван")
    await finish_expense(callback.message, state, "")
    await callback.answer()

@router.message(AddExpense.description)
async def process_expense_comment(message: types.Message, state: FSMContext):
    await finish_expense(message, state, message.text.strip())

async def finish_expense(message_or_chat, state: FSMContext, comment: str):
    data = await state.get_data()
    user_id = data.get('user_id')
    if not user_id:
        # fallback – если вдруг user_id нет в состоянии (маловероятно)
        user_id = message_or_chat.from_user.id
        print(f"Warning: user_id not in state, using {user_id}")

    print(f"finish_expense: user_id={user_id}, comment='{comment}'")

    if not data.get('date') or not data.get('category') or not data.get('amount'):
        print("Ошибка: не хватает данных в состоянии")
        await message_or_chat.answer("❌ Ошибка: данные не найдены. Попробуйте снова.")
        await state.clear()
        return

    add_transaction(
        user_id=user_id,
        t_type='expense',
        amount=data['amount'],
        category=data['category'],
        description=comment,
        date=data['date']
    )
    print(f"Добавлен расход: user_id={user_id}, amount={data['amount']}, date={data['date']}")

    # Проверка сразу после добавления
    from database import get_transactions_by_day
    check = get_transactions_by_day(user_id, data['date'])
    print(f"Проверка сразу после добавления: найдено {len(check)} записей за {data['date']}")
    if check:
        print("Запись:", check[0])

    await state.clear()
    await message_or_chat.answer(
        f"✅ Расход добавлен!\n"
        f"Сумма: {data['amount']} AZN\n"
        f"Категория: {data['category']}\n"
        f"Дата: {utils.format_date_ru(data['date'])}\n"
        f"Комментарий: {comment}",
        reply_markup=kb.expense_submenu
    )

# Изменение расхода (без изменений, оставляем как есть)
@router.message(lambda msg: msg.text == "✏️ Изменить расход")
async def edit_expense_start(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    transactions = get_recent_transactions(user_id, t_type='expense', limit=10)
    if not transactions:
        await message.answer("У вас нет расходов для изменения.")
        return

    builder = InlineKeyboardBuilder()
    for t in transactions:
        t_id, _, amount, category, desc, date_iso = t
        btn_text = f"{utils.format_date_ru(date_iso)} – {amount} AZN – {category}"
        if desc:
            btn_text += f" ({desc})"
        builder.row(InlineKeyboardButton(text=btn_text, callback_data=f"edit_exp_{t_id}"))
    builder.row(InlineKeyboardButton(text="❌ Отмена", callback_data="edit_cancel"))
    await message.answer("Выберите расход для изменения:", reply_markup=builder.as_markup())
    await state.set_state(EditExpense.choosing_transaction)

@router.callback_query(EditExpense.choosing_transaction)
async def edit_choose_transaction(callback: CallbackQuery, state: FSMContext):
    if callback.data == "edit_cancel":
        await state.clear()
        await callback.message.delete()
        await callback.message.answer("Главное меню", reply_markup=kb.main_menu)
        await callback.answer()
        return

    if callback.data.startswith("edit_exp_"):
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
        await state.set_state(EditExpense.choosing_field)
        await callback.answer()

@router.callback_query(EditExpense.choosing_field, F.data.startswith("edit_field_"))
async def edit_choose_field(callback: CallbackQuery, state: FSMContext):
    field = callback.data.replace("edit_field_", "")
    await state.update_data(field=field)
    await state.set_state(EditExpense.new_value)
    prompts = {
        "amount": "Введите новую сумму (число):",
        "category": "Введите новую категорию (текст):",
        "description": "Введите новый комментарий:",
        "date": "Введите новую дату в формате ДД.ММ.ГГГГ:"
    }
    await callback.message.edit_text(prompts.get(field, "Введите новое значение:"))
    await callback.answer()

# Обработчик для отмены на этапе выбора поля
@router.callback_query(EditExpense.choosing_field, F.data == "edit_cancel")
async def edit_cancel_from_field(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.delete()
    await callback.message.answer("Главное меню", reply_markup=kb.main_menu)
    await callback.answer()

@router.message(EditExpense.new_value)
async def edit_new_value(message: types.Message, state: FSMContext):
    data = await state.get_data()
    t_id = data['transaction_id']
    field = data['field']
    new_val = message.text.strip()
    user_id = message.from_user.id

    success = update_transaction(t_id, user_id, field, new_val)
    if success:
        await message.answer("✅ Расход успешно обновлён!")
    else:
        await message.answer("❌ Ошибка при обновлении. Попробуйте позже.")
    await state.clear()
    await message.answer("Главное меню", reply_markup=kb.main_menu)

# Удаление расхода (без изменений)
@router.message(lambda msg: msg.text == "❌ Удалить расход")
async def delete_expense_start(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    transactions = get_recent_transactions(user_id, t_type='expense', limit=10)
    if not transactions:
        await message.answer("У вас нет расходов для удаления.")
        return

    builder = InlineKeyboardBuilder()
    for t in transactions:
        t_id, _, amount, category, desc, date_iso = t
        btn_text = f"{utils.format_date_ru(date_iso)} – {amount} AZN – {category}"
        if desc:
            btn_text += f" ({desc})"
        builder.row(InlineKeyboardButton(text=btn_text, callback_data=f"del_exp_{t_id}"))
    builder.row(InlineKeyboardButton(text="❌ Отмена", callback_data="delete_cancel"))
    await message.answer("Выберите расход для удаления:", reply_markup=builder.as_markup())
    await state.set_state(DeleteExpense.confirming)

@router.callback_query(DeleteExpense.confirming)
async def delete_confirm(callback: CallbackQuery, state: FSMContext):
    if callback.data == "delete_cancel":
        await state.clear()
        await callback.message.delete()
        await callback.message.answer("Главное меню", reply_markup=kb.main_menu)
        await callback.answer()
        return

    if callback.data.startswith("del_exp_"):
        t_id = int(callback.data.split("_")[2])
        confirm_kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Да, удалить", callback_data=f"confirm_del_{t_id}"),
             InlineKeyboardButton(text="❌ Нет", callback_data="delete_cancel")]
        ])
        await callback.message.edit_text("Вы уверены, что хотите удалить этот расход?", reply_markup=confirm_kb)
        await callback.answer()

@router.callback_query(F.data.startswith("confirm_del_"))
async def delete_execute(callback: CallbackQuery, state: FSMContext):
    t_id = int(callback.data.split("_")[2])
    user_id = callback.from_user.id
    success = delete_transaction(t_id, user_id)
    if success:
        await callback.message.edit_text("✅ Расход удалён.")
    else:
        await callback.message.edit_text("❌ Ошибка при удалении.")
    await state.clear()
    await callback.message.answer("Главное меню", reply_markup=kb.main_menu)

    await callback.answer()

