from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

main_menu = ReplyKeyboardMarkup(keyboard=[
    [KeyboardButton(text="💰 Баланс")],
    [KeyboardButton(text="➕ Расход"), KeyboardButton(text="💵 Доход")],
    [KeyboardButton(text="📊 Аналитика"), KeyboardButton(text="📅 Общий")]
], resize_keyboard=True)

expense_submenu = ReplyKeyboardMarkup(keyboard=[
    [KeyboardButton(text="➕ Добавить расход")],
    [KeyboardButton(text="✏️ Изменить расход"), KeyboardButton(text="❌ Удалить расход")],
    [KeyboardButton(text="◀️ Назад")]
], resize_keyboard=True)

income_submenu = ReplyKeyboardMarkup(keyboard=[
    [KeyboardButton(text="💼 Зарплата")],
    [KeyboardButton(text="💸 Заработок")],
    [KeyboardButton(text="✏️ Изменить доход"), KeyboardButton(text="❌ Удалить доход")],
    [KeyboardButton(text="◀️ Назад")]
], resize_keyboard=True)

expense_categories = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="🚗 Машина", callback_data="exp_cat_машина"),
     InlineKeyboardButton(text="🏠 Дом", callback_data="exp_cat_дом")],
    [InlineKeyboardButton(text="☕ Кафе", callback_data="exp_cat_кафе"),
     InlineKeyboardButton(text="🚬 Сигареты", callback_data="exp_cat_сигареты")],
    [InlineKeyboardButton(text="💳 Кредит", callback_data="exp_cat_кредит"),
     InlineKeyboardButton(text="Другое", callback_data="exp_cat_другое")],
    [InlineKeyboardButton(text="❌ Отмена", callback_data="exp_cat_cancel")]
])

income_categories = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="💼 Зарплата", callback_data="inc_cat_зарплата")],
    [InlineKeyboardButton(text="💸 Заработок", callback_data="inc_cat_заработок")],
    [InlineKeyboardButton(text="❌ Отмена", callback_data="inc_cat_cancel")]
])

skip_keyboard = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="⏩ Пропустить", callback_data="skip_comment")]
])