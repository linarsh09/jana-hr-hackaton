
from functools import wraps

from flask import g, redirect, url_for, abort
from sqlalchemy import false
from app.models import Employee, User, UserRole
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


def _role_value(role):
    """Return the stored string value for an enum role or plain role string."""
    return role.value if isinstance(role, UserRole) else str(role)


def role_required(*allowed_roles: UserRole | str):
    """Требует авторизации и одну из указанных ролей."""
    def decorator(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            user = getattr(g, "current_user", None)

            if user is None:
                return redirect(url_for("users.login"))

            allowed_values = {_role_value(role) for role in allowed_roles}
            if _role_value(user.role) not in allowed_values:
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
    if user is None:
        return query.filter(false())
    role = _role_value(user.role)
    if role in (UserRole.HR.value, UserRole.ADMIN.value):
        return query
    own = current_employee()
    if own is None:
        return query.filter(false())
    if role == UserRole.MANAGER.value:
        return query.filter((Employee.id == own.id) | (Employee.manager_id == own.id))
    return query.filter(Employee.id == own.id)


def can_access_employee(employee: Employee | int) -> bool:
    """Shared access rule for employee data and future course progress APIs.

    HR and legacy ADMIN accounts can access everyone; managers can access their
    direct reports; employees can access only their own linked profile.
    """
    user = getattr(g, "current_user", None)
    target = employee if isinstance(employee, Employee) else db.session.get(Employee, employee)
    if target is None:
        return False
    return visible_employee_query().filter(Employee.id == target.id).first() is not None


def can_manage_employee(employee: Employee | int) -> bool:
    """Whether the current user may manage a profile, e.g. assign a course."""
    user = getattr(g, "current_user", None)
    if user is None:
        return False
    role = _role_value(user.role)
    if role in (UserRole.HR.value, UserRole.ADMIN.value):
        return True
    if role != UserRole.MANAGER.value:
        return False
    target = employee if isinstance(employee, Employee) else db.session.get(Employee, employee)
    own = current_employee()
    return target is not None and own is not None and target.manager_id == own.id
