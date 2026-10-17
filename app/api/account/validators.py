
def validate_login_form(username: str | None, password: str | None):
    errors = {}

    if not username or not username.strip():
        errors["username"] = "Введите логин."
    elif len(username.strip()) > 100:
        errors["username"] = "Логин слишком длинный."

    if not password:
        errors["password"] = "Введите пароль."
    elif len(password) > 128:
        errors["password"] = "Пароль слишком длинный."

    if errors:
        return None, errors

    return {
        "username": username.strip(),
        "password": password,
    }, {}


def validate_register_form(username: str | None, password: str | None):
    errors = {}

    if not username or not username.strip():
        errors["username"] = "Введите логин."
    elif len(username.strip()) > 100:
        errors["username"] = "Логин не должен превышать 100 символов."

    if not password:
        errors["password"] = "Введите пароль."
    elif len(password) < 8:
        errors["password"] = "Пароль должен содержать минимум 8 символов."
    elif len(password) > 128:
        errors["password"] = "Пароль слишком длинный."

    if errors:
        return None, errors

    return {
        "username": username.strip(),
        "password": password,
    }, {}
