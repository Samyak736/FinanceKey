from typing import Any

from models.db import get_cursor


def insert_transactions(rows: list[dict[str, Any]], user_id: int) -> int:
    with get_cursor() as cur:
        cur.executemany(
            """
            INSERT INTO transactions (date, description, amount, category, user_id)
            VALUES (:date, :description, :amount, :category, :user_id)
            """,
            [
                {
                    "date": r["date"],
                    "description": r["description"],
                    "amount": float(r["amount"]),
                    "category": r["category"],
                    "user_id": user_id,
                }
                for r in rows
            ],
        )
        return len(rows)


def clear_user_transactions(user_id: int) -> None:
    with get_cursor() as cur:
        cur.execute("DELETE FROM transactions WHERE user_id = ?", (user_id,))


def fetch_all_for_user(user_id: int) -> list[dict]:
    with get_cursor() as cur:
        cur.execute(
            """
            SELECT id, date, description, amount, category, user_id
            FROM transactions
            WHERE user_id = ?
            ORDER BY date ASC
            """,
            (user_id,),
        )
        return [dict(row) for row in cur.fetchall()]
