from app.api.employee.repository import EmployeeRepository
from app.models import User


class EmployeeService:

    @staticmethod
    def get_all_employees() -> list[User]:
        return EmployeeRepository.get_all()

    @staticmethod
    def get_employee(employee_id: int):
        employee = EmployeeRepository.get_by_id(employee_id)

        if employee is None:
            return None

        return {
            "id": employee.id,
            "first_name": employee.first_name,
            "last_name": employee.last_name,
            "full_name": employee.full_name,
            "email": employee.email,
            "position": employee.position.name if employee.position else None,
            "salary": float(employee.salary) if employee.salary else None,
            "hire_date": employee.hire_date.isoformat(),
            "vacation_balance": employee.vacation_balance,
            "manager": employee.manager.full_name if employee.manager else None,
            "department": {
                "id": employee.department.id,
                "name": employee.department.name,
            },
        }
