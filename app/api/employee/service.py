
from werkzeug.security import generate_password_hash

from app.api.employee.repository import EmployeeRepository
from app.api.vacations.service import VacationService
from app.models import User, Role


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
            "hire_date": (
                employee.hire_date.isoformat()
                if employee.hire_date else None
            ),
            "vacation_balance": employee.vacation_balance,
            "manager": employee.manager.full_name if employee.manager else None,
            "department": {
                "id": employee.department.id,
                "name": employee.department.name,
            } if employee.department else None,
        }

    @staticmethod
    def create_employee(
        username: str,
        password: str,
        role_value: str,
        is_active: bool = True,
    ) -> User:

        username = username.strip()
        role_value = role_value.strip().lower()

        if not username:
            raise ValueError("Введите имя пользователя.")

        if len(username) > 100:
            raise ValueError(
                "Имя пользователя не должно превышать 100 символов."
            )

        if len(password) < 8:
            raise ValueError(
                "Пароль должен содержать минимум 8 символов."
            )

        if EmployeeRepository.get_by_username(username) is not None:
            raise ValueError(
                "Пользователь с таким именем уже существует."
            )

        if role_value not in ("employee", "manager"):
            raise ValueError(
                "Можно создать только сотрудника или руководителя."
            )

        role = Role.query.filter_by(name=role_value).first()

        if role is None:
            raise ValueError("Указанная роль отсутствует в базе данных.")

        password_hash = generate_password_hash(password)

        return EmployeeRepository.create(
            username=username,
            password_hash=password_hash,
            role=role,
            is_active=is_active,
        )
