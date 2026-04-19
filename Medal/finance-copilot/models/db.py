import sqlite3
from contextlib import contextmanager

from config import DATABASE_PATH


def get_connection():
    return sqlite3.connect(DATABASE_PATH, check_same_thread=False)


@contextmanager
def get_cursor():
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    try:
        cur = conn.cursor()
        yield cur
        conn.commit()
    finally:
        conn.close()


def init_db():
    from pathlib import Path

    Path(DATABASE_PATH).parent.mkdir(parents=True, exist_ok=True)
    with get_cursor() as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                description TEXT NOT NULL,
                amount REAL NOT NULL,
                category TEXT NOT NULL,
                user_id INTEGER NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
            """
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_tx_user_date ON transactions(user_id, date)"
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_tx_user_cat ON transactions(user_id, category)"
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS uploads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                filename TEXT NOT NULL,
                uploaded_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                record_count INTEGER NOT NULL,
                total_credits REAL NOT NULL,
                total_debits REAL NOT NULL,
                period_start TEXT,
                period_end TEXT,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
            """
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_upload_user_date ON uploads(user_id, uploaded_at)"
        )
