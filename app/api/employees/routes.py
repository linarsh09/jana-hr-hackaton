"""Backward-compatible imports for the employee API routes."""

from app.api.employee.routes import employees_bp, get_employee, get_employees

__all__ = ["employees_bp", "get_employee", "get_employees"]
