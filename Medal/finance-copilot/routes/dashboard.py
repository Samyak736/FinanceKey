from __future__ import annotations

from flask import Blueprint, jsonify, render_template, redirect, url_for

import pandas as pd

from models import transaction as tx_model
from models.upload_history import get_upload_by_id, list_uploads_for_user
from services import insights as insight_svc
from services.anomalies import detect_spending_anomalies
from services.auth import current_user_id, login_required_api, login_required_page
from services.health_score import compute_health_score
from services.subscriptions import detect_recurring_subscriptions, subscription_summary

dashboard_bp = Blueprint("dashboard", __name__, url_prefix="/api/dashboard")


def _frame(user_id: int) -> pd.DataFrame:
    rows = tx_model.fetch_all_for_user(user_id)
    if not rows:
        return pd.DataFrame(columns=["date", "description", "amount", "category"])
    df = pd.DataFrame(rows)
    df["date"] = pd.to_datetime(df["date"])
    return df


@dashboard_bp.route("/summary", methods=["GET"])
@login_required_api
def summary():
    df = _frame(current_user_id())
    if df.empty:
        return jsonify(
            {
                "income": 0,
                "expense": 0,
                "net": 0,
                "savings_rate": 0,
            }
        )
    income = float(df[df["amount"] > 0]["amount"].sum())
    expense = float(-df[df["amount"] < 0]["amount"].sum())
    net = income - expense
    savings_rate = (net / income * 100) if income > 0 else 0
    return jsonify(
        {
            "income": income,
            "expense": expense,
            "net": net,
            "savings_rate": round(savings_rate, 1),
        }
    )


@dashboard_bp.route("/category-breakdown", methods=["GET"])
@login_required_api
def category_breakdown():
    user_id = current_user_id()
    df = _frame(user_id)
    expenses = df[df["amount"] < 0].copy()
    if expenses.empty:
        return jsonify({"breakdown": []})
    expenses["spent"] = -expenses["amount"]
    agg = (
        expenses.groupby("category", as_index=False)["spent"]
        .sum()
        .sort_values("spent", ascending=False)
    )
    return jsonify({"breakdown": agg.to_dict(orient="records")})


@dashboard_bp.route("/monthly-trend", methods=["GET"])
@login_required_api
def monthly_trend():
    user_id = current_user_id()
    df = _frame(user_id)
    if df.empty:
        return jsonify({"series": []})
    df = df.copy()
    df["month"] = df["date"].dt.to_period("M").astype(str)
    income = df[df["amount"] > 0].groupby("month", as_index=False)["amount"].sum()
    expense = df[df["amount"] < 0].copy()
    expense["spent"] = -expense["amount"]
    exp_agg = expense.groupby("month", as_index=False)["spent"].sum()
    merged = pd.merge(
        income.rename(columns={"amount": "income"}),
        exp_agg.rename(columns={"spent": "expense"}),
        on="month",
        how="outer",
    ).fillna(0)
    merged["savings"] = merged["income"] - merged["expense"]
    return jsonify({"series": merged.to_dict(orient="records")})


@dashboard_bp.route("/insights", methods=["GET"])
@login_required_api
def insights_endpoint():
    user_id = current_user_id()
    rows = tx_model.fetch_all_for_user(user_id)
    bundle = insight_svc.build_insight_bundle(rows)
    return jsonify({"insights": bundle})


@dashboard_bp.route("/health-score", methods=["GET"])
@login_required_api
def health_score():
    df = _frame(current_user_id())
    payload = compute_health_score(df)
    return jsonify(payload)


@dashboard_bp.route("/subscriptions", methods=["GET"])
@login_required_api
def subscriptions():
    df = _frame(current_user_id())
    rows = detect_recurring_subscriptions(df)
    text, total = subscription_summary(rows)
    return jsonify({"subscriptions": rows, "summary": text, "monthly_total": total})


@dashboard_bp.route("/anomalies", methods=["GET"])
@login_required_api
def anomalies():
    df = _frame(current_user_id())
    rows = detect_spending_anomalies(df)
    return jsonify({"anomalies": rows})


def register_pages(app):
    @app.get("/")
    @login_required_page
    def index():
        history = list_uploads_for_user(current_user_id())
        return render_template("index.html", history=history)

    @app.get("/dashboard")
    @login_required_page
    def dashboard_page():
        return render_template("dashboard.html")

    @app.get("/uploads/<int:upload_id>")
    @login_required_page
    def upload_detail_page(upload_id: int):
        upload = get_upload_by_id(upload_id, current_user_id())
        if not upload:
            return redirect(url_for("index"))
        return render_template("upload_detail.html", upload=upload)
