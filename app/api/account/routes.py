from flask import Blueprint, render_template, request, session, redirect, url_for, g, flash
from .service import AccountService
from .validators import validate_login_form, validate_register_form
from app.core.permissions import login_required, role_required
from app.models import UserRole
from app.api.vacations.service import VacationService


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
    return redirect(url_for("users.profile"))


@account_bp.route("/profile", methods=["GET"])
@login_required
def profile():
    employee = g.current_user.employee
    available_days = VacationService.get_available_days(employee.id) if employee else None
    return render_template(
        "account/profile.html",
        user=g.current_user,
        employee=employee,
        available_days=available_days,
    )


@account_bp.route("/requests", methods=["GET"])
@login_required
@role_required(UserRole.EMPLOYEE, UserRole.MANAGER, UserRole.HR, UserRole.ADMIN)
def requests_page():
    return render_template(
        "account/requests.html",
        user=g.current_user,
        # TODO: Коллега подключит создание и выборку заявок с разграничением по ролям.
    )


@account_bp.route("/courses", methods=["GET"])
@login_required
def courses_page():
    return render_template("account/courses.html", user=g.current_user)


@account_bp.route("/team", methods=["GET"])
@login_required
@role_required(UserRole.MANAGER)
def team_page():
    manager = g.current_user.employee
    employees = manager.direct_reports if manager else []
    return render_template("account/team.html", employees=employees)


@account_bp.route("/password", methods=["POST"])
@login_required
@role_required(UserRole.MANAGER, UserRole.HR, UserRole.ADMIN)
def change_password():
    current_password = request.form.get("current_password", "")
    new_password = request.form.get("new_password", "")
    confirm_password = request.form.get("confirm_password", "")

    if not AccountService.verify_password(g.current_user, current_password):
        flash("Текущий пароль указан неверно.", "danger")
    elif len(new_password) < 8:
        flash("Новый пароль должен содержать минимум 8 символов.", "danger")
    elif new_password != confirm_password:
        flash("Новые пароли не совпадают.", "danger")
    else:
        AccountService.change_password(g.current_user, new_password)
        flash("Пароль успешно изменён.", "success")
    return redirect(url_for("users.profile"))


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
