from app.extensions import db
from datetime import datetime, timezone


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
        db.UniqueConstraint("course_id", "position", name="uq_academy_lesson_position"),
        db.CheckConstraint("position > 0", name="ck_academy_lesson_position"),
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
    completed_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))


class CourseAssignment(db.Model):
    __tablename__ = "academy_course_assignments"
    employee_id = db.Column(db.Integer, db.ForeignKey("employees.id"), primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey("academy_courses.id"), primary_key=True)
    assigned_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    assigned_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
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
    __table_args__ = (db.UniqueConstraint("course_id", "position", name="uq_academy_question_position"),)


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
    submitted_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    __table_args__ = (db.Index("ix_academy_attempt_user_course", "user_id", "course_id"),)
