from werkzeug.security import check_password_hash
from app.extensions import db
from app.models import User


class AccountRepository:

    @staticmethod
    def get_by_username(username: str) -> User | None:
        return User.query.filter_by(username=username).first()

    @staticmethod
    def create(username: str, password_hash: str) -> User:
        user = User(
            username=username,
            password_hash=password_hash,
        )

        db.session.add(user)
        db.session.commit()

        return user

    @staticmethod
    def verify_password(user: User, password: str) -> bool:
        return check_password_hash(user.password_hash, password)
