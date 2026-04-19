from functools import wraps

from flask import jsonify, redirect, request, session, url_for


def current_user_id() -> int | None:
    return session.get("user_id")


def login_required_page(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if current_user_id() is None:
            return redirect(url_for("auth.login"))
        return view(*args, **kwargs)

    return wrapped


def login_required_api(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if current_user_id() is None:
            return jsonify({"error": "Authentication required."}), 401
        return view(*args, **kwargs)

    return wrapped
