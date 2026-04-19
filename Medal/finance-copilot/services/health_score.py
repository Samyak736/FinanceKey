from __future__ import annotations

from typing import Any

import pandas as pd


def _band(score: int) -> str:
    if score >= 80:
        return "Strong"
    if score >= 65:
        return "Good"
    if score >= 50:
        return "Fair"
    return "Needs attention"


def compute_health_score(df: pd.DataFrame) -> dict[str, Any]:
    """0–100 score: savings behaviour (40) + monthly consistency (30) + spend mix (30)."""
    if df.empty:
        return {
            "score": 0,
            "band": "No data",
            "headline": "Upload transactions to calculate your score.",
            "components": {"savings_ratio": 0.0, "consistency": 0.0, "budget_mix": 0.0},
            "notes": [],
        }

    income = float(df.loc[df["amount"] > 0, "amount"].sum())
    expense = float(-df.loc[df["amount"] < 0, "amount"].sum())
    net = income - expense

    if income > 0:
        savings_ratio = max(0.0, min(net / income, 1.0))
    elif expense == 0:
        savings_ratio = 0.5
    else:
        savings_ratio = 0.0

    exp_df = df[df["amount"] < 0].copy()
    exp_df["spent"] = -exp_df["amount"]
    exp_df["month"] = exp_df["date"].dt.to_period("M").astype(str)
    monthly = exp_df.groupby("month", as_index=False)["spent"].sum()["spent"]

    if len(monthly) >= 3 and float(monthly.mean()) > 0:
        cv = float(monthly.std() / monthly.mean())
        consistency = max(0.0, 1.0 - min(cv / 1.25, 1.0))
    elif len(monthly) >= 2 and float(monthly.mean()) > 0:
        cv = float(monthly.std() / monthly.mean())
        consistency = max(0.0, 1.0 - min(cv / 1.5, 1.0)) * 0.9
    else:
        consistency = 0.55

    notes: list[str] = []
    food_total = float(exp_df.loc[exp_df["category"].str.lower() == "food", "spent"].sum())
    shopping_total = float(exp_df.loc[exp_df["category"].str.lower() == "shopping", "spent"].sum())
    food_share = food_total / expense if expense > 0 else 0.0
    shopping_share = shopping_total / expense if expense > 0 else 0.0

    if expense <= 0:
        budget_mix = 0.4
    else:
        discretionary = (food_total + shopping_total) / expense
        target = 0.38
        if discretionary > target:
            over = discretionary - target
            budget_mix = max(0.0, 1.0 - min(over / 0.35, 1.0))
            if food_share > 0.22:
                notes.append("Food is a large share of spending.")
            if shopping_share > 0.18:
                notes.append("Shopping spend is elevated vs typical budgets.")
        else:
            budget_mix = min(1.0, 0.75 + (target - discretionary))

    raw = savings_ratio * 40 + consistency * 30 + budget_mix * 30
    score = int(max(0, min(100, round(raw))))
    band = _band(score)

    if not notes and food_share > 0.28:
        notes.append("Food spending is higher than the 25–30% guideline.")

    if notes:
        headline = f"Your Financial Health Score: {score}/100 ({band}, {notes[0].rstrip('.')})."
    else:
        headline = f"Your Financial Health Score: {score}/100 ({band})."

    return {
        "score": score,
        "band": band,
        "headline": headline,
        "components": {
            "savings_ratio": round(savings_ratio, 3),
            "consistency": round(consistency, 3),
            "budget_mix": round(budget_mix, 3),
        },
        "notes": notes,
        "savings_rate_pct": round((net / income * 100), 1) if income > 0 else 0.0,
    }
