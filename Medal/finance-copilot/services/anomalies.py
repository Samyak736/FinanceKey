from __future__ import annotations

from typing import Any

import pandas as pd


def detect_spending_anomalies(df: pd.DataFrame, multiplier: float = 2.0) -> list[dict[str, Any]]:
    """
    Flag expenses where spend > multiplier × category average spend (same category).
    """
    if df.empty:
        return []

    exp = df[df["amount"] < 0].copy()
    if exp.empty:
        return []

    exp["spent"] = -exp["amount"]
    results: list[dict[str, Any]] = []

    for cat, grp in exp.groupby("category"):
        if len(grp) < 2:
            baseline = float(exp["spent"].mean())
        else:
            baseline = float(grp["spent"].mean())
        if baseline <= 0:
            continue
        for _, row in grp.iterrows():
            spent = float(row["spent"])
            if spent <= baseline * multiplier:
                continue
            ratio = spent / baseline if baseline > 0 else 0.0
            results.append(
                {
                    "date": row["date"].strftime("%Y-%m-%d") if hasattr(row["date"], "strftime") else str(row["date"])[:10],
                    "description": str(row["description"])[:120],
                    "category": str(row["category"]),
                    "amount": round(spent, 2),
                    "category_avg": round(baseline, 2),
                    "ratio_vs_avg": round(ratio, 2),
                }
            )

    results.sort(key=lambda r: r["ratio_vs_avg"], reverse=True)
    return results[:12]
