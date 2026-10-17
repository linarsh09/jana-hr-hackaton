
from datetime import date

from werkzeug.security import generate_password_hash
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.models import User, Role, Employee, Department, Position
from app.api.account.repository import AccountRepository


class AccountService:
    @staticmethod
    def verify_password(user: User, password: str) -> bool:
        return AccountRepository.verify_password(user, password)

    @staticmethod
    def change_password(user: User, password: str) -> None:
        if len(password) < 8:
            raise ValueError("Пароль слишком короткий")

        user.password_hash = generate_password_hash(password)
        db.session.commit()

    @staticmethod
    def login_user(username: str, password: str) -> User | None:
        user = AccountRepository.get_by_username(username)

        if user is None or not user.is_active:
            return None

        if not AccountRepository.verify_password(user, password):
            return None

        return user

    @staticmethod
    def register_user(
        username: str,
        password: str,
        role_id: int
    ) -> User | None:
        if len(password) < 8:
            raise ValueError("Пароль должен содержать минимум 8 символов")

        if AccountRepository.get_by_username(username):
            return None

        return AccountRepository.create(
            username=username,
            password_hash=generate_password_hash(password),
            role_id=role_id
        )

    
    @staticmethod
    def create_employee(
        *,
        username: str,
        password: str,
        first_name: str,
        last_name: str,
        email: str,
        hire_date: date,
        department_id: int,
        position_id: int,
        role_name: str = "employee",
        manager_id: int | None = None,
    ) -> User:
        username = username.strip()
        first_name = first_name.strip()
        last_name = last_name.strip()
        email = email.strip().lower()
        role_name = role_name.strip().lower()

        if not all((username, first_name, last_name, email)):
            raise ValueError("Заполните обязательные поля.")

        if len(username) > 100:
            raise ValueError("Логин не должен превышать 100 символов.")

        if len(password) < 8:
            raise ValueError(
                "Пароль должен содержать минимум 8 символов."
            )

        if role_name not in ("employee", "manager"):
            raise ValueError("Недопустимая роль.")

        if not isinstance(hire_date, date):
            raise ValueError("Укажите корректную дату приёма.")

        role = Role.query.filter_by(name=role_name).first()
        if role is None:
            raise ValueError("Роль не найдена.")

        if db.session.get(Department, department_id) is None:
            raise ValueError("Подразделение не найдено.")

        if db.session.get(Position, position_id) is None:
            raise ValueError("Должность не найдена.")

        if AccountRepository.get_by_username(username):
            raise ValueError("Такой логин уже существует.")

        if Employee.query.filter_by(email=email).first():
            raise ValueError("Такой email уже существует.")

        manager = None
        if manager_id is not None:
            manager = db.session.get(Employee, manager_id)

            if manager is None:
                raise ValueError("Руководитель не найден.")

            if (
                manager.user is None
                or manager.user.role is None
                or manager.user.role.name.lower() != "manager"
            ):
                raise ValueError(
                    "Выбранный сотрудник не является руководителем."
                )

        employee = Employee(
            first_name=first_name,
            last_name=last_name,
            email=email,
            hire_date=hire_date,
            department_id=department_id,
            position_id=position_id,
            manager_id=manager_id,
            vacation_balance=0,
        )

        user = User(
            username=username,
            password_hash=generate_password_hash(password),
            role_id=role.id,
            employee=employee,
            is_active=True,
        )

        try:
            db.session.add(user)
            db.session.commit()
            return user

        except IntegrityError as error:
            db.session.rollback()
            raise ValueError(
                "Пользователь с таким логином или email уже существует."
            ) from error

        except Exception:
            db.session.rollback()
            raise
