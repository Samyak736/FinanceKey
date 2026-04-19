from __future__ import annotations

from datetime import timedelta
from typing import Any

import pandas as pd


def _load_df(rows: list[dict]) -> pd.DataFrame:
    if not rows:
        return pd.DataFrame(columns=["date", "description", "amount", "category"])
    df = pd.DataFrame(rows)
    df["date"] = pd.to_datetime(df["date"])
    return df


def spending_change_vs_prior(df: pd.DataFrame, category: str | None = None) -> str | None:
    if df.empty:
        return None
    now = df["date"].max()
    if pd.isna(now):
        return None
    window_end = now
    window_start = now - timedelta(days=30)
    prior_start = window_start - timedelta(days=30)
    if category is None:
        sub = df[df["amount"] < 0].copy()
    else:
        sub = df[df["category"].str.lower() == category.lower()].copy()
        sub = sub[sub["amount"] < 0]
    if sub.empty:
        return None
    cur = sub[(sub["date"] > window_start) & (sub["date"] <= window_end)]["amount"].sum()
    prev = sub[(sub["date"] > prior_start) & (sub["date"] <= window_start)]["amount"].sum()
    if prev == 0:
        return None
    pct = int(round((cur - prev) / abs(prev) * 100)) if prev != 0 else 0
    label = category or "overall"
    direction = "increased" if pct > 0 else "decreased"
    return f"{label.title()} spending {direction} by {abs(pct)}% vs the prior month."


def top_spending_category(df: pd.DataFrame) -> str | None:
    if df.empty:
        return None
    expenses = df[df["amount"] < 0].copy()
    if expenses.empty:
        return None
    expenses["spent"] = -expenses["amount"]
    top = expenses.groupby("category", as_index=False)["spent"].sum().sort_values(
        "spent", ascending=False
    )
    if top.empty:
        return None
    name = top.iloc[0]["category"]
    val = top.iloc[0]["spent"]
    return f"Your highest spending category is {name} (about ₹{val:,.0f} total)."


def merchant_spike(df: pd.DataFrame, top_n: int = 3) -> str | None:
    if df.empty:
        return None
    expenses = df[df["amount"] < 0].copy()
    if expenses.empty:
        return None
    expenses["spent"] = -expenses["amount"]
    by_m = expenses.groupby("description", as_index=False)["spent"].sum().sort_values(
        "spent", ascending=False
    )
    if by_m.empty:
        return None
    row = by_m.iloc[0]
    return f"Largest merchant concentration: {row['description'][:40]} (~₹{row['spent']:,.0f})."


def subscription_savings_tip(df: pd.DataFrame) -> str | None:
    sub = df[df["category"].str.lower() == "subscriptions"]
    if sub.empty or (sub["amount"] >= 0).all():
        return None
    monthly = -sub[sub["amount"] < 0]["amount"].sum()
    if monthly <= 0:
        return None
    save = monthly * 0.25
    return f"You could save about ₹{save:,.0f}/mo by trimming ~25% of subscription spend (currently ~₹{monthly:,.0f})."


def cash_flow_summary(df: pd.DataFrame) -> str | None:
    if df.empty:
        return None
    income = df[df["amount"] > 0]["amount"].sum()
    spent = -df[df["amount"] < 0]["amount"].sum()
    net = income - spent
    return f"Income ₹{income:,.0f} vs expenses ₹{spent:,.0f}; net cash flow ≈ ₹{net:,.0f}."


def build_insight_bundle(rows: list[dict]) -> list[str]:
    df = _load_df(rows)
    out: list[str] = []
    for fn in (
        cash_flow_summary,
        top_spending_category,
        lambda d: spending_change_vs_prior(d, "Food"),
        merchant_spike,
        subscription_savings_tip,
    ):
        msg = fn(df)  # type: ignore[arg-type]
        if msg:
            out.append(msg)
    return out[:5]
