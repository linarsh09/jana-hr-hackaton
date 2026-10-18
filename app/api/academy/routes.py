from functools import wraps

from flask import Blueprint, g, jsonify, request

from app.extensions import db
from app.models import Lesson
from . import service


academy_bp = Blueprint("academy", __name__, url_prefix="/api/academy")


@academy_bp.errorhandler(service.AcademyError)
def academy_error(error):
    return jsonify(error=error.code), error.status


def authenticated(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        user = getattr(g, "current_user", None)
        if user is None or not user.is_active:
            return jsonify(error="authentication_required"), 401
        return view(*args, **kwargs)
    return wrapped


def course_data(course):
    return dict(id=course.id, title=course.title, description=course.description)


@academy_bp.get("/courses")
@authenticated
def courses():
    records = service.visible_courses()
    return jsonify(courses=[course_data(course) for course in records])


@academy_bp.get("/courses/<int:course_id>")
@authenticated
def course_detail(course_id):
    course = service.accessible_course(course_id)
    if course is None:
        return jsonify(error="course_not_found"), 404
    data = course_data(course)
    data["lessons"] = [
        dict(id=lesson.id, title=lesson.title, position=lesson.position)
        for lesson in course.lessons
    ]
    return jsonify(data)


@academy_bp.get("/courses/<int:course_id>/lessons/<int:lesson_id>")
@authenticated
def lesson_detail(course_id, lesson_id):
    service.accessible_course(course_id)
    lesson = db.session.get(Lesson, lesson_id)
    if lesson is None or lesson.course_id != course_id:
        return jsonify(error="lesson_not_found"), 404
    return jsonify(id=lesson.id, course_id=lesson.course_id, title=lesson.title,
                   content=lesson.content, position=lesson.position)


@academy_bp.get("/csrf-token")
@authenticated
def csrf():
    return jsonify(csrf_token=service.csrf_token())


@academy_bp.post("/lessons/<int:lesson_id>/complete")
@authenticated
def complete(lesson_id):
    service.check_csrf(request.headers.get("X-CSRF-Token"))
    lesson = service.complete_lesson(lesson_id)
    return jsonify(service.progress_data(lesson.course, g.current_user.id))


@academy_bp.get("/courses/<int:course_id>/progress")
@authenticated
def progress(course_id):
    course = service.accessible_course(course_id)
    if not service.can_take_courses(g.current_user):
        raise service.AcademyError("forbidden", 403)
    return jsonify(service.progress_data(course, g.current_user.id))


@academy_bp.get("/employees")
@authenticated
def employees():
    if not service.manages_courses():
        raise service.AcademyError("forbidden", 403)
    return jsonify(employees=[dict(id=employee.id, name=employee.full_name)
                              for employee in service.eligible_employees()])


@academy_bp.route("/assignments", methods=["GET", "POST"])
@authenticated
def assignments():
    if not service.manages_courses():
        raise service.AcademyError("forbidden", 403)
    if request.method == "GET":
        return jsonify(assignments=service.assignment_report())
    service.check_csrf(request.headers.get("X-CSRF-Token"))
    data = request.get_json(silent=True)
    if not isinstance(data, dict) or any(type(data.get(key)) is not int or data[key] <= 0
                                        for key in ("employee_id", "course_id")):
        raise service.AcademyError("invalid_assignment", 400)
    row = service.assign_course(data["course_id"], data["employee_id"])
    return jsonify(employee_id=row.employee_id, course_id=row.course_id)


@academy_bp.route('/courses/<int:course_id>/quiz', methods=['GET', 'POST'])
@authenticated
def final_quiz(course_id):
    from . import quiz
    if request.method == 'GET':
        return jsonify(quiz.public_quiz(course_id))
    service.check_csrf(request.headers.get('X-CSRF-Token'))
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise service.AcademyError('invalid_answers', 400)
    attempt = quiz.submit(course_id, data.get('answers'), data.get('submission_id'))
    return jsonify(score_percent=attempt.score_percent, passed=attempt.passed,
                   correct_count=attempt.correct_count, question_count=attempt.question_count,
                   quiz=quiz.summary(course_id, g.current_user.id))