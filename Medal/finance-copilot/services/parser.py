from __future__ import annotations

import io
from datetime import datetime
from typing import Any

import pandas as pd


DATE_ALIASES = {"date", "transaction date", "txn date", "posted date", "value date"}
DESC_ALIASES = {"description", "desc", "narration", "particulars", "merchant", "details"}
AMOUNT_ALIASES = {"amount", "debit", "credit", "value"}
TYPE_ALIASES = {"type", "dr/cr", "d/c", "transaction type"}


def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    mapping = {c: str(c).strip().lower() for c in df.columns}
    df = df.rename(columns=mapping)
    cols = set(df.columns)

    def pick(*candidates: str) -> str | None:
        for c in candidates:
            if c in cols:
                return c
        for col in df.columns:
            lc = col.lower()
            for cand in candidates:
                if lc == cand or lc.replace(" ", "") == cand.replace(" ", ""):
                    return col
        return None

    date_col = None
    for alias in DATE_ALIASES:
        date_col = pick(alias) or date_col
    desc_col = None
    for alias in DESC_ALIASES:
        desc_col = pick(alias) or desc_col

    amt_col = None
    for alias in AMOUNT_ALIASES:
        amt_col = pick(alias) or amt_col

    type_col = pick(*TYPE_ALIASES)

    if not date_col or not desc_col:
        raise ValueError(
            "CSV must include recognizable date and description columns "
            f"(found: {list(df.columns)})"
        )
    if not amt_col and not (pick("debit") and pick("credit")):
        raise ValueError("CSV must include an amount column or separate debit/credit columns")

    out = pd.DataFrame()
    out["date"] = pd.to_datetime(df[date_col], errors="coerce", format="mixed", dayfirst=False)
    out["description"] = df[desc_col].astype(str).fillna("")

    debit_col = pick("debit")
    credit_col = pick("credit")
    if amt_col:
        amounts = pd.to_numeric(df[amt_col], errors="coerce").fillna(0.0)
        out["amount"] = amounts
    else:
        debit = pd.to_numeric(df[debit_col], errors="coerce").fillna(0.0) if debit_col else 0.0
        credit = pd.to_numeric(df[credit_col], errors="coerce").fillna(0.0) if credit_col else 0.0
        out["amount"] = credit - debit

    if type_col:
        t = df[type_col].astype(str).str.lower()
        out.loc[t.str.contains("cr|credit|income|deposit"), "amount"] = out["amount"].abs()
        out.loc[t.str.contains("dr|debit|expense|withdraw"), "amount"] = -out["amount"].abs()

    out = out.dropna(subset=["date"])
    if out.empty:
        raise ValueError("No valid rows after parsing dates")

    return out


def parse_csv_bytes(raw: bytes) -> list[dict[str, Any]]:
    buffer = io.BytesIO(raw)
    try:
        df = pd.read_csv(buffer)
    except Exception as exc:  # noqa: BLE001
        raise ValueError(f"Could not read CSV: {exc}") from exc

    if df.empty:
        raise ValueError("CSV is empty")

    normalized = _normalize_columns(df)
    records: list[dict[str, Any]] = []
    for _, row in normalized.iterrows():
        d: datetime = row["date"]
        amt = float(row["amount"])
        if amt > 0:
            tx_type = "income"
        elif amt < 0:
            tx_type = "expense"
        else:
            tx_type = "neutral"
        records.append(
            {
                "date": d.strftime("%Y-%m-%d"),
                "desc": str(row["description"]).strip(),
                "amount": amt,
                "type": tx_type,
            }
        )
    return records
