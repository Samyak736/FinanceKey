from __future__ import annotations

from flask import Blueprint, jsonify, request

from config import LLM_PROVIDER, OPENAI_API_KEY, GEMINI_API_KEY
from models import transaction as tx_model
from services.auth import current_user_id, login_required_api

copilot_bp = Blueprint("copilot", __name__, url_prefix="/api/copilot")


def _get_user_data(user_id: int) -> str:
    rows = tx_model.fetch_all_for_user(user_id)
    if not rows:
        return "No transaction data available."
    csv_lines = ["date,description,amount,category"]
    for row in rows:
        csv_lines.append(f"{row['date']},{row['description']},{row['amount']},{row['category']}")
    return "\n".join(csv_lines)


def _openai_query(query: str, data: str) -> str:
    if not OPENAI_API_KEY:
        return "OpenAI API key not configured."
    try:
        from openai import OpenAI
    except ImportError:
        return "OpenAI library not installed."

    client = OpenAI(api_key=OPENAI_API_KEY)
    prompt = f"""
You are a financial copilot. Analyze the user's transaction data (CSV format below) and answer their query in a helpful, concise way.

Transaction Data:
{data}

User Query: {query}

Provide a brief insight or answer based on the data.
"""
    completion = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
        max_tokens=500,
    )
    return completion.choices[0].message.content or "No response from OpenAI."


def _gemini_query(query: str, data: str) -> str:
    if not GEMINI_API_KEY:
        return "Gemini API key not configured."
    try:
        import google.generativeai as genai
    except ImportError:
        return "Gemini library not installed."

    genai.configure(api_key=GEMINI_API_KEY)
    
    # List available models and pick the first one that supports generateContent
    try:
        models = list(genai.list_models())
        supported_models = [m for m in models if 'generateContent' in m.supported_generation_methods]
        if not supported_models:
            return "No supported Gemini models found."
        model_name = supported_models[0].name  # e.g., 'models/gemini-1.0-pro'
        model = genai.GenerativeModel(model_name.split('/')[-1])  # Extract name after 'models/'
    except Exception as e:
        return f"Error listing models: {e}"

    prompt = f"""
You are a financial copilot. Analyze the user's transaction data (CSV format below) and answer their query in a helpful, concise way.

Transaction Data:
{data}

User Query: {query}

Provide a brief insight or answer based on the data.
"""
    try:
        resp = model.generate_content(prompt)
        return resp.text or "No response from Gemini."
    except Exception as e:
        return f"Gemini error: {e}"


@copilot_bp.route("/query", methods=["POST"])
@login_required_api
def copilot_query():
    body = request.get_json(silent=True) or {}
    query = (body.get("query") or "").strip()
    if not query:
        return jsonify({"error": "query is required"}), 400

    user_id = current_user_id()
    if user_id is None:
        return jsonify({"error": "Authentication required."}), 401

    data = _get_user_data(user_id)

    if LLM_PROVIDER == "gemini":
        insight = _gemini_query(query, data)
    else:
        insight = _openai_query(query, data)

    return jsonify(
        {
            "insight": insight,
            "data": {},
            "chart": "none",
        }
    )
