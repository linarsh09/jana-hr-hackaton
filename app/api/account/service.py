from werkzeug.security import generate_password_hash

from app.api.account.repository import AccountRepository
from app.models import User


class AccountService:
    @staticmethod
    def login_user(username: str, password: str) -> User | None:
        user = AccountRepository.get_by_username(username)

        if user is None:
            return None

        if not AccountRepository.verify_password(user, password):
            return None

        return user
    
    @staticmethod
    def register_user(username: str, password: str) -> User | None:
        existing_user = AccountRepository.get_by_username(username)

        if existing_user is not None:
            return None

        password_hash = generate_password_hash(password)

        return AccountRepository.create(
            username=username,
            password_hash=password_hash,
        )
