
from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    abort,
    g,
)

from app.extensions import db
from app.models import User, Employee, Department, Position, Role
from app.api.admin.service import AdminService
from app.core.permissions import (
    can_manage_employee,
    login_required,
    role_required,
)
from datetime import date

from app.api.account.service import AccountService
admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


@admin_bp.route("/employees")
@login_required
@role_required("hr")
def employees():
    users = AdminService.get_all_employees()
    return render_template("admin/index.html", employees=users)



@admin_bp.route("/employees/create", methods=["GET", "POST"])
@login_required
@role_required("hr")
def create_employee():
    departments, positions, _ = AdminService.get_form_data()

    managers = [
        employee
        for employee in Employee.query.all()
        if (
            employee.user
            and employee.user.role
            and employee.user.role.name.lower() == "manager"
        )
    ]

    if request.method == "POST":
        try:
            hire_date_value = request.form.get("hire_date", "")
            try:
                hire_date = date.fromisoformat(hire_date_value)
            except (ValueError, TypeError):
                raise ValueError("Укажите корректную дату приёма.")

            manager_id = request.form.get("manager_id", type=int) or None

            if manager_id is not None and manager_id not in {
                manager.id for manager in managers
            }:
                raise ValueError("Выберите существующего руководителя.")

            AccountService.create_employee(
                username=request.form.get("username", ""),
                password=request.form.get("password", ""),
                first_name=request.form.get("first_name", ""),
                last_name=request.form.get("last_name", ""),
                email=request.form.get("email", ""),
                hire_date=hire_date,
                department_id=request.form.get("department_id", type=int),
                position_id=request.form.get("position_id", type=int),
                role_name=request.form.get("role", "employee"),
                manager_id=manager_id,
            )

            flash(
                "Сотрудник, карточка и учётная запись созданы.",
                "success",
            )
            return redirect(url_for("admin.employees"))

        except ValueError as error:
            db.session.rollback()
            flash(str(error), "danger")

        except Exception:
            db.session.rollback()
            flash("Не удалось создать сотрудника.", "danger")

    return render_template(
        "admin/employees/create.html",
        departments=departments,
        positions=positions,
        managers=managers,
    )

@admin_bp.route("/employees/card/create", methods=["GET", "POST"])
@login_required
@role_required("hr")
def create_employee_card():
    departments, positions, _ = AdminService.get_form_data()

    if request.method == "POST":
        try:
            AdminService.create_employee_card(request.form)

            flash(
                "Карточка создана. Теперь привяжите её к учётной записи.",
                "success",
            )
            return redirect(url_for("admin.link_employee_account"))

        except ValueError as error:
            db.session.rollback()
            flash(str(error), "danger")

        except Exception:
            db.session.rollback()
            flash("Не удалось создать карточку сотрудника.", "danger")

    return render_template(
        "admin/employees/card_create.html",
        departments=departments,
        positions=positions,
    )


@admin_bp.route("/employees/link", methods=["GET", "POST"])
@login_required
@role_required("hr")
def link_employee_account():
    if request.method == "POST":
        try:
            user_id = request.form.get("user_id", type=int)
            employee_id = request.form.get("employee_id", type=int)
            manager_id = request.form.get("manager_id", type=int) or None

            if user_id is None or employee_id is None:
                raise ValueError(
                    "Выберите учётную запись и кадровую карточку."
                )

            AdminService.link_employee_account(
                user_id=user_id,
                employee_id=employee_id,
                manager_id=manager_id,
            )

            flash("Учётная запись связана с карточкой.", "success")
            return redirect(url_for("admin.link_employee_account"))

        except ValueError as error:
            db.session.rollback()
            flash(str(error), "danger")

        except Exception:
            db.session.rollback()
            flash(
                "Не удалось связать учётную запись с карточкой.",
                "danger",
            )

    users = User.query.order_by(User.username).all()
    employees_list = Employee.query.order_by(
        Employee.last_name,
        Employee.first_name,
    ).all()

    managers = [
        employee
        for employee in employees_list
        if (
            employee.user
            and employee.user.role
            and employee.user.role.name.lower() == "manager"
        )
    ]

    return render_template(
        "admin/employees/link.html",
        users=users,
        employees=employees_list,
        managers=managers,
    )


@admin_bp.route(
    "/employees/edit/<int:employee_id>",
    methods=["GET", "POST"],
)
@login_required
@role_required("hr", "manager")
def edit_employee(employee_id):
    # Здесь employee_id — ID кадровой карточки Employee.
    employee = db.session.get(Employee, employee_id)

    if employee is None or employee.user is None:
        abort(404)

    user = employee.user
    current_role = (
        g.current_user.role.name.lower()
        if g.current_user.role
        else ""
    )
    is_manager = current_role == "manager"

    if is_manager and not can_manage_employee(employee):
        abort(403)

    departments, positions, _ = AdminService.get_form_data()

    if request.method == "POST":
        try:
            first_name = request.form.get("first_name", "").strip()
            last_name = request.form.get("last_name", "").strip()
            email = request.form.get("email", "").strip().lower()
            department_id = request.form.get("department_id", type=int)
            position_id = request.form.get("position_id", type=int)

            if not all((
                first_name,
                last_name,
                email,
                department_id,
                position_id,
            )):
                raise ValueError("Заполните все обязательные поля.")

            if db.session.get(Department, department_id) is None:
                raise ValueError("Выбранное подразделение не найдено.")

            if db.session.get(Position, position_id) is None:
                raise ValueError("Выбранная должность не найдена.")

            duplicate_email = Employee.query.filter(
                Employee.email == email,
                Employee.id != employee.id,
            ).first()

            if duplicate_email:
                raise ValueError(
                    "У сотрудника с таким email уже есть карточка."
                )

            employee.first_name = first_name
            employee.last_name = last_name
            employee.email = email
            employee.department_id = department_id
            employee.position_id = position_id

            # Руководитель не может изменять настройки учётной записи.
            if not is_manager:
                username = request.form.get("username", "").strip()

                if not username:
                    raise ValueError("Введите имя пользователя.")

                duplicate_user = User.query.filter(
                    User.username == username,
                    User.id != user.id,
                ).first()

                if duplicate_user:
                    raise ValueError("Такой логин уже используется.")

                user.username = username
                user.is_active = request.form.get("is_active") == "1"

                role_name = request.form.get(
                    "role",
                    user.role.name if user.role else "employee",
                ).strip().lower()

                if role_name not in ("employee", "manager"):
                    raise ValueError(
                        "Разрешены роли сотрудника и руководителя."
                    )

                role = Role.query.filter_by(name=role_name).first()

                if role is None:
                    raise ValueError("Выбранная роль не найдена.")

                user.role = role

            db.session.commit()
            flash("Данные сотрудника сохранены.", "success")

            if is_manager:
                return redirect(url_for("users.team_page"))

            return redirect(url_for("admin.employees"))

        except ValueError as error:
            db.session.rollback()
            flash(str(error), "danger")

        except Exception:
            db.session.rollback()
            flash("Не удалось сохранить данные сотрудника.", "danger")

        employee = db.session.get(Employee, employee_id)

        if employee is None or employee.user is None:
            abort(404)

        user = employee.user

    template = (
        "account/team_edit.html"
        if is_manager
        else "admin/employees/edit.html"
    )

    return render_template(
        template,
        user=user,
        employee=employee,
        departments=departments,
        positions=positions,
    )


@admin_bp.route(
    "/employees/delete/<int:employee_id>",
    methods=["POST"],
)
@login_required
@role_required("hr")
def delete_employee(employee_id):
    try:
        deactivated = AdminService.deactivate_employee(employee_id)

        if not deactivated:
            abort(404)

        flash("Учётная запись сотрудника отключена.", "success")

    except Exception:
        db.session.rollback()
        flash("Не удалось отключить учётную запись.", "danger")

    return redirect(url_for("admin.employees"))
