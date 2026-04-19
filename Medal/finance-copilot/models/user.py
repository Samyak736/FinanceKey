from sqlite3 import IntegrityError

from models.db import get_cursor


def create_user(username: str, password_hash: str) -> int:
    with get_cursor() as cur:
        try:
            cur.execute(
                "INSERT INTO users (username, password_hash) VALUES (?, ?)",
                (username, password_hash),
            )
        except IntegrityError as exc:
            raise ValueError("Username already exists") from exc
        return cur.lastrowid


def get_user_by_username(username: str) -> dict | None:
    with get_cursor() as cur:
        cur.execute(
            "SELECT id, username, password_hash, created_at FROM users WHERE username = ?",
            (username,),
        )
        row = cur.fetchone()
        return dict(row) if row else None


def get_user_by_id(user_id: int) -> dict | None:
    with get_cursor() as cur:
        cur.execute(
            "SELECT id, username, password_hash, created_at FROM users WHERE id = ?",
            (user_id,),
        )
        row = cur.fetchone()
        return dict(row) if row else None
