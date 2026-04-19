from models.db import get_cursor


def insert_upload(
    user_id: int,
    filename: str,
    record_count: int,
    total_credits: float,
    total_debits: float,
    period_start: str | None,
    period_end: str | None,
) -> int:
    with get_cursor() as cur:
        cur.execute(
            """
            INSERT INTO uploads (
                user_id,
                filename,
                record_count,
                total_credits,
                total_debits,
                period_start,
                period_end
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                filename,
                record_count,
                total_credits,
                total_debits,
                period_start,
                period_end,
            ),
        )
        return cur.lastrowid


def list_uploads_for_user(user_id: int) -> list[dict]:
    with get_cursor() as cur:
        cur.execute(
            """
            SELECT id, filename, uploaded_at, record_count, total_credits, total_debits, period_start, period_end
            FROM uploads
            WHERE user_id = ?
            ORDER BY uploaded_at DESC
            """,
            (user_id,),
        )
        return [dict(row) for row in cur.fetchall()]


def get_upload_by_id(upload_id: int, user_id: int) -> dict | None:
    with get_cursor() as cur:
        cur.execute(
            """
            SELECT id, filename, uploaded_at, record_count, total_credits, total_debits, period_start, period_end
            FROM uploads
            WHERE id = ? AND user_id = ?
            """,
            (upload_id, user_id),
        )
        row = cur.fetchone()
        return dict(row) if row else None
