from flask import Blueprint, render_template, request, session, redirect, url_for, flash, jsonify
from app.extensions import db
from app.models import Employee
from app.api.employees.service import EmployeeService
from app.core.permissions import login_required, role_required


admin_bp = Blueprint(
    "admin",
    __name__,
    url_prefix="/admin",
)

@admin_bp.route("/employees")
@login_required
@role_required("hr")
def employees():
    employees = EmployeeService.get_all_employees()

    return render_template(
        "admin/index.html",
        employees=employees
    )

@admin_bp.route("/employees/create", methods=["GET", "POST"])
@login_required
@role_required("hr")
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



@admin_bp.route(
    "/employees/edit/<int:employee_id>",
    methods=["GET", "PUT"],
)
@login_required
@role_required("hr")
def edit_employee(employee_id):
    employee = db.session.get(Employee, employee_id)

    if employee is None:
        return jsonify({"error": "Employee not found"}), 404

    # GET: вернуть текущие данные сотрудника
    if request.method == "GET":
        return jsonify({
            "id": employee.id,
            "first_name": employee.first_name,
            "last_name": employee.last_name,
            "department": employee.department,
            "position": employee.position,
            "manager_id": employee.manager_id,
        }), 200

    # PUT: обновить данные сотрудника
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({
            "error": "Request body must be a JSON object"
        }), 400

    allowed_fields = (
        "first_name",
        "last_name",
        "department",
        "position",
    )

    for field in allowed_fields:
        if field not in data:
            continue

        value = data[field]

        if field in ("first_name", "last_name"):
            if not isinstance(value, str) or not value.strip():
                return jsonify({
                    "error": f"{field} must be a non-empty string"
                }), 400

            value = value.strip()

        elif value is not None and not isinstance(value, str):
            return jsonify({
                "error": f"{field} must be a string or null"
            }), 400

        setattr(employee, field, value)

    if "manager_id" in data:
        manager_id = data["manager_id"]

        if manager_id is not None:
            # bool является подклассом int в Python,
            # поэтому проверяем его отдельно.
            if isinstance(manager_id, bool) or not isinstance(manager_id, int):
                return jsonify({
                    "error": "manager_id must be an integer or null"
                }), 400

            if manager_id == employee.id:
                return jsonify({
                    "error": "Employee cannot be their own manager"
                }), 400

            manager = db.session.get(Employee, manager_id)

            if manager is None:
                return jsonify({
                    "error": "Manager not found"
                }), 404

        employee.manager_id = manager_id

    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        return jsonify({
            "error": "Failed to update employee"
        }), 500

    return jsonify({
        "message": "Employee updated successfully",
        "employee": {
            "id": employee.id,
            "first_name": employee.first_name,
            "last_name": employee.last_name,
            "department": employee.department,
            "position": employee.position,
            "manager_id": employee.manager_id,
        },
    }), 200



@admin_bp.route(
    "/employees/delete/<int:employee_id>",
    methods=["DELETE"],
)


@login_required
@role_required("hr")
def delete_employee(employee_id):
    employee = db.session.get(Employee, employee_id)

    if employee is None:
        return jsonify({"error": "Employee not found"}), 404

    # Проверяем связанные записи
    if employee.user is not None:
        return jsonify({
            "error": "Cannot delete employee linked to a user account"
        }), 409

    if employee.vacation_requests:
        return jsonify({
            "error": "Cannot delete employee with vacation requests"
        }), 409

    if employee.subordinates:
        return jsonify({
            "error": "Cannot delete employee who has subordinates"
        }), 409

    try:
        db.session.delete(employee)
        db.session.commit()
    except Exception:
        db.session.rollback()
        return jsonify({
            "error": "Failed to delete employee"
        }), 500

    return jsonify({
        "message": "Employee deleted successfully",
        "id": employee_id,
    }), 200
