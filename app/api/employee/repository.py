from app.extensions import db
from app.models import Employee, User


class EmployeeRepository:
    @staticmethod
    def get_all() -> list[User]:
        return User.query.order_by(User.id.asc()).all()

    @staticmethod
    def get_by_id(user_id: int) -> Employee | None:
        return db.session.get(Employee, user_id)

    # ДОБАВЛЕНО: поиск по имени пользователя
    @staticmethod
    def get_by_username(username: str) -> User | None:
        return User.query.filter_by(username=username).first()

    # ДОБАВЛЕНО: создание пользователя
    @staticmethod
    def create(
        username: str,
        password_hash: str,
        role,
        is_active: bool = True,
    ) -> User:
        employee = User(
            username=username,
            password_hash=password_hash,
            role=role,
            is_active=is_active,
        )

        db.session.add(employee)
        db.session.commit()

        return employee
