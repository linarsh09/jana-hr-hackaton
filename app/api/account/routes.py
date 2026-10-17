
from flask import (
    Blueprint,
    render_template,
    request,
    session,
    redirect,
    url_for,
    g,
    flash,
    abort,
)
from app.api.vacations.service import VacationService
from app.extensions import db
from app.models import Role, VacationRequest
from app.core.permissions import login_required, role_required
from .service import AccountService
from .validators import validate_login_form, validate_register_form
from datetime import date

from app.api.account.service import AccountService


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

    user = AccountService.login_user(
        data["username"],
        data["password"],
    )

    if user is None:
        return render_template(
            "account/login.html",
            errors={"general": "Неверный логин или пароль."},
            username=data["username"],
        ), 401

    session.clear()
    session["user_id"] = user.id

    return redirect(url_for("users.profile"))


@account_bp.route("/profile")
@login_required
def profile():
    user = g.current_user
    employee = user.employee

    available_days = (
        VacationService.get_available_days(employee.id)
        if employee
        else None
    )

    return render_template(
        "account/profile.html",
        user=user,
        employee=employee,
        available_days=available_days,
    )

@account_bp.route("/requests")
@login_required
def requests_page():
    user = g.current_user
    employee = user.employee

    role_name = user.role.name if user.role else None

    if role_name == "hr":
        requests = VacationRequest.query.all()

    elif role_name == "manager":
        if employee is None:
            requests = []
        else:
            subordinate_ids = [
                subordinate.id
                for subordinate in employee.subordinates
            ]
            subordinate_ids.append(employee.id)

            requests = VacationRequest.query.filter(
                VacationRequest.employee_id.in_(
                    subordinate_ids
                )
            ).all()

    else:
        requests = (
            employee.vacation_requests
            if employee is not None
            else []
        )

    return render_template(
        "account/requests.html",
        user=user,
        employee=employee,
        requests=requests,
    )


@account_bp.route("/courses")
@login_required
def courses_page():
    return render_template(
        "account/courses.html",
        user=g.current_user,
    )


@account_bp.route("/team")
@role_required("manager", "hr")
def team_page():
    user = g.current_user
    employee = user.employee

    if user.role.name == "hr":
        from app.models import Employee
        employees = Employee.query.all()
    else:
        employees = (
            [report for report in employee.subordinates
             if report.user is not None and report.user.is_active]
            if employee is not None
            else []
        )

    return render_template(
        "account/team.html",
        user=user,
        employees=employees,
    )


@account_bp.route("/password", methods=["POST"])
@login_required
@role_required("manager", "hr")
def change_password():
    user = g.current_user

    current_password = request.form.get(
        "current_password", ""
    )
    new_password = request.form.get(
        "new_password", ""
    )
    confirm_password = request.form.get(
        "confirm_password", ""
    )

    if not AccountService.verify_password(
        user, current_password
    ):
        flash("Текущий пароль неверный.", "danger")

    elif len(new_password) < 8:
        flash(
            "Пароль должен содержать минимум 8 символов.",
            "danger",
        )

    elif new_password != confirm_password:
        flash("Пароли не совпадают.", "danger")

    else:
        AccountService.change_password(
            user, new_password
        )
        flash("Пароль успешно изменён.", "success")

    return redirect(url_for("users.profile"))


@account_bp.route("/register", methods=["GET", "POST"])
@role_required("hr")
def register():
    # Создавать учётные записи может только HR.
    # По умолчанию новому пользователю назначается роль employee.
    if request.method == "GET":
        return render_template("account/register.html")

    username = request.form.get("username")
    password = request.form.get("password")

    data, errors = validate_register_form(
        username, password
    )

    if errors:
        return render_template(
            "account/register.html",
            errors=errors,
            username=username or "",
        ), 400

    employee_role = Role.query.filter_by(
        name="employee"
    ).first()

    if employee_role is None:
        return render_template(
            "account/register.html",
            errors={
                "general": "Роль сотрудника не создана."
            },
            username=data["username"],
        ), 503

    try:
        user = AccountService.register_user(
            username=data["username"],
            password=data["password"],
            role_id=employee_role.id,
        )
    except Exception:
        db.session.rollback()
        raise

    if user is None:
        return render_template(
            "account/register.html",
            errors={
                "general": "Этот логин уже занят."
            },
            username=data["username"],
        ), 409

    flash("Аккаунт создан. Войдите в систему.", "success")
    return redirect(url_for("users.login"))


@account_bp.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return redirect(url_for("users.login"))
