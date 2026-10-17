from functools import wraps

from flask import g, redirect, url_for, abort, session
from sqlalchemy import false

from app.models import Employee, User
from app.extensions import db


def load_current_user():
    user_id = session.get("user_id")

    g.current_user = None

    if user_id is None:
        return

    user = db.session.get(User, user_id)

    if user is None or not user.is_active:
        session.clear()
        return

    g.current_user = user


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if getattr(g, "current_user", None) is None:
            return redirect(url_for("users.login"))

        return view(*args, **kwargs)

    return wrapped


def role_required(*allowed_roles):
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


def current_employee():
    user = getattr(g, "current_user", None)

    if user is None:
        return None

    return user.employee


def visible_employee_query():
    user = getattr(g, "current_user", None)
    query = Employee.query

    if user is None or user.role is None:
        return query.filter(false())

    role_name = user.role.name

    if role_name == "hr":
        return query

    employee = current_employee()

    if employee is None:
        return query.filter(false())


    if role_name == "manager":
        return query.filter(
            (Employee.id == employee.id)
            | (Employee.manager_id == employee.id)
        )

    if role_name == "employee":
        return query.filter(Employee.id == employee.id)

    return query.filter(false())



def can_access_employee(employee):
    target = (
        employee
        if isinstance(employee, Employee)
        else db.session.get(Employee, employee)
    )

    if target is None:
        return False

    return (
        visible_employee_query()
        .filter(Employee.id == target.id)
        .first()
        is not None
    )


def can_manage_employee(employee):
    user = getattr(g, "current_user", None)

    if user is None or user.role is None:
        return False

    target = (
        employee
        if isinstance(employee, Employee)
        else db.session.get(Employee, employee)
    )

    if target is None:
        return False

    if user.role.name == "hr":
        return True

    if user.role.name != "manager":
        return False

    own_employee = current_employee()

    return (
        own_employee is not None
        and target.manager_id == own_employee.id
    )
