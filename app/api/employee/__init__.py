"""Compatibility exports for code that still uses the legacy plural package."""

from app.api.employee.repository import EmployeeRepository

__all__ = ["EmployeeRepository"]
