from datetime import date

from flask import Blueprint, abort, flash, g, redirect, render_template, request, url_for

from app.api.account.service import AccountService
from app.core.permissions import can_manage_employee, login_required, role_required
from app.extensions import db
from app.models import Department, Employee, Position, Role, User


admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


def _manager_profiles():
    return (
        Employee.query.join(User, Employee.id == User.employee_id)
        .join(Role, User.role_id == Role.id)
        .filter(Role.name == "manager")
        .order_by(Employee.last_name, Employee.first_name)
        .all()
    )


@admin_bp.route("/employees")
@login_required
@role_required("hr")
def employees():
    users = (
        User.query.join(Role, User.role_id == Role.id)
        .filter(
            Role.name.in_(["employee", "manager"]),
            User.is_active.is_(True),
        )
        .order_by(User.id.asc())
        .all()
    )
    return render_template("admin/index.html", employees=users)


@admin_bp.route("/employees/create", methods=["GET", "POST"])
@login_required
@role_required("hr")
def create_employee():
    departments = Department.query.order_by(Department.name).all()
    positions = Position.query.order_by(Position.name).all()
    managers = _manager_profiles()
    if request.method == "POST":
        try:
            hire_date = date.fromisoformat(request.form.get("hire_date", ""))
            manager_id = request.form.get("manager_id", type=int) or None
            if manager_id is not None and manager_id not in {item.id for item in managers}:
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
                role_name=request.form.get("role", "employee").lower(),
                manager_id=manager_id,
            )
            flash("Сотрудник, карточка и учётная запись созданы.", "success")
            return redirect(url_for("admin.employees"))
        except (ValueError, TypeError) as error:
            db.session.rollback()
            flash(str(error) or "Проверьте дату приёма.", "danger")
        except Exception:
            db.session.rollback()
            flash("Не удалось создать сотрудника. Проверьте введённые данные.", "danger")
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
    departments = Department.query.order_by(Department.name).all()
    positions = Position.query.order_by(Position.name).all()
    if request.method == "POST":
        try:
            employee = Employee(
                first_name=request.form.get("first_name", "").strip(),
                last_name=request.form.get("last_name", "").strip(),
                email=request.form.get("email", "").strip().lower(),
                hire_date=date.fromisoformat(request.form.get("hire_date", "")),
                department_id=request.form.get("department_id", type=int),
                position_id=request.form.get("position_id", type=int),
            )
            if not all((employee.first_name, employee.last_name, employee.email,
                        employee.department_id, employee.position_id)):
                raise ValueError("Заполните все обязательные поля.")
            db.session.add(employee)
            db.session.commit()
            flash("Карточка создана. Теперь привяжите её к учётной записи.", "success")
            return redirect(url_for("admin.link_employee_account"))
        except (ValueError, TypeError) as error:
            db.session.rollback()
            flash(str(error) or "Проверьте дату приёма.", "danger")
        except Exception:
            db.session.rollback()
            flash("Не удалось создать карточку сотрудника.", "danger")
    return render_template("admin/employees/card_create.html", departments=departments, positions=positions)


@admin_bp.route("/employees/link", methods=["GET", "POST"])
@login_required
@role_required("hr")
def link_employee_account():
    if request.method == "POST":
        user = db.session.get(User, request.form.get("user_id", type=int))
        employee = db.session.get(Employee, request.form.get("employee_id", type=int))
        manager_id = request.form.get("manager_id", type=int) or None
        manager = db.session.get(Employee, manager_id) if manager_id else None
        manager_ids = {item.id for item in _manager_profiles()}
        if user is None or employee is None:
            flash("Выберите существующие учётную запись и карточку.", "danger")
        elif user.employee not in (None, employee) or employee.user not in (None, user):
            flash("Эта учётная запись или карточка уже связана.", "danger")
        elif manager_id == employee.id:
            flash("Сотрудник не может быть руководителем самому себе.", "danger")
        elif manager_id is not None and manager_id not in manager_ids:
            flash("Выберите руководителя с привязанной учётной записью.", "danger")
        else:
            employee.user = user
            employee.manager = manager
            db.session.commit()
            flash("Учётная запись связана с карточкой.", "success")
            return redirect(url_for("admin.link_employee_account"))
    users = User.query.order_by(User.username).all()
    employees = Employee.query.order_by(Employee.last_name, Employee.first_name).all()
    return render_template(
        "admin/employees/link.html", users=users, employees=employees,
        managers=_manager_profiles(),
    )


@admin_bp.route("/employees/edit/<int:employee_id>", methods=["GET", "POST"])
@login_required
@role_required("hr", "manager")
def edit_employee(employee_id):
    user = db.session.get(User, employee_id)
    if user is None or user.employee is None:
        abort(404)
    employee = user.employee
    is_manager = g.current_user.role.name == "manager"
    if is_manager and not can_manage_employee(employee):
        abort(403)
    departments = Department.query.order_by(Department.name).all()
    positions = Position.query.order_by(Position.name).all()
    if request.method == "POST":
        try:
            employee.first_name = request.form.get("first_name", "").strip()
            employee.last_name = request.form.get("last_name", "").strip()
            employee.email = request.form.get("email", "").strip().lower()
            employee.department_id = request.form.get("department_id", type=int)
            employee.position_id = request.form.get("position_id", type=int)
            if not all((employee.first_name, employee.last_name, employee.email,
                        employee.department_id, employee.position_id)):
                raise ValueError("Заполните все обязательные поля.")
            duplicate = Employee.query.filter(
                Employee.email == employee.email, Employee.id != employee.id
            ).first()
            if duplicate:
                raise ValueError("У сотрудника с таким email уже есть карточка.")
            if not is_manager:
                username = request.form.get("username", "").strip()
                duplicate_user = User.query.filter(
                    User.username == username, User.id != user.id
                ).first()
                if not username:
                    raise ValueError("Введите имя пользователя.")
                if duplicate_user:
                    raise ValueError("Такой логин уже используется.")
                user.username = username
                user.is_active = request.form.get("is_active") == "1"
                role_name = request.form.get("role", user.role.name)
                if role_name not in ("employee", "manager"):
                    raise ValueError("Разрешены роли сотрудника и руководителя.")
                role = Role.query.filter_by(name=role_name).first()
                if role is None:
                    raise ValueError("Выбранная роль не найдена.")
                user.role = role
            db.session.commit()
            flash("Данные сотрудника сохранены.", "success")
            return redirect(url_for("users.team_page" if is_manager else "admin.employees"))
        except ValueError as error:
            db.session.rollback()
            flash(str(error), "danger")
            user = db.session.get(User, employee_id)
            employee = user.employee if user else None
    template = "account/team_edit.html" if is_manager else "admin/employees/edit.html"
    return render_template(
        template, user=user, employee=employee,
        departments=departments, positions=positions,
    )


@admin_bp.route("/employees/delete/<int:employee_id>", methods=["POST"])
@login_required
@role_required("hr")
def delete_employee(employee_id):
    user = db.session.get(User, employee_id)
    if user is None:
        abort(404)
    user.is_active = False
    db.session.commit()
    flash("Учётная запись сотрудника отключена.", "success")
    return redirect(url_for("admin.employees"))
