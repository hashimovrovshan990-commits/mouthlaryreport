import sqlite3
from utils import parse_date_ru
from datetime import datetime

DB_NAME = 'finance.db'

def init_db():
    with sqlite3.connect(DB_NAME) as conn:
        cur = conn.cursor()
        cur.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                created_at TEXT
            )
        ''')
        cur.execute('''
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                type TEXT CHECK(type IN ('income', 'expense')),
                amount REAL,
                category TEXT,
                description TEXT,
                date TEXT,
                created_at TEXT
            )
        ''')
        conn.commit()

def add_user(user_id, username, first_name):
    with sqlite3.connect(DB_NAME) as conn:
        cur = conn.cursor()
        cur.execute(
            "INSERT OR IGNORE INTO users (user_id, username, first_name, created_at) VALUES (?, ?, ?, ?)",
            (user_id, username, first_name, datetime.now().isoformat())
        )
        conn.commit()

def add_transaction(user_id, t_type, amount, category, description, date):
    with sqlite3.connect(DB_NAME) as conn:
        cur = conn.cursor()
        cur.execute('''
            INSERT INTO transactions (user_id, type, amount, category, description, date, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (user_id, t_type, amount, category, description, date, datetime.now().isoformat()))
        conn.commit()
        return cur.lastrowid

def get_balance(user_id):
    with sqlite3.connect(DB_NAME) as conn:
        cur = conn.cursor()
        cur.execute('''
            SELECT 
                SUM(CASE WHEN type='income' THEN amount ELSE 0 END) as total_income,
                SUM(CASE WHEN type='expense' THEN amount ELSE 0 END) as total_expense
            FROM transactions WHERE user_id=?
        ''', (user_id,))
        row = cur.fetchone()
        income = row[0] or 0
        expense = row[1] or 0
        balance = income - expense
        return balance, income, expense

def get_transactions_by_period(user_id, start_date, end_date):
    with sqlite3.connect(DB_NAME) as conn:
        cur = conn.cursor()
        cur.execute('''
            SELECT type, amount, category, description, date 
            FROM transactions 
            WHERE user_id=? AND date BETWEEN ? AND ?
            ORDER BY date DESC
        ''', (user_id, start_date, end_date))
        return cur.fetchall()

def get_expenses_by_category(user_id, start_date, end_date):
    with sqlite3.connect(DB_NAME) as conn:
        cur = conn.cursor()
        cur.execute('''
            SELECT category, SUM(amount) as total 
            FROM transactions 
            WHERE user_id=? AND type='expense' AND date BETWEEN ? AND ?
            GROUP BY category
            ORDER BY total DESC
        ''', (user_id, start_date, end_date))
        return cur.fetchall()

def get_incomes_by_category(user_id, start_date, end_date):
    with sqlite3.connect(DB_NAME) as conn:
        cur = conn.cursor()
        cur.execute('''
            SELECT category, SUM(amount) as total 
            FROM transactions 
            WHERE user_id=? AND type='income' AND date BETWEEN ? AND ?
            GROUP BY category
            ORDER BY total DESC
        ''', (user_id, start_date, end_date))
        return cur.fetchall()

def get_total_by_category(user_id, t_type, category, start_date=None, end_date=None):
    with sqlite3.connect(DB_NAME) as conn:
        cur = conn.cursor()
        query = "SELECT SUM(amount) FROM transactions WHERE user_id=? AND type=? AND category=?"
        params = [user_id, t_type, category]
        if start_date and end_date:
            query += " AND date BETWEEN ? AND ?"
            params.extend([start_date, end_date])
        cur.execute(query, params)
        return cur.fetchone()[0] or 0

def get_recent_transactions(user_id, t_type=None, limit=10):
    with sqlite3.connect(DB_NAME) as conn:
        cur = conn.cursor()
        query = "SELECT id, type, amount, category, description, date FROM transactions WHERE user_id=?"
        params = [user_id]
        if t_type:
            query += " AND type=?"
            params.append(t_type)
        query += " ORDER BY date DESC, id DESC LIMIT ?"
        params.append(limit)
        cur.execute(query, params)
        return cur.fetchall()

def delete_transaction(transaction_id, user_id):
    with sqlite3.connect(DB_NAME) as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM transactions WHERE id=? AND user_id=?", (transaction_id, user_id))
        conn.commit()
        return cur.rowcount > 0

def update_transaction(transaction_id, user_id, field, new_value):
    allowed_fields = {'amount': 'REAL', 'category': 'TEXT', 'description': 'TEXT', 'date': 'TEXT'}
    if field not in allowed_fields:
        return False
    with sqlite3.connect(DB_NAME) as conn:
        cur = conn.cursor()
        if field == 'date':
            try:
                new_value = parse_date_ru(new_value)
            except:
                pass
        cur.execute(f"UPDATE transactions SET {field}=? WHERE id=? AND user_id=?", (new_value, transaction_id, user_id))
        conn.commit()
        return cur.rowcount > 0

def get_transactions_by_day(user_id, date_iso):
    with sqlite3.connect(DB_NAME) as conn:
        cur = conn.cursor()
        cur.execute('''
            SELECT type, amount, category, description, date 
            FROM transactions 
            WHERE user_id=? AND date=?
            ORDER BY date DESC
        ''', (user_id, date_iso))
        rows = cur.fetchall()
        print(f"get_transactions_by_day: user_id={user_id}, date={date_iso}, найдено={len(rows)}")
        for row in rows:
            print(row)
        return rows