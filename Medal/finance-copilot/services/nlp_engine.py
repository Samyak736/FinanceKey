from __future__ import annotations

import json
import re
from typing import Any

from config import GEMINI_API_KEY, LLM_PROVIDER, OPENAI_API_KEY

INTENT_SCHEMA_HINT = """
Return ONLY valid JSON with keys:
intent: one of [compare, summary, overspend, category_breakdown, savings, merchant, monthly_trend,
health_score, subscriptions, biggest_category, reduce_spending, anomalies, unknown]
category: string or null (e.g. Food, Travel)
time_range_months: integer or null
merchant: string or null
"""


def _rule_based_intent(query: str) -> dict[str, Any]:
    q = query.lower().strip()
    intent = "unknown"
    category = None
    months = None
    merchant = None

    m = re.search(r"(\d+)\s*months?", q)
    if m:
        months = int(m.group(1))

    cats = ["food", "travel", "shopping", "subscriptions", "housing", "utilities", "healthcare"]
    for c in cats:
        if c in q:
            category = c.title()
            break

    if "health" in q and ("score" in q or "financial" in q):
        intent = "health_score"
    elif "biggest" in q and ("expense" in q or "spending" in q) and "category" in q:
        intent = "biggest_category"
    elif "largest" in q and "category" in q and ("spend" in q or "expense" in q):
        intent = "biggest_category"
    elif (
        ("reduce" in q and "spend" in q)
        or ("cut" in q and "spend" in q)
        or ("where" in q and "reduce" in q)
        or "where can i save" in q
    ):
        intent = "reduce_spending"
    elif "anomal" in q or "unusual" in q or "spike" in q:
        intent = "anomalies"
    elif ("subscription" in q or "recurring" in q) and any(
        w in q
        for w in [
            "list",
            "detect",
            "show",
            "what are",
            "which",
            "what",
            "do i have",
            "tell me",
        ]
    ):
        intent = "subscriptions"
    elif "compare" in q or ("last" in q and "month" in q):
        intent = "compare"
    elif "pie" in q or "breakdown" in q or ("category" in q and "distribution" in q):
        intent = "category_breakdown"
    elif "show" in q and "category" in q and "breakdown" in q:
        intent = "category_breakdown"
    elif "show" in q and "monthly" in q and "trend" in q:
        intent = "monthly_trend"
    elif "overspend" in q or "too much" in q or ("where" in q and "spend" in q):
        intent = "overspend"
    elif "save" in q and "subscription" in q:
        intent = "savings"
    elif ("subscription" in q or "recurring" in q) and any(
        k in q for k in ["reduce", "cut", "lower", "cancel", "trim", "too many", "cheaper"]
    ):
        intent = "savings"
    elif "save" in q:
        intent = "savings"
    elif "zomato" in q or "swiggy" in q or "uber" in q:
        intent = "merchant"
        merchant = "zomato" if "zomato" in q else "swiggy" if "swiggy" in q else "uber"
    elif "trend" in q or ("month" in q and "trend" in q):
        intent = "monthly_trend"
    elif "summary" in q or "overview" in q or "total" in q:
        intent = "summary"
    else:
        intent = "summary"

    if intent == "compare" and months is None:
        months = 3
    if intent in {"compare", "monthly_trend"} and months is None:
        months = 3

    return {
        "intent": intent,
        "category": category,
        "time_range_months": months,
        "merchant": merchant,
    }


def _openai_parse(query: str) -> dict[str, Any] | None:
    if not OPENAI_API_KEY:
        return None
    try:
        from openai import OpenAI
    except ImportError:
        return None

    client = OpenAI(api_key=OPENAI_API_KEY)
    completion = client.chat.completions.create(
        model="gpt-4o-mini",
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": "You extract structured intents for a finance app. " + INTENT_SCHEMA_HINT},
            {"role": "user", "content": query},
        ],
        temperature=0,
    )
    text = completion.choices[0].message.content or "{}"
    return json.loads(text)


def _gemini_parse(query: str) -> dict[str, Any] | None:
    if not GEMINI_API_KEY:
        return None
    try:
        import google.generativeai as genai
    except ImportError:
        return None

    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel("gemini-1.5-flash")
    resp = model.generate_content(
        "Extract intent JSON. " + INTENT_SCHEMA_HINT + "\nUser: " + query
    )
    text = resp.text or "{}"
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?", "", text).strip("` \n")
    return json.loads(text)


def detect_intent(user_query: str) -> dict[str, Any]:
    structured: dict[str, Any] | None = None
    try:
        if LLM_PROVIDER == "gemini":
            structured = _gemini_parse(user_query)
        else:
            structured = _openai_parse(user_query)
    except Exception:  # noqa: BLE001
        structured = None

    if structured and isinstance(structured, dict) and structured.get("intent"):
        return {
            "intent": structured.get("intent", "unknown"),
            "category": structured.get("category"),
            "time_range_months": structured.get("time_range_months"),
            "merchant": structured.get("merchant"),
        }
    return _rule_based_intent(user_query)
