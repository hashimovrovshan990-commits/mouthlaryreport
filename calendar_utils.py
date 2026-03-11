from datetime import datetime, timedelta, date
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
import calendar

async def generate_calendar(year: int, month: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    month_names = ['Янв', 'Фев', 'Мар', 'Апр', 'Май', 'Июн',
                   'Июл', 'Авг', 'Сен', 'Окт', 'Ноя', 'Декабрь']
    
    builder.row(
        InlineKeyboardButton(text="📅", callback_data=f"select_year_{year}_{month}"),
        InlineKeyboardButton(text=f"{month_names[month-1]} {year}", callback_data="ignore"),
        InlineKeyboardButton(text="📅", callback_data=f"select_year_{year}_{month}"),
        width=3
    )
    
    builder.row(
        InlineKeyboardButton(text="◀️", callback_data=f"prev_month_{year}_{month}"),
        InlineKeyboardButton(text="⬅️ Месяц", callback_data=f"prev_month_{year}_{month}"),
        InlineKeyboardButton(text="Месяц ➡️", callback_data=f"next_month_{year}_{month}"),
        InlineKeyboardButton(text="▶️", callback_data=f"next_month_{year}_{month}"),
        width=4
    )
    
    week_days = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
    builder.row(*[InlineKeyboardButton(text=day, callback_data="ignore") for day in week_days], width=7)
    
    cal = calendar.monthcalendar(year, month)
    for week in cal:
        row_buttons = []
        for day in week:
            if day == 0:
                row_buttons.append(InlineKeyboardButton(text=" ", callback_data="ignore"))
            else:
                row_buttons.append(InlineKeyboardButton(
                    text=str(day),
                    callback_data=f"day_{year}_{month}_{day}"
                ))
        builder.row(*row_buttons, width=7)
    
    builder.row(InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_calendar"))
    return builder.as_markup()

async def generate_year_selector(current_year: int, current_month: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    start_year = current_year - 5
    end_year = current_year + 5
    years = []
    for y in range(start_year, end_year + 1):
        years.append(InlineKeyboardButton(text=str(y), callback_data=f"select_year_num_{y}_{current_month}"))
    
    builder.row(*years[:4], width=4)
    builder.row(*years[4:8], width=4)
    builder.row(*years[8:12], width=4)
    builder.row(InlineKeyboardButton(text="◀️ Назад к календарю", callback_data=f"back_to_calendar_{current_year}_{current_month}"))
    builder.row(InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_calendar"))
    return builder.as_markup()

def process_calendar_callback(callback_data: str):
    if callback_data.startswith("day_"):
        parts = callback_data.split("_")
        if len(parts) == 4:
            _, year, month, day = parts
            return ("date", date(int(year), int(month), int(day)))
    elif callback_data.startswith("prev_month_"):
        parts = callback_data.split("_")
        if len(parts) == 4:
            _, _, year, month = parts
            dt = date(int(year), int(month), 1) - timedelta(days=1)
            return ("navigate", dt.year, dt.month)
    elif callback_data.startswith("next_month_"):
        parts = callback_data.split("_")
        if len(parts) == 4:
            _, _, year, month = parts
            dt = date(int(year), int(month), 28) + timedelta(days=4)
            return ("navigate", dt.year, dt.month)
    elif callback_data.startswith("select_year_"):
        parts = callback_data.split("_")
        if len(parts) == 4:
            _, _, year, month = parts
            return ("select_year", int(year), int(month))
    elif callback_data.startswith("select_year_num_"):
        parts = callback_data.split("_")
        if len(parts) == 5:
            _, _, _, year, month = parts
            return ("year_selected", int(year), int(month))
    elif callback_data.startswith("back_to_calendar_"):
        parts = callback_data.split("_")
        if len(parts) == 5:
            _, _, _, year, month = parts
            return ("navigate", int(year), int(month))
    elif callback_data == "cancel_calendar":
        return ("cancel",)
    return None
