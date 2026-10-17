from flask import Blueprint, jsonify
from app.models import Employee
from app.api.employees.service import EmployeeService


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
              department:
                type: string
    """
    employees = Employee.query.all()

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
    employee = EmployeeService.get_employee(employee_id)

    if employee is None:
        return jsonify({
            "error": "Employee not found"
        }), 404

    return jsonify(employee), 200
