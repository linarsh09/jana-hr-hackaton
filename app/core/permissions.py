
from functools import wraps

from flask import g, redirect, url_for, abort, session

from app.models import User
from app.extensions import db


def load_current_user():
    """Загружает текущего пользователя из сессии."""

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
    """Разрешает доступ только авторизованным пользователям."""

    @wraps(view)
    def wrapped(*args, **kwargs):

        user = getattr(g, "current_user", None)

        if user is None:
            return redirect(url_for("users.login"))

        return view(*args, **kwargs)

    return wrapped


def role_required(*allowed_roles: str):
    """Разрешает доступ пользователям с указанными ролями."""

    def decorator(view):

        @wraps(view)
        def wrapped(*args, **kwargs):

            user = getattr(g, "current_user", None)

            if user is None:
                return redirect(url_for("users.login"))

            if user.role is None:
                abort(403)

            if user.role.name not in allowed_roles:
                abort(403)

            return view(*args, **kwargs)

        return wrapped

    return decorator
