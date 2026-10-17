# app/models.py

from datetime import date, datetime
from enum import Enum

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Enum as SQLEnum
from .extensions import db
import enum


# =========================
# Enums
# =========================

class VacationStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class RequestType(str, Enum):
    VACATION = "vacation"
    SICK_LEAVE = "sick_leave"
    CERTIFICATE = "certificate"
    OTHER = "other"


class ReviewStatus(str, Enum):
    DRAFT = "draft"
    COMPLETED = "completed"


# =========================
# 1. Department
# =========================

class Department(db.Model):
    __tablename__ = "departments"

    id = db.Column(db.Integer, primary_key=True)

    name = db.Column(
        db.String(120),
        nullable=False,
        unique=True,
    )

    description = db.Column(
        db.Text,
        nullable=True,
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        nullable=False,
    )

    employees = db.relationship(
        "Employee",
        back_populates="department",
        lazy="select",
    )

    def __repr__(self):
        return f"<Department {self.name}>"


# =========================
# 2. Employee
# =========================

class Employee(db.Model):
    __tablename__ = "employees"

    id = db.Column(
        db.Integer,
        primary_key=True,
    )

    first_name = db.Column(
        db.String(100),
        nullable=False,
    )

    last_name = db.Column(
        db.String(100),
        nullable=False,
    )

    email = db.Column(
        db.String(255),
        nullable=False,
        unique=True,
        index=True,
    )

    position = db.Column(
        db.String(150),
        nullable=False,
    )

    company = db.Column(db.String(150), nullable=True)

    salary = db.Column(
        db.Numeric(12, 2),
        nullable=True,
    )

    hire_date = db.Column(
        db.Date,
        nullable=False,
    )

    vacation_days = db.Column(
        db.Integer,
        default=24,
        nullable=False,
    )

    department_id = db.Column(
        db.Integer,
        db.ForeignKey("departments.id"),
        nullable=False,
    )

    # Optional while test accounts and legacy employee records are being linked.
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), unique=True)
    manager_id = db.Column(db.Integer, db.ForeignKey("employees.id"), nullable=True, index=True)

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        nullable=False,
    )

    department = db.relationship(
        "Department",
        back_populates="employees",
    )

    user = db.relationship("User", back_populates="employee", foreign_keys=[user_id])
    manager = db.relationship(
        "Employee", remote_side=[id], back_populates="direct_reports", foreign_keys=[manager_id]
    )
    direct_reports = db.relationship(
        "Employee", back_populates="manager", foreign_keys=[manager_id]
    )

    vacation_requests = db.relationship(
        "VacationRequest",
        back_populates="employee",
        cascade="all, delete-orphan",
    )

    performance_reviews = db.relationship(
        "PerformanceReview",
        back_populates="employee",
        cascade="all, delete-orphan",
    )

    ai_conversations = db.relationship(
        "AIConversation",
        back_populates="employee",
        cascade="all, delete-orphan",
    )

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    def __repr__(self):
        return f"<Employee {self.email}>"


# =========================
# 3. VacationRequest
# =========================

class VacationRequest(db.Model):
    __tablename__ = "vacation_requests"

    id = db.Column(
        db.Integer,
        primary_key=True,
    )

    employee_id = db.Column(
        db.Integer,
        db.ForeignKey("employees.id"),
        nullable=False,
        index=True,
    )

    start_date = db.Column(
        db.Date,
        nullable=True,
    )

    end_date = db.Column(
        db.Date,
        nullable=True,
    )

    request_type = db.Column(
        SQLEnum(RequestType, name="request_type"),
        default=RequestType.VACATION,
        nullable=False,
    )

    status = db.Column(
        SQLEnum(VacationStatus),
        default=VacationStatus.PENDING,
        nullable=False,
    )

    comment = db.Column(
        db.Text,
        nullable=True,
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        nullable=False,
    )

    employee = db.relationship(
        "Employee",
        back_populates="vacation_requests",
    )

    def __repr__(self):
        return f"<VacationRequest {self.id}>"

    @property
    def days(self):
        if self.start_date is None or self.end_date is None:
            return 0
        return (self.end_date - self.start_date).days + 1


# =========================
# 4. PerformanceReview
# =========================

class PerformanceReview(db.Model):
    __tablename__ = "performance_reviews"

    id = db.Column(
        db.Integer,
        primary_key=True,
    )

    employee_id = db.Column(
        db.Integer,
        db.ForeignKey("employees.id"),
        nullable=False,
        index=True,
    )

    reviewer_name = db.Column(
        db.String(200),
        nullable=False,
    )

    period = db.Column(
        db.String(50),
        nullable=False,
    )

    score = db.Column(
        db.Integer,
        nullable=True,
    )

    strengths = db.Column(
        db.Text,
        nullable=True,
    )

    weaknesses = db.Column(
        db.Text,
        nullable=True,
    )

    comment = db.Column(
        db.Text,
        nullable=True,
    )

    status = db.Column(
        SQLEnum(ReviewStatus),
        default=ReviewStatus.DRAFT,
        nullable=False,
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        nullable=False,
    )

    employee = db.relationship(
        "Employee",
        back_populates="performance_reviews",
    )

    def __repr__(self):
        return f"<PerformanceReview {self.id}>"


# =========================
# 5. AIConversation
# =========================

class AIConversation(db.Model):
    __tablename__ = "ai_conversations"

    id = db.Column(
        db.Integer,
        primary_key=True,
    )

    employee_id = db.Column(
        db.Integer,
        db.ForeignKey("employees.id"),
        nullable=False,
        index=True,
    )

    title = db.Column(
        db.String(255),
        nullable=True,
    )

    messages = db.Column(
        db.JSON,
        nullable=False,
        default=list,
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        nullable=False,
    )

    updated_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    employee = db.relationship(
        "Employee",
        back_populates="ai_conversations",
    )

    def __repr__(self):
        return f"<AIConversation {self.id}>"


class UserRole(enum.Enum):
    ADMIN = "admin"
    HR = "hr"
    MANAGER = "manager"
    EMPLOYEE = "employee"


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(
        db.Integer,
        primary_key=True,
    )

    username = db.Column(
        db.String(100),
        nullable=False,
        unique=True,
        index=True,
    )

    password_hash = db.Column(
        db.String(255),
        nullable=False,
    )

    is_active = db.Column(
        db.Boolean,
        default=True,
        nullable=False,
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        nullable=False,
    )

    role = db.Column(
        db.Enum(UserRole, name="user_role"),
        nullable=False,
        default=UserRole.EMPLOYEE,
    )

    employee = db.relationship("Employee", back_populates="user", uselist=False, foreign_keys="Employee.user_id")

    def __repr__(self):
        return f"<User {self.username} ({self.role.value})>"
