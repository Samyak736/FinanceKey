from flask import Blueprint, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from models.user import create_user, get_user_by_id, get_user_by_username

auth_bp = Blueprint("auth", __name__)


@auth_bp.get("/login")
def login():
    if session.get("user_id"):
        return redirect(url_for("index"))
    return render_template("login.html", error=None)


@auth_bp.post("/login")
def login_post():
    username = (request.form.get("username") or "").strip()
    password = request.form.get("password") or ""
    if not username or not password:
        return render_template("login.html", error="Enter both username and password.")

    user = get_user_by_username(username)
    if user is None or not check_password_hash(user["password_hash"], password):
        return render_template("login.html", error="Invalid username or password.")

    session.clear()
    session["user_id"] = user["id"]
    return redirect(url_for("index"))


@auth_bp.get("/register")
def register():
    if session.get("user_id"):
        return redirect(url_for("index"))
    return render_template("register.html", error=None)


@auth_bp.post("/register")
def register_post():
    username = (request.form.get("username") or "").strip()
    password = request.form.get("password") or ""
    if not username or not password:
        return render_template("register.html", error="Create both username and password.")
    if len(password) < 6:
        return render_template("register.html", error="Password must be at least 6 characters.")

    try:
        create_user(username, generate_password_hash(password))
    except ValueError as exc:
        return render_template("register.html", error=str(exc))

    return redirect(url_for("auth.login"))


@auth_bp.get("/logout")
def logout():
    session.clear()
    return redirect(url_for("auth.login"))
