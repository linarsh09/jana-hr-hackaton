from flask import Blueprint, render_template, request, session, redirect, url_for
from .service import AccountService
from .validators import validate_login_form, validate_register_form
from app.core.permissions import login_required, role_required


account_bp = Blueprint(
    "users",
    __name__,
    url_prefix="/account",
)


@account_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("account/login.html")

    username = request.form.get("username")
    password = request.form.get("password")

    data, errors = validate_login_form(username, password)

    if errors:
        return render_template(
            "account/login.html",
            errors=errors,
            username=username or "",
        ), 400

    account_service = AccountService()
    user = account_service.login_user(
        data["username"],
        data["password"],
    )

    if user is None:
        return render_template(
            "account/login.html",
            errors={"general": "Неверный логин или пароль."},
            username=data["username"],
        ), 401

    # Сохраняем состояние авторизации.
    session.clear()
    session["user_id"] = user.id

    # Перенаправляем на профиль.
    return redirect("/account/profile")


@account_bp.route("/profile", methods=["GET"])
@login_required
def profile():
    user_id = session.get("user_id")

    if user_id is None:
        return redirect(url_for("users.login"))

    return render_template("admin/index.html")


@account_bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "GET":
        return render_template("account/register.html")

    username = request.form.get("username")
    password = request.form.get("password")

    data, errors = validate_register_form(username, password)

    if errors:
        return render_template(
            "account/register.html",
            errors=errors,
            username=username or "",
        ), 400

    try:
        user = AccountService.register_user(
            data["username"],
            data["password"],
        )
    except Exception:
        # Откатываем транзакцию, если произошла ошибка БД.
        from app.extensions import db
        db.session.rollback()
        raise

    if user is None:
        return render_template(
            "account/register.html",
            errors={"general": "Этот логин уже занят."},
            username=data["username"],
        ), 409

    return redirect(url_for("users.login"))

@account_bp.route("/logout", methods=["POST"])
def logout():
    session.clear()

    return redirect(url_for("users.login"))
