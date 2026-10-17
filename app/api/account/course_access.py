"""Role rules shared with the academy module.

The academy owns course pages and progress records. It can import these
helpers without placing course implementation inside the account package.
"""
from app.models import Employee, User, UserRole


def can_take_courses(user: User | None) -> bool:
    # INTEGRATION POINT (academy): use this before allowing a user to start a course.
    """Only ordinary employees take courses; HR and managers assign them."""
    return user is not None and user.is_active and user.role == UserRole.EMPLOYEE


def can_assign_courses(user: User | None, employee: Employee) -> bool:
    # INTEGRATION POINT (academy): use this before creating an assignment.
    """HR can assign to anyone; managers can assign to their direct reports."""
    if user is None or not user.is_active:
        return False
    if user.role == UserRole.HR:
        return True
    return (
        user.role == UserRole.MANAGER
        and user.employee is not None
        and employee.manager_id == user.employee.id
    )
