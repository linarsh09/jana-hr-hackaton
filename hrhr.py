
from getpass import getpass

from werkzeug.security import generate_password_hash

from app import create_app
from app.extensions import db
from app.models import User, Role


app = create_app()

with app.app_context():
    hr_role = Role.query.filter_by(name="hr").first()

    if hr_role is None:
        print("Ошибка: роль hr не найдена в базе данных.")

    else:
        username = input("Введите логин HR: ").strip()

        existing_user = User.query.filter_by(
            username=username
        ).first()

        if not username:
            print("Ошибка: логин не может быть пустым.")

        elif existing_user:
            print("Ошибка: пользователь уже существует.")

        else:
            password = getpass("Введите пароль HR: ")

            if len(password) < 8:
                print("Пароль должен содержать минимум 8 символов.")

            else:
                hr_user = User(
                    username=username,
                    password_hash=generate_password_hash(password),
                    role_id=hr_role.id,
                    is_active=True
                )

                try:
                    db.session.add(hr_user)
                    db.session.commit()
                    print("HR успешно создан!")
                except Exception as error:
                    db.session.rollback()
                    print("Ошибка при создании HR:", error)
