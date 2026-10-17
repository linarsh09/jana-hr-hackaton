
from datetime import date

from werkzeug.security import generate_password_hash
from app.extensions import db
from app.models import Role, Employee, User, Department, Position
from app.api.employee.service import EmployeeService


class AdminService:
    
    @staticmethod
    def create_employee_account(
        username: str,
        password: str,
        role_name: str = "employee",
    ):
        return EmployeeService.create_employee(
            username=username,
            password=password,
            role_value=role_name,
            is_active=True,
        )

    @staticmethod
    def get_all_employees():
        return (
            User.query
            .join(Role, User.role_id == Role.id)
            .filter(
                Role.name.in_(["employee", "manager"]),
                User.is_active.is_(True),
            )
            .order_by(User.id.asc())
            .all()
        )

    @staticmethod
    def get_form_data():
        departments = Department.query.order_by(Department.name).all()
        positions = Position.query.order_by(Position.name).all()

        managers = (
            Employee.query
            .join(User, Employee.id == User.employee_id)
            .join(Role, User.role_id == Role.id)
            .filter(Role.name == "manager")
            .order_by(Employee.last_name, Employee.first_name)
            .all()
        )

        return departments, positions, managers

    @staticmethod
    def create_employee_card(data):
        first_name = data.get("first_name", "").strip()
        last_name = data.get("last_name", "").strip()
        email = data.get("email", "").strip().lower()

        try:
            hire_date = date.fromisoformat(data.get("hire_date", ""))
        except (ValueError, TypeError):
            raise ValueError("Укажите корректную дату приёма.")

        department_id = data.get("department_id", type=int)
        position_id = data.get("position_id", type=int)

        if not all((
            first_name,
            last_name,
            email,
            department_id,
            position_id,
        )):
            raise ValueError("Заполните все обязательные поля.")

        if not Department.query.get(department_id):
            raise ValueError("Выберите существующее подразделение.")

        if not Position.query.get(position_id):
            raise ValueError("Выберите существующую должность.")

        if Employee.query.filter_by(email=email).first():
            raise ValueError("Карточка с таким email уже существует.")

        employee = Employee(
            first_name=first_name,
            last_name=last_name,
            email=email,
            hire_date=hire_date,
            department_id=department_id,
            position_id=position_id,
        )

        try:
            db.session.add(employee)
            db.session.commit()
            return employee
        except Exception:
            db.session.rollback()
            raise

    @staticmethod
    def link_employee_account(user_id, employee_id, manager_id=None):
        user = db.session.get(User, user_id)
        employee = db.session.get(Employee, employee_id)
        manager = (
            db.session.get(Employee, manager_id)
            if manager_id else None
        )

        if user is None or employee is None:
            raise ValueError(
                "Выберите существующую учётную запись и карточку."
            )

        if user.employee not in (None, employee):
            raise ValueError("Учётная запись уже связана с другой карточкой.")

        if employee.user not in (None, user):
            raise ValueError("Карточка уже связана с другой учётной записью.")

        if manager_id == employee.id:
            raise ValueError(
                "Сотрудник не может быть руководителем самому себе."
            )

        if manager and manager.manager_id == employee.id:
            raise ValueError(
                "Нельзя назначить подчинённого руководителем его руководителя."
            )

        if manager and (
            manager.user is None
            or manager.user.role != "manager"
        ):
            raise ValueError(
                "У руководителя должна быть учётная запись "
                "с ролью руководителя."
            )

        try:
            employee.user = user
            employee.manager = manager
            db.session.commit()
        except Exception:
            db.session.rollback()
            raise

    @staticmethod
    def get_employee_for_edit(user_id):
        user = db.session.get(User, user_id)

        if user is None or user.employee is None:
            return None, None

        return user, user.employee

    @staticmethod
    def update_employee(user, employee, data, is_manager=False):
        employee.first_name = data.get("first_name", "").strip()
        employee.last_name = data.get("last_name", "").strip()
        employee.email = data.get("email", "").strip().lower()
        employee.department_id = data.get("department_id", type=int)
        employee.position_id = data.get("position_id", type=int)

        if not all((
            employee.first_name,
            employee.last_name,
            employee.email,
            employee.department_id,
            employee.position_id,
        )):
            raise ValueError("Заполните все обязательные поля.")

        if not Department.query.get(employee.department_id):
            raise ValueError("Выберите существующее подразделение.")

        if not Position.query.get(employee.position_id):
            raise ValueError("Выберите существующую должность.")

        duplicate_email = Employee.query.filter(
            Employee.email == employee.email,
            Employee.id != employee.id,
        ).first()

        if duplicate_email:
            raise ValueError("У сотрудника с таким email уже есть карточка.")

        if not is_manager:
            username = data.get("username", "").strip()

            if not username:
                raise ValueError("Введите имя пользователя.")

            duplicate_user = User.query.filter(
                User.username == username,
                User.id != user.id,
            ).first()

            if duplicate_user:
                raise ValueError("Такой логин уже используется.")

            role_name = data.get("role", user.role.name)

            if role_name not in ("employee", "manager"):
                raise ValueError(
                    "Разрешены роли сотрудника и руководителя."
                )

            role = Role.query.filter_by(name=role_name).first()

            if role is None:
                raise ValueError("Выбранная роль не найдена.")

            user.username = username
            user.is_active = data.get("is_active") == "1"
            user.role = role

        try:
            db.session.commit()
        except Exception:
            db.session.rollback()
            raise

    @staticmethod
    def deactivate_employee(user_id):
        user = db.session.get(User, user_id)

        if user is None:
            return False

        user.is_active = False

        try:
            db.session.commit()
        except Exception:
            db.session.rollback()
            raise

        return True
