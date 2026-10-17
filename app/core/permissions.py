
from functools import wraps

from flask import g, redirect, url_for, abort, session
from sqlalchemy import false
from app.models import Employee, User, Role
from app.extensions import db
from app.models import Employee, User


def load_current_user():
    """Загружает текущего пользователя для запроса."""
    from flask import session

    user_id = session.get("user_id")
    g.current_user = None
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
            if user.role is None or user.role.name not in allowed_roles:
                abort(403)
            return view(*args, **kwargs)
        return wrapped
    return decorator


def current_employee() -> Employee | None:
    """Return the employee profile linked to the signed-in account, if any."""
    user = getattr(g, "current_user", None)
    return user.employee if user is not None else None


def visible_employee_query():
    """Query employee profiles visible to the signed-in user.

    Reuse this in employee and course-progress features to keep their scopes
    consistent. Managers currently see their own profile and direct reports.
    """
    user = getattr(g, "current_user", None)
    query = Employee.query
    if user is None or user.role is None:
        return query.filter(false())
    if user.role.name == "hr":
        return query
    employee = current_employee()
    if employee is None:
        return query.filter(false())
    if user.role.name == "manager":
        return query.filter((Employee.id == employee.id) | (Employee.manager_id == employee.id))
    if user.role.name == "employee":
        return query.filter(Employee.id == employee.id)
    return query.filter(false())


def can_access_employee(employee):
    target = employee if isinstance(employee, Employee) else db.session.get(Employee, employee)
    return target is not None and visible_employee_query().filter(Employee.id == target.id).first() is not None


def can_manage_employee(employee):
    user = getattr(g, "current_user", None)
    if user is None or user.role is None:
        return False
    target = employee if isinstance(employee, Employee) else db.session.get(Employee, employee)
    if target is None:
        return False
    if user.role.name == "hr":
        return True
    own_employee = current_employee()
    return user.role.name == "manager" and own_employee is not None and target.manager_id == own_employee.id
