from functools import wraps
from flask import g, redirect, url_for, abort
from app.models import User, UserRole
from app.extensions import db


def load_current_user():
    """Загружает текущего пользователя для запроса."""
    from flask import session

    user_id = session.get("user_id")

    if user_id is None:
        g.current_user = None
        return

    user = db.session.get(User, user_id)

    if user is None or not user.is_active:
        session.clear()
        g.current_user = None
        return

    g.current_user = user


def login_required(view):
    """Требует авторизации."""
    @wraps(view)
    def wrapped(*args, **kwargs):
        user = getattr(g, "current_user", None)

        if user is None:
            return redirect(url_for("users.login"))

        return view(*args, **kwargs)

    return wrapped


def role_required(*allowed_roles: UserRole):
    """Требует авторизации и одну из указанных ролей."""
    @wraps(role_required)
    def decorator(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            user = getattr(g, "current_user", None)

            if user is None:
                return redirect(url_for("users.login"))

            if user.role not in allowed_roles:
                abort(403)

            return view(*args, **kwargs)

        return wrapped

    return decorator
