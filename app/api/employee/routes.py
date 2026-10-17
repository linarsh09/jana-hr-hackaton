from flask import Blueprint, jsonify, g
from app.models import Employee
from app.api.employee.service import EmployeeService
from app.core.permissions import can_access_employee, visible_employee_query


employees_bp = Blueprint(
    "employees",
    __name__,
    url_prefix="/api/v1/employees",
)


@employees_bp.get("")
def get_employees():
    """
    Получить список сотрудников
    ---
    tags:
      - Employees
    responses:
      200:
        description: Список сотрудников
        schema:
          type: array
          items:
            type: object
            properties:
              id:
                type: integer
              first_name:
                type: string
              last_name:
                type: string
              email:
                type: string
              position:
                type: string
              company:
                type: string
              department:
                type: string
    """
    if getattr(g, "current_user", None) is None:
        return jsonify({"error": "Authentication required"}), 401
    employees = visible_employee_query().order_by(Employee.id).all()

    return jsonify([
        {
            "id": employee.id,
            "first_name": employee.first_name,
            "last_name": employee.last_name,
            "email": employee.email,
            "position": employee.position,
            "department": employee.department.name,
        }
        for employee in employees
    ])

@employees_bp.get("/<int:employee_id>")
def get_employee(employee_id: int):
    if getattr(g, "current_user", None) is None:
        return jsonify({"error": "Authentication required"}), 401
    if not can_access_employee(employee_id):
        return jsonify({"error": "Forbidden"}), 403
    employee = EmployeeService.get_employee(employee_id)

    if employee is None:
        return jsonify({
            "error": "Employee not found"
        }), 404

    # Salary is HR-only data; it is deliberately omitted for employees and
    # managers even when the profile itself is within their permitted scope.
    if g.current_user.role.value != "hr":
        employee.pop("salary", None)

    return jsonify(employee), 200