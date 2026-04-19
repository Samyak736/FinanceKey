from __future__ import annotations

import sqlite3
from pathlib import Path

from flask import Blueprint, jsonify, redirect, request, send_from_directory, url_for

from config import BASE_DIR
from models import transaction as tx_model
from models.upload_history import insert_upload
from services.auth import current_user_id, login_required_api
from services.categorizer import apply_categories
from services.parser import parse_csv_bytes

upload_bp = Blueprint("upload", __name__)


@upload_bp.get("/sample-csv")
def download_sample_csv():
    return send_from_directory(Path(BASE_DIR) / "data", "sample.csv", as_attachment=True)


@upload_bp.route("/upload", methods=["POST"])
@login_required_api
def upload_csv():
    if "file" not in request.files:
        return jsonify({"error": "Missing file field `file`."}), 400
    file = request.files["file"]
    if not file or file.filename == "":
        return jsonify({"error": "Empty filename."}), 400

    raw = file.read()
    try:
        records = parse_csv_bytes(raw)
        categorized = apply_categories(records)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    user_id = current_user_id()
    if user_id is None:
        return jsonify({"error": "Authentication required."}), 401

    total_credits = sum(float(r["amount"]) for r in categorized if float(r["amount"]) > 0)
    total_debits = sum(-float(r["amount"]) for r in categorized if float(r["amount"]) < 0)
    dates = sorted(r["date"] for r in categorized if r.get("date"))
    period_start = dates[0] if dates else None
    period_end = dates[-1] if dates else None

    replace = request.form.get("replace", "true").lower() != "false"
    try:
        if replace:
            tx_model.clear_user_transactions(user_id)
        inserted = tx_model.insert_transactions(categorized, user_id)
        insert_upload(
            user_id=user_id,
            filename=file.filename,
            record_count=len(categorized),
            total_credits=total_credits,
            total_debits=total_debits,
            period_start=period_start,
            period_end=period_end,
        )
    except sqlite3.OperationalError as exc:
        return jsonify(
            {
                "error": (
                    "Could not write to the database (disk full, read-only filesystem, or "
                    "SQLite locked). On cloud hosts, use a persistent volume for DATABASE_PATH "
                    f"or a single worker. Details: {exc}"
                )
            }
        ), 500

    wants_redirect = request.args.get("redirect") == "1"
    if wants_redirect:
        return redirect(url_for("dashboard_page"))

    return jsonify({"inserted": inserted, "preview": categorized[:5]})


@upload_bp.route("/parse-preview", methods=["POST"])
@login_required_api
def parse_preview():
    if "file" not in request.files:
        return jsonify({"error": "Missing file field `file`."}), 400
    file = request.files["file"]
    raw = file.read()
    try:
        records = parse_csv_bytes(raw)
        categorized = apply_categories(records)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify({"rows": categorized[:20], "total": len(categorized)})
