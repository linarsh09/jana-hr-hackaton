"""Role rules shared with the academy module.

The academy owns course pages and progress records. It can import these
helpers without placing course implementation inside the account package.
"""
from app.models import Employee, User


def can_take_courses(user: User | None) -> bool:
    # INTEGRATION POINT (academy): use this before allowing a user to start a course.
    """Only ordinary employees take courses; HR and managers assign them."""
    return user is not None and user.is_active and user.role is not None and user.role.name == "employee"


def can_assign_courses(user: User | None, employee: Employee) -> bool:
    # INTEGRATION POINT (academy): use this before creating an assignment.
    """HR can assign to anyone; managers can assign to their direct reports."""
    if user is None or not user.is_active:
        return False
    if user.role is None:
        return False
    if user.role.name == "hr":
        return True
    return (
        user.role.name == "manager"
        and user.employee is not None
        and employee.manager_id == user.employee.id
    )
