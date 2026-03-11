from aiogram.fsm.state import State, StatesGroup

class AddExpense(StatesGroup):
    date = State()
    category = State()
    amount = State()
    description = State()

class AddIncome(StatesGroup):
    date = State()
    amount = State()
    description = State()

class AnalyticsPeriod(StatesGroup):
    period_type = State()
    choosing = State()

class GeneralChoice(StatesGroup):
    period_type = State()
    choosing = State()

class EditExpense(StatesGroup):
    choosing_transaction = State()
    choosing_field = State()
    new_value = State()

class DeleteExpense(StatesGroup):
    confirming = State()
    transaction_id = State()

class EditIncome(StatesGroup):
    choosing_transaction = State()
    choosing_field = State()
    new_value = State()

class DeleteIncome(StatesGroup):
    confirming = State()
    transaction_id = State()
