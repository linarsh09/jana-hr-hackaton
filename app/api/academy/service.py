"""Shared access and progress rules for HTML pages and JSON API."""
import secrets
from hmac import compare_digest

from flask import g, session
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.models import Employee, User, Role
from app.api.account.course_access import can_assign_courses, can_take_courses
from app.models import Course, CourseAssignment, Lesson, LessonCompletion


class AcademyError(Exception):
    def __init__(self, code, status):
        self.code, self.status = code, status


def csrf_token():
    return session.setdefault("academy_csrf", secrets.token_hex(32))


def check_csrf(token):
    expected = session.get("academy_csrf")
    if not expected or not isinstance(token, str) or not compare_digest(expected, token):
        raise AcademyError("invalid_csrf_token", 400)


def manages_courses():
    return g.current_user.role in (Role.HR, Role.ADMIN, Role.MANAGER)


def visible_courses():
    query = db.select(Course).order_by(Course.id)
    if not manages_courses():
        employee = g.current_user.employee
        if employee is None:
            return []
        query = query.join(CourseAssignment).where(CourseAssignment.employee_id == employee.id)
    return db.session.scalars(query).all()


def accessible_course(course_id):
    course = db.session.get(Course, course_id)
    if course is None:
        raise AcademyError("course_not_found", 404)
    if not manages_courses():
        employee = g.current_user.employee
        if employee is None or db.session.get(CourseAssignment, (employee.id, course_id)) is None:
            raise AcademyError("course_not_found", 404)
    return course


def eligible_employees():
    query = db.select(Employee).join(User, Employee.user_id == User.id).where(
        User.role == Role.EMPLOYEE, User.is_active.is_(True))
    if g.current_user.role == Role.MANAGER:
        own = g.current_user.employee
        if own is None:
            return []
        query = query.where(Employee.manager_id == own.id)
    elif g.current_user.role not in (Role.HR, Role.ADMIN):
        return []
    return db.session.scalars(query.order_by(Employee.last_name, Employee.id)).all()


def assign_course(course_id, employee_id):
    if not manages_courses():
        raise AcademyError("forbidden", 403)
    employee = db.session.get(Employee, employee_id)
    if employee is None:
        raise AcademyError("employee_not_found", 404)
    if not can_assign_courses(g.current_user, employee):
        raise AcademyError("forbidden", 403)
    if not can_take_courses(employee.user):
        raise AcademyError("employee_not_eligible", 400)
    accessible_course(course_id)
    key = (employee_id, course_id)
    assignment = db.session.get(CourseAssignment, key)
    if assignment is None:
        assignment = CourseAssignment(employee_id=employee_id, course_id=course_id, assigned_by=g.current_user.id)
        db.session.add(assignment)
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            assignment = db.session.get(CourseAssignment, key)
            if assignment is None:
                raise
    return assignment


def complete_lesson(lesson_id):
    if not can_take_courses(g.current_user):
        raise AcademyError("forbidden", 403)
    lesson = db.session.get(Lesson, lesson_id)
    if lesson is None:
        raise AcademyError("lesson_not_found", 404)
    accessible_course(lesson.course_id)
    key = (g.current_user.id, lesson_id)
    if db.session.get(LessonCompletion, key) is None:
        db.session.add(LessonCompletion(user_id=key[0], lesson_id=key[1]))
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            if db.session.get(LessonCompletion, key) is None:
                raise
    return lesson


def progress_data(course, user_id):
    ids = [lesson.id for lesson in course.lessons]
    done = set(db.session.scalars(db.select(LessonCompletion.lesson_id).where(
        LessonCompletion.user_id == user_id, LessonCompletion.lesson_id.in_(ids))))
    total = len(ids)
    status = "completed" if total and len(done) == total else ("in_progress" if done else "not_started")
    from .quiz import summary
    quiz = summary(course.id, user_id)
    if status == "completed" and quiz['required'] and not quiz['passed']:
        status = "test_pending"
    return dict(course_id=course.id, total_lessons=total, completed_lessons=len(done),
                progress_percent=int(len(done) * 100 / total) if total else 0,
                status=status, completed_lesson_ids=sorted(done), quiz=quiz)


def assignment_report():
    employees = eligible_employees()
    by_id = {employee.id: employee for employee in employees}
    assignments = db.session.scalars(db.select(CourseAssignment).where(
        CourseAssignment.employee_id.in_(by_id)).order_by(CourseAssignment.assigned_at.desc())).all()
    return [dict(employee_id=row.employee_id, employee_name=by_id[row.employee_id].full_name,
                 course_title=row.course.title, **progress_data(row.course, by_id[row.employee_id].user_id))
            for row in assignments]