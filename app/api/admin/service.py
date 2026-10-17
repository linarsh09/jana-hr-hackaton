from werkzeug.security import generate_password_hash

from app.api.employee.repository import EmployeeRepository
from app.models import User


class EmployeeService:
    @staticmethod
    def get_all_employees() -> list[User]:
        return EmployeeRepository.get_all()
