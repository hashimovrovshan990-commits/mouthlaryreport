import asyncpg
import logging
from datetime import datetime
import os

DATABASE_URL = os.getenv("DATABASE_URL")
logger = logging.getLogger(__name__)

class Database:
    def __init__(self):
        self.pool = None

    async def create_pool(self):
        self.pool = await asyncpg.create_pool(DATABASE_URL)
        await self.init_db()

    async def init_db(self):
        async with self.pool.acquire() as conn:
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    user_id BIGINT PRIMARY KEY,
                    username TEXT,
                    first_name TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
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
            await conn.execute('CREATE INDEX IF NOT EXISTS idx_transactions_user_date ON transactions(user_id, date)')
            await conn.execute('CREATE INDEX IF NOT EXISTS idx_transactions_type ON transactions(type)')

    async def add_user(self, user_id, username, first_name):
        async with self.pool.acquire() as conn:
            await conn.execute('''
                INSERT INTO users (user_id, username, first_name, created_at)
                VALUES ($1, $2, $3, $4)
                ON CONFLICT (user_id) DO NOTHING
            ''', user_id, username, first_name, datetime.now())

    async def add_transaction(self, user_id, t_type, amount, category, description, date):
        if isinstance(date, str):
            try:
                date_obj = datetime.fromisoformat(date).date()
            except ValueError:
                date_obj = datetime.strptime(date, "%Y-%m-%d").date()
        else:
            date_obj = date

        async with self.pool.acquire() as conn:
            result = await conn.fetchrow('''
                INSERT INTO transactions (user_id, type, amount, category, description, date, created_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                RETURNING id
            ''', user_id, t_type, amount, category, description, date_obj, datetime.now())
            return result['id']

    async def get_balance(self, user_id):
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
        start = datetime.fromisoformat(start_date).date() if isinstance(start_date, str) else start_date
        end = datetime.fromisoformat(end_date).date() if isinstance(end_date, str) else end_date

        async with self.pool.acquire() as conn:
            rows = await conn.fetch('''
                SELECT type, amount, category, description, date 
                FROM transactions 
                WHERE user_id=$1 AND date BETWEEN $2 AND $3
                ORDER BY date DESC
            ''', user_id, start, end)
            return [(r['type'], r['amount'], r['category'], r['description'], r['date'].isoformat()) for r in rows]

    async def get_transactions_by_day(self, user_id, date_iso):
        date_obj = datetime.fromisoformat(date_iso).date() if isinstance(date_iso, str) else date_iso

        async with self.pool.acquire() as conn:
            rows = await conn.fetch('''
                SELECT type, amount, category, description, date 
                FROM transactions 
                WHERE user_id=$1 AND date=$2
                ORDER BY date DESC
            ''', user_id, date_obj)
            return [(r['type'], r['amount'], r['category'], r['description'], r['date'].isoformat()) for r in rows]

    async def get_expenses_by_category(self, user_id, start_date, end_date):
        start = datetime.fromisoformat(start_date).date() if isinstance(start_date, str) else start_date
        end = datetime.fromisoformat(end_date).date() if isinstance(end_date, str) else end_date

        async with self.pool.acquire() as conn:
            rows = await conn.fetch('''
                SELECT category, SUM(amount) as total 
                FROM transactions 
                WHERE user_id=$1 AND type='expense' AND date BETWEEN $2 AND $3
                GROUP BY category
                ORDER BY total DESC
            ''', user_id, start, end)
            return [(r['category'], r['total']) for r in rows]

    async def get_total_by_category(self, user_id, t_type, category, start_date=None, end_date=None):
        async with self.pool.acquire() as conn:
            if start_date and end_date:
                start = datetime.fromisoformat(start_date).date() if isinstance(start_date, str) else start_date
                end = datetime.fromisoformat(end_date).date() if isinstance(end_date, str) else end_date
                result = await conn.fetchval('''
                    SELECT COALESCE(SUM(amount), 0)
                    FROM transactions 
                    WHERE user_id=$1 AND type=$2 AND category=$3 
                      AND date BETWEEN $4 AND $5
                ''', user_id, t_type, category, start, end)
            else:
                result = await conn.fetchval('''
                    SELECT COALESCE(SUM(amount), 0)
                    FROM transactions 
                    WHERE user_id=$1 AND type=$2 AND category=$3
                ''', user_id, t_type, category)
            return result

    async def get_recent_transactions(self, user_id, t_type=None, limit=10):
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
        try:
            async with self.pool.acquire() as conn:
                result = await conn.execute('''
                    DELETE FROM transactions 
                    WHERE id=$1 AND user_id=$2
                ''', transaction_id, user_id)
                logger.info(f"delete_transaction raw result: {result}")
                success = result == "DELETE 1"
                logger.info(f"delete_transaction success: {success}")
                return success
        except Exception as e:
            logger.error(f"Ошибка в delete_transaction: {e}", exc_info=True)
            return False

    async def update_transaction(self, transaction_id, user_id, field, new_value):
        allowed_fields = {'amount', 'category', 'description', 'date'}
        if field not in allowed_fields:
            return False
        async with self.pool.acquire() as conn:
            if field == 'date':
                try:
                    date_obj = datetime.strptime(new_value, "%d.%m.%Y").date()
                except ValueError:
                    try:
                        date_obj = datetime.fromisoformat(new_value).date()
                    except ValueError:
                        return False
                new_value = date_obj
            await conn.execute(
                f"UPDATE transactions SET {field}=$1 WHERE id=$2 AND user_id=$3",
                new_value, transaction_id, user_id
            )
            return True

db = Database()
