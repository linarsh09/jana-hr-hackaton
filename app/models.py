from datetime import datetime, timezone
from app.extensions import db
from sqlalchemy import CheckConstraint, UniqueConstraint


def now():
    return datetime.now(timezone.utc)


class Role(db.Model):
    __tablename__ = 'roles'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(30), unique=True, nullable=False)
    description = db.Column(db.String(255))
    users = db.relationship('User', back_populates='role')


class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'), nullable=False)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id'), unique=True)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=now)
    role = db.relationship('Role', back_populates='users')
    employee = db.relationship('Employee', back_populates='user', foreign_keys=[employee_id])


class Department(db.Model):
    __tablename__ = 'departments'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False, unique=True)
    description = db.Column(db.Text)
    employees = db.relationship('Employee', back_populates='department')


class Position(db.Model):
    __tablename__ = 'positions'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False, unique=True)
    description = db.Column(db.Text)
    employees = db.relationship('Employee', back_populates='position')


class Employee(db.Model):
    __tablename__ = 'employees'
    __table_args__ = (CheckConstraint('manager_id IS NULL OR manager_id <> id', name='ck_employee_not_self_manager'),)
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False)
    hire_date = db.Column(db.Date, nullable=False)
    vacation_days = db.Column(db.Integer, nullable=False, default=24, server_default="24")
    salary = db.Column(db.Numeric(12, 2))
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'), nullable=False)
    position_id = db.Column(db.Integer, db.ForeignKey('positions.id'), nullable=False)
    manager_id = db.Column(db.Integer, db.ForeignKey('employees.id'))
    department = db.relationship('Department', back_populates='employees')
    position = db.relationship('Position', back_populates='employees')
    manager = db.relationship('Employee', remote_side=[id], back_populates='subordinates', foreign_keys=[manager_id])
    subordinates = db.relationship('Employee', back_populates='manager', foreign_keys=[manager_id])
    user = db.relationship('User', back_populates='employee', uselist=False, foreign_keys='User.employee_id')
    vacation_requests = db.relationship('VacationRequest', back_populates='employee', foreign_keys='VacationRequest.employee_id')
    performance_reviews = db.relationship('PerformanceReview', back_populates='employee', foreign_keys='PerformanceReview.employee_id')
    ai_conversations = db.relationship('AIConversation', back_populates='employee')
    @property
    def full_name(self):
        return f'{self.first_name} {self.last_name}'


class VacationRequest(db.Model):
    __tablename__ = 'vacation_requests'
    __table_args__ = (CheckConstraint('end_date >= start_date', name='ck_vacation_dates'), CheckConstraint("status IN ('pending', 'approved', 'rejected')", name='ck_vacation_status'))
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=False)
    request_type = db.Column(db.String(30), nullable=False, default="vacation")
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(20), nullable=False, default='pending')
    comment = db.Column(db.Text)
    reviewed_by_id = db.Column(db.Integer, db.ForeignKey('employees.id'))
    reviewed_at = db.Column(db.DateTime(timezone=True))
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=now)
    employee = db.relationship('Employee', back_populates='vacation_requests', foreign_keys=[employee_id])
    reviewer = db.relationship('Employee', foreign_keys=[reviewed_by_id])
    @property
    def days(self):
        return (self.end_date - self.start_date).days + 1


class PerformanceReview(db.Model):
    __tablename__ = 'performance_reviews'
    __table_args__ = (CheckConstraint('period_end >= period_start', name='ck_review_period'), CheckConstraint('score IS NULL OR (score >= 1 AND score <= 5)', name='ck_review_score'), CheckConstraint("status IN ('draft', 'completed')", name='ck_review_status'))
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=False)
    reviewer_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=False)
    period_start = db.Column(db.Date, nullable=False)
    period_end = db.Column(db.Date, nullable=False)
    score = db.Column(db.Integer)
    strengths = db.Column(db.Text)
    weaknesses = db.Column(db.Text)
    status = db.Column(db.String(20), nullable=False, default='draft')
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=now)
    employee = db.relationship('Employee', back_populates='performance_reviews', foreign_keys=[employee_id])
    reviewer = db.relationship('Employee', foreign_keys=[reviewer_id])


class KnowledgeCategory(db.Model):
    __tablename__ = 'knowledge_categories'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), unique=True, nullable=False)
    articles = db.relationship('KnowledgeArticle', back_populates='category')


class KnowledgeArticle(db.Model):
    __tablename__ = 'knowledge_articles'
    id = db.Column(db.Integer, primary_key=True)
    category_id = db.Column(db.Integer, db.ForeignKey('knowledge_categories.id'), nullable=False)
    author_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=False)
    title = db.Column(db.String(255), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=now)
    category = db.relationship('KnowledgeCategory', back_populates='articles')
    author = db.relationship('Employee', foreign_keys=[author_id])


class Course(db.Model):
    __tablename__ = 'courses'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    created_by_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=now)
    creator = db.relationship('Employee', foreign_keys=[created_by_id])
    modules = db.relationship('CourseModule', back_populates='course')
    enrollments = db.relationship('CourseEnrollment', back_populates='course')


class CourseModule(db.Model):
    __tablename__ = 'course_modules'
    __table_args__ = (UniqueConstraint('course_id', 'position', name='uq_course_module_order'), UniqueConstraint('id', 'course_id', name='uq_module_course_pair'), CheckConstraint('position > 0', name='ck_module_position'))
    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    title = db.Column(db.String(255), nullable=False)
    content = db.Column(db.Text)
    position = db.Column(db.Integer, nullable=False)
    course = db.relationship('Course', back_populates='modules')
    progress = db.relationship('ModuleProgress', back_populates='module')


class CourseEnrollment(db.Model):
    __tablename__ = 'course_enrollments'
    __table_args__ = (UniqueConstraint('employee_id', 'course_id', name='uq_employee_course'), UniqueConstraint('id', 'course_id', name='uq_enrollment_course_pair'), CheckConstraint("status IN ('enrolled', 'in_progress', 'completed')", name='ck_enrollment_status'))
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    status = db.Column(db.String(20), nullable=False, default='enrolled')
    enrolled_at = db.Column(db.DateTime(timezone=True), nullable=False, default=now)
    completed_at = db.Column(db.DateTime(timezone=True))
    employee = db.relationship('Employee', foreign_keys=[employee_id])
    course = db.relationship('Course', back_populates='enrollments')
    progress = db.relationship('ModuleProgress', back_populates='enrollment')


class ModuleProgress(db.Model):
    __tablename__ = 'module_progress'
    __table_args__ = (UniqueConstraint('enrollment_id', 'module_id', name='uq_enrollment_module'),)
    id = db.Column(db.Integer, primary_key=True)
    enrollment_id = db.Column(db.Integer, nullable=False)
    module_id = db.Column(db.Integer, nullable=False)
    course_id = db.Column(db.Integer, nullable=False)
    completed_at = db.Column(db.DateTime(timezone=True), nullable=False, default=now)
    __table_args__ = (
        UniqueConstraint('enrollment_id', 'module_id', name='uq_enrollment_module'),
        db.ForeignKeyConstraint(['enrollment_id', 'course_id'], ['course_enrollments.id', 'course_enrollments.course_id']),
        db.ForeignKeyConstraint(['module_id', 'course_id'], ['course_modules.id', 'course_modules.course_id']),
    )
    enrollment = db.relationship('CourseEnrollment', back_populates='progress')
    module = db.relationship('CourseModule', back_populates='progress')


class AIConversation(db.Model):
    __tablename__ = 'ai_conversations'
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=False)
    title = db.Column(db.String(255))
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=now)
    employee = db.relationship('Employee', back_populates='ai_conversations')
    messages = db.relationship('AIMessage', back_populates='conversation', order_by='AIMessage.id')


class AIMessage(db.Model):
    __tablename__ = 'ai_messages'
    __table_args__ = (CheckConstraint("sender IN ('user', 'assistant', 'system')", name='ck_ai_sender'),)
    id = db.Column(db.Integer, primary_key=True)
    conversation_id = db.Column(db.Integer, db.ForeignKey('ai_conversations.id'), nullable=False)
    sender = db.Column(db.String(20), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=now)
    conversation = db.relationship('AIConversation', back_populates='messages')


class VacationBalanceTransaction(db.Model):
    __tablename__ = 'vacation_balance_transactions'
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=False)
    days_delta = db.Column(db.Numeric(6, 2), nullable=False)
    reason = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=now)
    employee = db.relationship('Employee', foreign_keys=[employee_id])
