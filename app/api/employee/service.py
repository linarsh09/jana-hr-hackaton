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
            "position": employee.position,
            "company": employee.company,
            "salary": float(employee.salary) if employee.salary else None,
            "hire_date": employee.hire_date.isoformat(),
            "vacation_days": employee.vacation_days,
            "available_vacation_days": VacationService.get_available_days(employee.id),
            "manager": employee.manager.full_name if employee.manager else None,
            "department": {
                "id": employee.department.id,
                "name": employee.department.name,
            },
        }

    # ДОБАВЛЕНО: создание сотрудника
    @staticmethod
    def create_employee(
        username: str,
        password: str,
        role_value: str,
        is_active: bool = True,
    ) -> User:

        username = username.strip()

        if not username:
            raise ValueError("Введите имя пользователя.")

        if len(username) > 100:
            raise ValueError(
                "Имя пользователя не должно превышать 100 символов."
            )

        if len(password) < 8:
            raise ValueError("Пароль должен содержать минимум 8 символов.")

        if EmployeeRepository.get_by_username(username) is not None:
            raise ValueError("Пользователь с таким именем уже существует.")

        try:
            role = Role(str.lower(role_value))
        except (ValueError, TypeError):
            raise ValueError("Некорректная роль пользователя.")

        if role not in ("employee", "manager"):
            raise ValueError("Здесь можно создать только работника или руководителя.")

        password_hash = generate_password_hash(password)

        return EmployeeRepository.create(
            username=username,
            password_hash=password_hash,
            role=role,
            is_active=is_active,
        )
