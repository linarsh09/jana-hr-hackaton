import secrets

from flask import g
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.api.account.course_access import can_take_courses
from .models import QuizQuestion, QuizAttempt
from . import service

PASS_PERCENT = 80


def questions(course_id):
    return db.session.scalars(db.select(QuizQuestion).filter_by(course_id=course_id).order_by(QuizQuestion.position)).all()


def summary(course_id, user_id):
    attempts = db.session.scalars(db.select(QuizAttempt).filter_by(course_id=course_id, user_id=user_id)
                                  .order_by(QuizAttempt.submitted_at, QuizAttempt.id)).all()
    return dict(required=bool(questions(course_id)), attempts=len(attempts),
                passed=any(attempt.passed for attempt in attempts),
                best_score=max((attempt.score_percent for attempt in attempts), default=None),
                last_score=attempts[-1].score_percent if attempts else None,
                last_attempt_at=attempts[-1].submitted_at.isoformat() + 'Z' if attempts else None,
                pass_percent=PASS_PERCENT)


def ready_course(course_id):
    course = service.accessible_course(course_id)
    if not can_take_courses(g.current_user):
        raise service.AcademyError('forbidden', 403)
    progress = service.progress_data(course, g.current_user.id)
    if not course.lessons or progress['completed_lessons'] != progress['total_lessons']:
        raise service.AcademyError('lessons_not_completed', 409)
    if not questions(course_id):
        raise service.AcademyError('quiz_not_found', 404)
    return course


def public_quiz(course_id):
    ready_course(course_id)
    return dict(course_id=course_id, pass_percent=PASS_PERCENT, submission_id=secrets.token_hex(24),
                questions=[dict(id=q.id, text=q.text, options=q.options) for q in questions(course_id)])


def submit(course_id, answers, submission_id):
    ready_course(course_id)
    if not isinstance(submission_id, str) or not 16 <= len(submission_id) <= 64:
        raise service.AcademyError('invalid_submission_id', 400)
    previous = db.session.scalar(db.select(QuizAttempt).filter_by(submission_id=submission_id))
    if previous:
        if previous.user_id != g.current_user.id or previous.course_id != course_id:
            raise service.AcademyError('invalid_submission_id', 400)
        return previous
    items = questions(course_id)
    if not isinstance(answers, dict) or set(answers) != {str(q.id) for q in items}:
        raise service.AcademyError('answer_all_questions', 400)
    correct = 0
    for question in items:
        answer = answers[str(question.id)]
        if type(answer) is not int or not 0 <= answer < len(question.options):
            raise service.AcademyError('invalid_answer', 400)
        correct += answer == question.correct_option
    attempt = QuizAttempt(course_id=course_id, user_id=g.current_user.id, submission_id=submission_id,
                          correct_count=correct, question_count=len(items), score_percent=correct*100//len(items),
                          passed=correct*100 >= PASS_PERCENT*len(items))
    db.session.add(attempt)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        previous = db.session.scalar(db.select(QuizAttempt).filter_by(submission_id=submission_id,
                                      course_id=course_id, user_id=g.current_user.id))
        if previous is None:
            raise
        return previous
    return attempt
