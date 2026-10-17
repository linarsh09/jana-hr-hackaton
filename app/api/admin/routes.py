from datetime import date

from flask import Blueprint, render_template, request, session, redirect, url_for, flash
from app.models import UserRole, Employee, User, Department
from app.extensions import db
from app.api.employee.service import EmployeeService
from app.core.permissions import login_required, role_required


admin_bp = Blueprint(
    "admin",
    __name__,
    url_prefix="/admin",
)

POSITION_OPTIONS = (
    ("Руководитель подразделения", "Руководитель подразделения"),
    ("HR-специалист", "HR-специалист"),
    ("Backend-разработчик", "Backend-разработчик"),
    ("Frontend-разработчик", "Frontend-разработчик"),
    ("QA-инженер", "QA-инженер"),
    ("Финансовый аналитик", "Финансовый аналитик"),
    ("Маркетолог", "Маркетолог"),
    ("Менеджер по продажам", "Менеджер по продажам"),
)

@admin_bp.route("/employees")
@login_required
@role_required(UserRole.ADMIN, UserRole.HR)
def employees():
    employees = EmployeeService.get_all_employees()

    return render_template(
        "admin/index.html",
        employees=employees
    )

@admin_bp.route("/employees/create", methods=["GET", "POST"])
@login_required
@role_required(UserRole.ADMIN, UserRole.HR)
def create_employee():

    if request.method == "POST":
        username = request.form.get("username", "")
        password = request.form.get("password", "")
        role = request.form.get("role", "EMPLOYEE")
        is_active = request.form.get("is_active") == "1"

        try:
            EmployeeService.create_employee(
                username=username,
                password=password,
                role_value=role,
                is_active=is_active,
            )

            flash("Сотрудник успешно добавлен.", "success")
            return redirect(url_for("admin.employees"))

        except ValueError as error:
            flash(str(error), "danger")

        except Exception:
            flash("Не удалось создать сотрудника.", "danger")

    return render_template("admin/employees/create.html")


@admin_bp.route("/employees/card/create", methods=["GET", "POST"])
@login_required
@role_required(UserRole.ADMIN, UserRole.HR)
def create_employee_card():
    departments = Department.query.order_by(Department.name).all()
    if request.method == "POST":
        first_name = request.form.get("first_name", "").strip()
        last_name = request.form.get("last_name", "").strip()
        email = request.form.get("email", "").strip().lower()
        position_choice = request.form.get("position", "").strip()
        other_position = request.form.get("other_position", "").strip()
        position = other_position if position_choice == "other" else position_choice
        company = request.form.get("company", "").strip() or None
        department_id = request.form.get("department_id", type=int)
        hire_date_value = request.form.get("hire_date", "").strip()

        try:
            if not all((first_name, last_name, email, position, department_id, hire_date_value)):
                raise ValueError("Заполните все обязательные поля.")
            if position_choice != "other" and position_choice not in dict(POSITION_OPTIONS):
                raise ValueError("Выберите должность из списка.")
            if position_choice == "other" and len(position) > 150:
                raise ValueError("Название должности не должно превышать 150 символов.")
            if Employee.query.filter_by(email=email).first() is not None:
                raise ValueError("Карточка с таким email уже существует.")
            department = db.session.get(Department, department_id)
            if department is None:
                raise ValueError("Выберите существующее подразделение.")
            hire_date = date.fromisoformat(hire_date_value)

            employee = Employee(
                first_name=first_name,
                last_name=last_name,
                email=email,
                position=position,
                company=company,
                department=department,
                hire_date=hire_date,
            )
            db.session.add(employee)
            db.session.commit()
            flash("Карточка сотрудника создана. Теперь свяжите её с учётной записью.", "success")
            return redirect(url_for("admin.link_employee_account"))
        except ValueError as error:
            db.session.rollback()
            flash(str(error), "danger")

    return render_template(
        "admin/employees/card_create.html",
        departments=departments,
        position_options=POSITION_OPTIONS,
    )


@admin_bp.route("/employees/link", methods=["GET", "POST"])
@login_required
@role_required(UserRole.ADMIN, UserRole.HR)
def link_employee_account():
    if request.method == "POST":
        user = db.session.get(User, request.form.get("user_id", type=int))
        employee = db.session.get(Employee, request.form.get("employee_id", type=int))
        manager_id = request.form.get("manager_id", type=int) or None
        manager = db.session.get(Employee, manager_id) if manager_id else None

        if user is None or employee is None:
            flash("Выберите существующие учётную запись и карточку сотрудника.", "danger")
        elif employee.user_id not in (None, user.id) or (user.employee and user.employee.id != employee.id):
            flash("Эта учётная запись или карточка уже связана с другой записью.", "danger")
        elif manager_id == employee.id:
            flash("Сотрудник не может быть руководителем самому себе.", "danger")
        elif manager and manager.manager_id == employee.id:
            flash("Нельзя назначить подчинённого руководителем его руководителя.", "danger")
        elif manager and (manager.user is None or manager.user.role != UserRole.MANAGER):
            flash("У выбранного руководителя должна быть связанная учётная запись с ролью руководителя.", "danger")
        else:
            employee.user = user
            employee.manager = manager
            db.session.commit()
            flash("Связь учётной записи и кадровой карточки сохранена.", "success")
            return redirect(url_for("admin.link_employee_account"))

    users = User.query.order_by(User.username).all()
    employees = Employee.query.order_by(Employee.last_name, Employee.first_name).all()
    return render_template(
        "admin/employees/link.html",
        users=users,
        employees=employees,
        managers=[employee for employee in employees if employee.user and employee.user.role == UserRole.MANAGER],
    )


@admin_bp.route("/employees/edit/<int:employee_id>", methods=["GET", "PUT"])
@login_required
@role_required(UserRole.ADMIN, UserRole.HR)
def edit_employee():
    ...


@admin_bp.route("/employees/delete/<int:employee_id>", methods=["DELETE"])
@login_required
@role_required(UserRole.ADMIN, UserRole.HR)
def delete_employee():
    ...
