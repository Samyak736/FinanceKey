from __future__ import annotations

from typing import Any

import pandas as pd

from models.db import get_cursor
from services import insights as insight_svc
from services.anomalies import detect_spending_anomalies
from services.health_score import compute_health_score
from services.subscriptions import detect_recurring_subscriptions, subscription_summary


def _fetch_rows(user_id: int) -> list[dict]:
    with get_cursor() as cur:
        cur.execute(
            """
            SELECT date, description, amount, category
            FROM transactions
            WHERE user_id = ?
            ORDER BY date ASC
            """,
            (user_id,),
        )
        return [dict(row) for row in cur.fetchall()]


def _df(user_id: int) -> pd.DataFrame:
    rows = _fetch_rows(user_id)
    if not rows:
        return pd.DataFrame(columns=["date", "description", "amount", "category"])
    df = pd.DataFrame(rows)
    df["date"] = pd.to_datetime(df["date"])
    return df


def _filter_months(df: pd.DataFrame, months: int | None) -> pd.DataFrame:
    if df.empty or not months:
        return df
    end = df["date"].max()
    if pd.isna(end):
        return df
    start = end - pd.DateOffset(months=months)
    return df[df["date"] >= start]


def run_intent(user_id: int, intent_payload: dict[str, Any]) -> dict[str, Any]:
    intent = (intent_payload.get("intent") or "unknown").lower()
    category = intent_payload.get("category")
    months = intent_payload.get("time_range_months")
    merchant_kw = (intent_payload.get("merchant") or "").lower()

    df = _df(user_id)
    if df.empty:
        return {
            "insight": "Upload a CSV to unlock answers.",
            "data": {},
            "chart": "none",
        }

    df_win = _filter_months(df, months)

    if intent == "health_score":
        health = compute_health_score(df_win)
        return {
            "insight": health["headline"],
            "data": {"health": health},
            "chart": "none",
        }

    if intent == "subscriptions":
        subs = detect_recurring_subscriptions(df_win)
        text, total = subscription_summary(subs)
        return {
            "insight": text.replace("\n", " • "),
            "data": {"subscriptions": subs, "monthly_total": total},
            "chart": "bar" if subs else "none",
        }

    if intent == "biggest_category":
        tip = insight_svc.top_spending_category(df_win) or "No expense rows yet."
        exp = df_win[df_win["amount"] < 0].copy()
        exp["spent"] = -exp["amount"]
        agg = exp.groupby("category", as_index=False)["spent"].sum().sort_values("spent", ascending=False)
        return {
            "insight": tip,
            "data": {"breakdown": agg.to_dict(orient="records")},
            "chart": "pie",
        }

    if intent == "reduce_spending":
        exp = df_win[df_win["amount"] < 0].copy()
        exp["spent"] = -exp["amount"]
        top_cats = (
            exp.groupby("category", as_index=False)["spent"]
            .sum()
            .sort_values("spent", ascending=False)
            .head(3)
        )
        subs = detect_recurring_subscriptions(df_win)
        sub_text, sub_total = subscription_summary(subs)
        anomalies = detect_spending_anomalies(df_win)
        top_anom = anomalies[0] if anomalies else None
        parts = [
            "Fast wins: trim the top categories below, then review recurring charges.",
            "Top categories: "
            + ", ".join(f"{r['category']} ₹{r['spent']:,.0f}" for _, r in top_cats.iterrows()),
        ]
        if sub_total > 0:
            parts.append(f"Recurring total ≈ ₹{sub_total:,.0f}/mo — cancel unused apps first.")
        if top_anom:
            parts.append(
                f"Largest anomaly: ₹{top_anom['amount']:,.0f} on {top_anom['category']} "
                f"({top_anom['ratio_vs_avg']:.1f}× category avg)."
            )
        return {
            "insight": " ".join(parts),
            "data": {
                "breakdown": top_cats.to_dict(orient="records"),
                "subscriptions": subs,
                "subscription_monthly_total": sub_total,
                "anomalies": anomalies[:5],
            },
            "chart": "pie",
        }

    if intent == "anomalies":
        flags = detect_spending_anomalies(df_win)
        if not flags:
            return {
                "insight": "No anomalies detected with the 2× category-average rule.",
                "data": {"anomalies": []},
                "chart": "none",
            }
        top = flags[0]
        msg = (
            f"Unusual spending: ₹{top['amount']:,.0f} on {top['category']} "
            f"({top['ratio_vs_avg']:.1f}× your average in that category)."
        )
        return {
            "insight": msg,
            "data": {"anomalies": flags},
            "chart": "bar",
        }

    if intent == "compare":
        if category:
            sub = df_win[
                (df_win["category"].str.lower() == category.lower()) & (df_win["amount"] < 0)
            ]
            if sub.empty:
                return {
                    "insight": f"No {category} transactions in range.",
                    "data": {},
                    "chart": "bar",
                }
        else:
            sub = df_win[df_win["amount"] < 0].copy()
        sub = sub.copy()
        sub["month"] = sub["date"].dt.to_period("M").astype(str)
        agg = sub.groupby("month", as_index=False)["amount"].sum()
        agg["spent"] = -agg["amount"].clip(upper=0)
        label = category or "all expenses"
        text = (
            insight_svc.spending_change_vs_prior(sub, category)
            if category
            else insight_svc.spending_change_vs_prior(sub, None)
        ) or f"Monthly trend for {label} ready."
        return {
            "insight": text,
            "data": {"series": agg.to_dict(orient="records")},
            "chart": "bar",
        }

    if intent == "category_breakdown":
        exp = df_win[df_win["amount"] < 0].copy()
        exp["spent"] = -exp["amount"]
        agg = exp.groupby("category", as_index=False)["spent"].sum()
        return {
            "insight": insight_svc.top_spending_category(df_win) or "Category split ready.",
            "data": {"breakdown": agg.to_dict(orient="records")},
            "chart": "pie",
        }

    if intent == "overspend":
        tip = insight_svc.top_spending_category(df_win)
        spike = insight_svc.merchant_spike(df_win)
        msg = " ".join(x for x in (tip, spike) if x)
        exp = df_win[df_win["amount"] < 0].copy()
        exp["spent"] = -exp["amount"]
        agg = exp.groupby("category", as_index=False)["spent"].sum().sort_values("spent", ascending=False)
        return {
            "insight": msg or "Review categories with the largest totals.",
            "data": {"breakdown": agg.to_dict(orient="records")},
            "chart": "pie",
        }

    if intent == "savings":
        subs = detect_recurring_subscriptions(df_win)
        sub_text, sub_total = subscription_summary(subs)
        tip = insight_svc.subscription_savings_tip(df_win)
        tail = (
            " Action: pause one low-use subscription, set a food delivery weekly cap, "
            "and re-run this chat after your next statement."
        )
        insight = " ".join(x for x in (sub_text.replace("\n", " "), tip, tail) if x)
        return {
            "insight": insight.strip(),
            "data": {"subscriptions": subs, "monthly_total": sub_total},
            "chart": "bar" if subs else "none",
        }

    if intent == "merchant":
        if not merchant_kw:
            msg = insight_svc.merchant_spike(df_win) or "No merchant concentration detected."
            exp = df_win[df_win["amount"] < 0].copy()
            exp["spent"] = -exp["amount"]
            top = (
                exp.groupby("description", as_index=False)["spent"]
                .sum()
                .sort_values("spent", ascending=False)
                .head(5)
            )
            return {
                "insight": msg,
                "data": {"merchants": top.to_dict(orient="records")},
                "chart": "bar",
            }
        sub = df_win[df_win["description"].str.lower().str.contains(merchant_kw, na=False)]
        if sub.empty:
            return {"insight": f"No rows matching {merchant_kw}.", "data": {}, "chart": "line"}
        sub = sub.copy()
        sub["month"] = sub["date"].dt.to_period("M").astype(str)
        agg = sub.groupby("month", as_index=False)["amount"].sum()
        agg["spent"] = -agg["amount"].clip(upper=0)
        total = float(agg["spent"].sum())
        return {
            "insight": f"{merchant_kw.title()} spend about ₹{total:,.0f} in selected window.",
            "data": {"series": agg.to_dict(orient="records")},
            "chart": "line",
        }

    if intent == "monthly_trend":
        dfc = df_win.copy()
        dfc["month"] = dfc["date"].dt.to_period("M").astype(str)
        income = dfc[dfc["amount"] > 0].groupby("month", as_index=False)["amount"].sum()
        expense = dfc[dfc["amount"] < 0].copy()
        expense["spent"] = -expense["amount"]
        exp_agg = expense.groupby("month", as_index=False)["spent"].sum()
        merged = pd.merge(
            income.rename(columns={"amount": "income"}),
            exp_agg.rename(columns={"spent": "expense"}),
            on="month",
            how="outer",
        ).fillna(0)
        return {
            "insight": insight_svc.cash_flow_summary(dfc) or "Monthly cash flow trend computed.",
            "data": {"cashflow": merged.to_dict(orient="records")},
            "chart": "line",
        }

    # summary / default
    income = float(df_win[df_win["amount"] > 0]["amount"].sum())
    spent = float(-df_win[df_win["amount"] < 0]["amount"].sum())
    net = income - spent
    return {
        "insight": f"Totals — income ₹{income:,.0f}, expenses ₹{spent:,.0f}, net ₹{net:,.0f}.",
        "data": {"income": income, "expense": spent, "net": net},
        "chart": "none",
    }
