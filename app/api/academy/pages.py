from flask import Blueprint, abort, flash, g, redirect, render_template, request, session, url_for

from app.core.permissions import login_required
from app.api.account.course_access import can_take_courses
from app.extensions import db
from app.models import Lesson, LessonCompletion
from . import service

academy_pages = Blueprint("academy_pages", __name__, url_prefix="/academy", template_folder="templates")


@academy_pages.errorhandler(service.AcademyError)
def academy_error(error):
    return render_template("academy/error.html", error=error), error.status


@academy_pages.get("/")
@academy_pages.get("/courses/<int:course_id>")
@academy_pages.get("/courses/<int:course_id>/lessons/<int:lesson_id>")
@login_required
def catalog(course_id=None, lesson_id=None):
    courses = service.visible_courses()
    course = service.accessible_course(course_id) if course_id else None
    if course_id and course is None:
        abort(404)
    lesson = db.session.get(Lesson, lesson_id) if lesson_id else None
    if lesson_id and (lesson is None or lesson.course_id != course_id):
        abort(404)
    completed = set(db.session.scalars(db.select(LessonCompletion.lesson_id).filter_by(user_id=g.current_user.id)))
    total = sum(len(item.lessons) for item in courses)
    done = sum(item.id in completed for entry in courses for item in entry.lessons)
    service.csrf_token()
    course_results = {item.id: service.progress_data(item, g.current_user.id) for item in courses}
    return render_template("academy/catalog.html", courses=courses, course=course,
                           lesson=lesson, completed=completed, total=total, done=done,
                           can_complete=can_take_courses(g.current_user),
                           manages_courses=service.manages_courses(),
                           course_results=course_results, course_progress=course_results.get(course_id),
                           employees=service.eligible_employees(),
                           report=service.assignment_report() if service.manages_courses() else [])


@academy_pages.post("/lessons/<int:lesson_id>/complete")
@login_required
def complete(lesson_id):
    service.check_csrf(request.form.get("csrf_token"))
    lesson = service.complete_lesson(lesson_id)
    following = next((item for item in lesson.course.lessons if item.position > lesson.position), None)
    if following:
        return redirect(url_for("academy_pages.catalog", course_id=lesson.course_id, lesson_id=following.id))
    return redirect(url_for("academy_pages.catalog", course_id=lesson.course_id))


@academy_pages.post("/assignments")
@login_required
def assign():
    service.check_csrf(request.form.get("csrf_token"))
    course_id = request.form.get("course_id", type=int)
    employee_id = request.form.get("employee_id", type=int)
    if not course_id or not employee_id:
        raise service.AcademyError("invalid_assignment", 400)
    service.assign_course(course_id, employee_id)
    flash("Курс назначен. Он доступен в личном кабинете сотрудника.", "success")
    return redirect(url_for("academy_pages.catalog"))


@academy_pages.route('/courses/<int:course_id>/quiz', methods=['GET', 'POST'])
@login_required
def final_quiz(course_id):
    from . import quiz
    course = quiz.ready_course(course_id)
    service.csrf_token()
    error = None
    if request.method == 'POST':
        service.check_csrf(request.form.get('csrf_token'))
        answers = {}
        for question in quiz.questions(course_id):
            value = request.form.get('question_' + str(question.id))
            try:
                answers[str(question.id)] = int(value)
            except (TypeError, ValueError):
                error = 'Ответь на каждый вопрос — затем отправь тест.'
        if error is None:
            attempt = quiz.submit(course_id, answers, request.form.get('submission_id'))
            flash(f'Результат: {attempt.score_percent}%. ' + ('Тест сдан!' if attempt.passed else 'Пока не сдан. Повтори материалы и попробуй ещё раз.'), 'success')
            return redirect(url_for('academy_pages.final_quiz', course_id=course_id))
    data = quiz.public_quiz(course_id)
    return render_template('academy/quiz.html', course=course, quiz_data=data,
                           quiz_summary=quiz.summary(course_id, g.current_user.id), quiz_error=error)