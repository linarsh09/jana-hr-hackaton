from datetime import datetime, timezone

from sqlalchemy import CheckConstraint, ForeignKeyConstraint, UniqueConstraint, Index
from werkzeug.security import check_password_hash, generate_password_hash

from app.extensions import db


def now():
    return datetime.now(timezone.utc)


class Role(db.Model):
    __tablename__ = "roles"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(30), unique=True, nullable=False)
    description = db.Column(db.String(255))

    users = db.relationship("User", back_populates="role")


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role_id = db.Column(db.Integer, db.ForeignKey("roles.id"), nullable=False)
    employee_id = db.Column(db.Integer, db.ForeignKey("employees.id"), unique=True)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=now)

    role = db.relationship("Role", back_populates="users")
    employee = db.relationship("Employee", back_populates="user", foreign_keys=[employee_id])
    chat_logs = db.relationship("AIChatLog", back_populates="user", cascade="all, delete-orphan")
    fallbacks = db.relationship("AIFallbackLog", back_populates="user", cascade="all, delete-orphan")

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Department(db.Model):
    __tablename__ = "departments"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False, unique=True)
    description = db.Column(db.Text)

    employees = db.relationship("Employee", back_populates="department")


class Position(db.Model):
    __tablename__ = "positions"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False, unique=True)
    description = db.Column(db.Text)

    employees = db.relationship("Employee", back_populates="position")


class Employee(db.Model):
    __tablename__ = "employees"
    __table_args__ = (
        CheckConstraint("manager_id IS NULL OR manager_id <> id", name="ck_employee_not_self_manager"),
        CheckConstraint("vacation_balance >= 0", name="ck_employee_vacation_balance"),
    )

    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False)
    hire_date = db.Column(db.Date, nullable=False)
    vacation_days = db.Column(db.Integer, nullable=False, default=24, server_default="24")
    salary = db.Column(db.Numeric(12, 2))
    vacation_balance = db.Column(db.Integer, nullable=False, default=0)
    department_id = db.Column(db.Integer, db.ForeignKey("departments.id"), nullable=False)
    position_id = db.Column(db.Integer, db.ForeignKey("positions.id"), nullable=False)
    manager_id = db.Column(db.Integer, db.ForeignKey("employees.id"))

    department = db.relationship("Department", back_populates="employees")
    position = db.relationship("Position", back_populates="employees")
    manager = db.relationship(
        "Employee", remote_side=[id], back_populates="subordinates", foreign_keys=[manager_id]
    )
    subordinates = db.relationship(
        "Employee", back_populates="manager", foreign_keys=[manager_id]
    )
    user = db.relationship(
        "User", back_populates="employee", uselist=False, foreign_keys="User.employee_id"
    )
    vacation_requests = db.relationship(
        "VacationRequest", back_populates="employee", foreign_keys="VacationRequest.employee_id"
    )
    authored_articles = db.relationship("KnowledgeArticle", back_populates="author")
    reviewed_requests = db.relationship(
        "VacationRequest", back_populates="reviewer", foreign_keys="VacationRequest.reviewed_by_id"
    )

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"


class VacationRequest(db.Model):
    __tablename__ = "vacation_requests"
    __table_args__ = (
        CheckConstraint("end_date >= start_date", name="ck_vacation_dates"),
        CheckConstraint("status IN ('pending', 'approved', 'rejected')", name="ck_vacation_status"),
    )
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey("employees.id"), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(20), nullable=False, default="pending")
    comment = db.Column(db.Text)
    reviewed_by_id = db.Column(db.Integer, db.ForeignKey("employees.id"))
    reviewed_at = db.Column(db.DateTime(timezone=True))
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=now)

    employee = db.relationship(
        "Employee", back_populates="vacation_requests", foreign_keys=[employee_id]
    )
    reviewer = db.relationship(
        "Employee", back_populates="reviewed_requests", foreign_keys=[reviewed_by_id]
    )

    @property
    def days(self):
        return (self.end_date - self.start_date).days + 1


class Notification(db.Model):
    __tablename__ = 'notifications'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    message = db.Column(db.String(255), nullable=False)
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime(timezone=True), default=now)

    user = db.relationship('User', backref=db.backref('notifications', lazy=True))


class KnowledgeCategory(db.Model):
    __tablename__ = "knowledge_categories"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), unique=True, nullable=False)

    articles = db.relationship("KnowledgeArticle", back_populates="category")


class KnowledgeArticle(db.Model):
    __tablename__ = "knowledge_articles"

    id = db.Column(db.Integer, primary_key=True)
    category_id = db.Column(db.Integer, db.ForeignKey("knowledge_categories.id"), nullable=False)
    author_id = db.Column(db.Integer, db.ForeignKey("employees.id"), nullable=False)
    title = db.Column(db.String(255), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=now)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=now, onupdate=now)

    category = db.relationship("KnowledgeCategory", back_populates="articles")
    author = db.relationship("Employee", back_populates="authored_articles")


class Course(db.Model):
    __tablename__ = "academy_courses"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False, default="")
    lessons = db.relationship(
        "Lesson", back_populates="course", order_by="Lesson.position",
        cascade="all, delete-orphan",
    )


class Lesson(db.Model):
    __tablename__ = "academy_lessons"
    __table_args__ = (
        UniqueConstraint("course_id", "position", name="uq_academy_lesson_position"),
        CheckConstraint("position > 0", name="ck_academy_lesson_position"),
    )

    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey("academy_courses.id"), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False, default="")
    position = db.Column(db.Integer, nullable=False)
    course = db.relationship("Course", back_populates="lessons")


class LessonCompletion(db.Model):
    __tablename__ = "academy_lesson_completions"
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), primary_key=True)
    lesson_id = db.Column(db.Integer, db.ForeignKey("academy_lessons.id"), primary_key=True)
    completed_at = db.Column(db.DateTime(timezone=True), nullable=False, default=now)


class CourseAssignment(db.Model):
    __tablename__ = "academy_course_assignments"
    employee_id = db.Column(db.Integer, db.ForeignKey("employees.id"), primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey("academy_courses.id"), primary_key=True)
    assigned_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    assigned_at = db.Column(db.DateTime(timezone=True), nullable=False, default=now)
    employee = db.relationship("Employee")
    course = db.relationship("Course")


class QuizQuestion(db.Model):
    __tablename__ = "academy_quiz_questions"
    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey("academy_courses.id"), nullable=False, index=True)
    position = db.Column(db.Integer, nullable=False)
    text = db.Column(db.Text, nullable=False)
    options = db.Column(db.JSON, nullable=False)
    correct_option = db.Column(db.Integer, nullable=False)
    __table_args__ = (UniqueConstraint("course_id", "position", name="uq_academy_question_position"),)


class QuizAttempt(db.Model):
    __tablename__ = "academy_quiz_attempts"
    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey("academy_courses.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    submission_id = db.Column(db.String(64), nullable=False, unique=True)
    correct_count = db.Column(db.Integer, nullable=False)
    question_count = db.Column(db.Integer, nullable=False)
    score_percent = db.Column(db.Integer, nullable=False)
    passed = db.Column(db.Boolean, nullable=False)
    submitted_at = db.Column(db.DateTime(timezone=True), nullable=False, default=now)
    __table_args__ = (Index("ix_academy_attempt_user_course", "user_id", "course_id"),)


# Новые таблицы для аналитики и работы ИИ-ассистента
class AIChatLog(db.Model):
    __tablename__ = "ai_chat_logs"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    query = db.Column(db.Text, nullable=False)
    response = db.Column(db.Text, nullable=False)
    triggered_fallback = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=now)

    user = db.relationship("User", back_populates="chat_logs")


class AIFallbackLog(db.Model):
    __tablename__ = "ai_fallback_logs"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    unanswered_query = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), nullable=False, default="pending")  # pending, resolved
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=now)

    user = db.relationship("User", back_populates="fallbacks")