from flask import Blueprint, render_template, request, session, redirect, url_for, flash
from app.models import UserRole
from app.api.employees.service import EmployeeService
from app.core.permissions import login_required, role_required


admin_bp = Blueprint(
    "admin",
    __name__,
    url_prefix="/admin",
)

@admin_bp.route("/employees")
@login_required
@role_required(UserRole.ADMIN)
def employees():
    employees = EmployeeService.get_all_employees()

    return render_template(
        "admin/index.html",
        employees=employees
    )

@admin_bp.route("/employees/create", methods=["GET", "POST"])
@login_required
@role_required(UserRole.ADMIN)
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


@admin_bp.route("/employees/edit/<int:employee_id>", methods=["GET", "PUT"])
@login_required
@role_required(UserRole.ADMIN)
def edit_employee():
    ...


@admin_bp.route("/employees/delete/<int:employee_id>", methods=["DELETE"])
@login_required
@role_required(UserRole.ADMIN)
def delete_employee():
    ...
