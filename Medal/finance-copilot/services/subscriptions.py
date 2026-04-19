from __future__ import annotations

from typing import Any

import pandas as pd


def _merchant_key(description: str) -> str:
    """Fold common brand variants so 'Netflix' and 'Netflix Subscription' merge."""
    d = str(description).strip().lower()
    if "netflix" in d:
        return "netflix"
    if "spotify" in d:
        return "spotify"
    if "youtube" in d and "premium" in d:
        return "youtube premium"
    return d


def detect_recurring_subscriptions(
    df: pd.DataFrame, *, exclude_bills: bool = True
) -> list[dict[str, Any]]:
    """
    Heuristic: same normalized merchant + same charge amount, ≥2 charges,
    median gap between charges roughly monthly (~20–42 days).

    By default skips Housing/Utilities so rent and power bills do not crowd
    discretionary “subscription-style” merchants in demos.
    """
    if df.empty:
        return []

    exp = df[df["amount"] < 0].copy()
    if exp.empty:
        return []

    if exclude_bills:
        exp = exp[~exp["category"].isin(["Housing", "Utilities"])]

    exp["merchant_key"] = exp["description"].map(_merchant_key)
    exp["monthly_charge"] = -exp["amount"]
    exp = exp.sort_values("date")

    found: list[dict[str, Any]] = []
    for (mkey, charge_amt), grp in exp.groupby(["merchant_key", "amount"]):
        if len(grp) < 2:
            continue
        diffs = grp["date"].diff().dt.days.dropna()
        if diffs.empty:
            continue
        med = float(diffs.median())
        if not (20 <= med <= 42):
            continue
        label = str(grp.iloc[-1]["description"]).strip()[:80]
        monthly = float(-charge_amt)
        found.append(
            {
                "merchant": label,
                "amount_monthly": round(monthly, 2),
                "occurrences": int(len(grp)),
                "cadence_days": round(med, 1),
            }
        )

    found.sort(key=lambda r: r["amount_monthly"] * r["occurrences"], reverse=True)
    return found


def subscription_summary(rows: list[dict[str, Any]]) -> tuple[str, float]:
    if not rows:
        return ("No recurring charges detected from this statement window.", 0.0)
    total = sum(r["amount_monthly"] for r in rows)
    lines = [f"{r['merchant']}: ₹{r['amount_monthly']:,.0f}/mo ({r['occurrences']} hits)" for r in rows[:8]]
    tail = f"Total subscriptions (detected): ₹{total:,.0f}/month."
    return ("\n".join(lines) + "\n" + tail, float(total))
