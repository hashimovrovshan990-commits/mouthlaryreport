import asyncpg
from datetime import datetime
import os

DATABASE_URL = os.getenv("DATABASE_URL")

class Database:
    def __init__(self):
        self.pool = None

    async def create_pool(self):
        """Создаёт пул соединений к базе данных"""
        self.pool = await asyncpg.create_pool(DATABASE_URL)
        await self.init_db()

    async def init_db(self):
        """Создаёт таблицы, если их нет"""
        async with self.pool.acquire() as conn:
            # Таблица пользователей
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    user_id BIGINT PRIMARY KEY,
                    username TEXT,
                    first_name TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Таблица транзакций
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS transactions (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT REFERENCES users(user_id) ON DELETE CASCADE,
                    type VARCHAR(10) CHECK (type IN ('income', 'expense')),
                    amount DECIMAL(10, 2),
                    category TEXT,
                    description TEXT,
                    date DATE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Индексы для быстрого поиска
            await conn.execute('CREATE INDEX IF NOT EXISTS idx_transactions_user_date ON transactions(user_id, date)')
            await conn.execute('CREATE INDEX IF NOT EXISTS idx_transactions_type ON transactions(type)')

    async def add_user(self, user_id, username, first_name):
        """Добавляет пользователя, если его нет"""
        async with self.pool.acquire() as conn:
            await conn.execute('''
                INSERT INTO users (user_id, username, first_name, created_at)
                VALUES ($1, $2, $3, $4)
                ON CONFLICT (user_id) DO NOTHING
            ''', user_id, username, first_name, datetime.now())

    async def add_transaction(self, user_id, t_type, amount, category, description, date):
        """Добавляет транзакцию"""
        async with self.pool.acquire() as conn:
            result = await conn.fetchrow('''
                INSERT INTO transactions (user_id, type, amount, category, description, date, created_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                RETURNING id
            ''', user_id, t_type, amount, category, description, date, datetime.now())
            return result['id']

    async def get_balance(self, user_id):
        """Возвращает баланс, сумму доходов и расходов"""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow('''
                SELECT 
                    COALESCE(SUM(CASE WHEN type='income' THEN amount ELSE 0 END), 0) as total_income,
                    COALESCE(SUM(CASE WHEN type='expense' THEN amount ELSE 0 END), 0) as total_expense
                FROM transactions 
                WHERE user_id=$1
            ''', user_id)
            income = row['total_income']
            expense = row['total_expense']
            balance = income - expense
            return balance, income, expense

    async def get_transactions_by_period(self, user_id, start_date, end_date):
        """Возвращает транзакции за период"""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch('''
                SELECT type, amount, category, description, date 
                FROM transactions 
                WHERE user_id=$1 AND date BETWEEN $2 AND $3
                ORDER BY date DESC
            ''', user_id, start_date, end_date)
            return [(r['type'], r['amount'], r['category'], r['description'], r['date'].isoformat()) for r in rows]

    async def get_transactions_by_day(self, user_id, date_iso):
        """Возвращает транзакции за конкретный день"""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch('''
                SELECT type, amount, category, description, date 
                FROM transactions 
                WHERE user_id=$1 AND date=$2
                ORDER BY date DESC
            ''', user_id, date_iso)
            print(f"get_transactions_by_day: user_id={user_id}, date={date_iso}, найдено={len(rows)}")
            return [(r['type'], r['amount'], r['category'], r['description'], r['date'].isoformat()) for r in rows]

    async def get_expenses_by_category(self, user_id, start_date, end_date):
        """Возвращает сумму расходов по категориям за период"""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch('''
                SELECT category, SUM(amount) as total 
                FROM transactions 
                WHERE user_id=$1 AND type='expense' AND date BETWEEN $2 AND $3
                GROUP BY category
                ORDER BY total DESC
            ''', user_id, start_date, end_date)
            return [(r['category'], r['total']) for r in rows]

    async def get_total_by_category(self, user_id, t_type, category, start_date=None, end_date=None):
        """Возвращает общую сумму по категории"""
        async with self.pool.acquire() as conn:
            if start_date and end_date:
                result = await conn.fetchval('''
                    SELECT COALESCE(SUM(amount), 0)
                    FROM transactions 
                    WHERE user_id=$1 AND type=$2 AND category=$3 
                      AND date BETWEEN $4 AND $5
                ''', user_id, t_type, category, start_date, end_date)
            else:
                result = await conn.fetchval('''
                    SELECT COALESCE(SUM(amount), 0)
                    FROM transactions 
                    WHERE user_id=$1 AND type=$2 AND category=$3
                ''', user_id, t_type, category)
            return result

    async def get_recent_transactions(self, user_id, t_type=None, limit=10):
        """Возвращает последние транзакции с ID"""
        async with self.pool.acquire() as conn:
            if t_type:
                rows = await conn.fetch('''
                    SELECT id, type, amount, category, description, date 
                    FROM transactions 
                    WHERE user_id=$1 AND type=$2
                    ORDER BY date DESC, id DESC 
                    LIMIT $3
                ''', user_id, t_type, limit)
            else:
                rows = await conn.fetch('''
                    SELECT id, type, amount, category, description, date 
                    FROM transactions 
                    WHERE user_id=$1
                    ORDER BY date DESC, id DESC 
                    LIMIT $2
                ''', user_id, limit)
            return [(r['id'], r['type'], r['amount'], r['category'], r['description'], r['date'].isoformat()) for r in rows]

    async def delete_transaction(self, transaction_id, user_id):
        """Удаляет транзакцию"""
        async with self.pool.acquire() as conn:
            result = await conn.execute('''
                DELETE FROM transactions 
                WHERE id=$1 AND user_id=$2
            ''', transaction_id, user_id)
            return result == "DELETE 1"

    async def update_transaction(self, transaction_id, user_id, field, new_value):
        """Обновляет поле транзакции"""
        allowed_fields = {'amount', 'category', 'description', 'date'}
        if field not in allowed_fields:
            return False
        async with self.pool.acquire() as conn:
            result = await conn.execute(
                f"UPDATE transactions SET {field}=$1 WHERE id=$2 AND user_id=$3",
                new_value, transaction_id, user_id
            )
            return result.startswith("UPDATE")

# Создаём глобальный экземпляр базы данных
db = Database()
