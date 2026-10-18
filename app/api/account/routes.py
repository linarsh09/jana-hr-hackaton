
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
from app.models import Role, VacationRequest, Employee
from app.core.permissions import login_required, role_required, can_manage_employee
from .service import AccountService
from .validators import validate_login_form, validate_register_form
from datetime import date, datetime, timezone
import secrets
from hmac import compare_digest

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

@account_bp.route("/requests", methods=["GET", "POST"])
@login_required
def requests_page():
    user = g.current_user
    employee = user.employee
    role = user.role.name.lower() if user.role else ""
    csrf = session.setdefault("requests_csrf", secrets.token_hex(32))

    if request.method == "POST":
        if not compare_digest(csrf, request.form.get("csrf_token", "")):
            abort(400)
        if role != "employee" or employee is None:
            abort(403)

        try:
            if request.form.get("request_type", "vacation") != "vacation":
                raise ValueError("Пока доступны только заявки на отпуск.")
            VacationService.create_request(
                employee_id=employee.id,
                start_date=date.fromisoformat(request.form["start_date"]),
                end_date=date.fromisoformat(request.form["end_date"]),
                comment=request.form.get("comment", "").strip()[:2000] or None
            )
            flash("Заявка успешно отправлена!", "success")

        except (ValueError, KeyError) as error:
            flash(str(error), "danger")

        return redirect(url_for("users.requests_page"))

    if role == "hr":
        requests_list = VacationRequest.query.all()

    elif role == "manager":
        requests_list = (
            VacationRequest.query
            .join(Employee, VacationRequest.employee_id == Employee.id)
            .filter(Employee.manager_id == employee.id)
            .all()
            if employee else []
        )

    elif role == "employee":
        requests_list = (
            VacationRequest.query
            .filter_by(employee_id=employee.id)
            .all()
            if employee else []
        )

    else:
        abort(403)

    available_days = (
        VacationService.get_available_days(employee.id)
        if role == "employee" and employee else None
    )

    return render_template(
        "account/requests.html",
        user=user,
        employee=employee,
        requests=sorted(requests_list, key=lambda item: item.id, reverse=True),
        csrf_token=csrf,
        available_days=available_days
    )


@account_bp.route(
    "/requests/<int:request_id>/<action>",
    methods=["POST"]
)
@role_required("manager", "hr")
def review_vacation_request(request_id, action):
    if action not in ("approve", "reject"):
        abort(404)

    token = session.get("requests_csrf")
    if not token or not compare_digest(token, request.form.get("csrf_token", "")):
        abort(400)
    user = g.current_user
    reviewer = user.employee
    vacation = db.get_or_404(VacationRequest, request_id)

    if not can_manage_employee(vacation.employee):
        abort(403)

    if vacation.status != "pending":
        flash("Заявка уже рассмотрена.", "warning")
        return redirect(url_for("users.requests_page"))

    vacation.status = (
        "approved" if action == "approve" else "rejected"
    )

    vacation.reviewed_by_id = reviewer.id if reviewer else None
    vacation.reviewed_at = datetime.now(timezone.utc)

    db.session.commit()

    flash("Статус заявки обновлён.", "success")
    return redirect(url_for("users.requests_page"))

@account_bp.route("/courses")
@login_required
def courses_page():
    return redirect(url_for("academy_pages.catalog"))


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
