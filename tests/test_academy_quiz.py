import secrets
import unittest

import test_academy
from app.extensions import db
from app.models import UserRole
from app.api.academy.models import QuizQuestion, QuizAttempt, Course, LessonCompletion


class QuizTests(unittest.TestCase):
    tearDown = test_academy.AcademyCatalogTests.tearDown
    as_user = test_academy.AcademyCatalogTests.as_user
    add_account = test_academy.AcademyCatalogTests.add_account

    def setUp(self):
        test_academy.AcademyCatalogTests.setUp(self)
        for position in range(1, 6):
            db.session.add(QuizQuestion(course_id=self.course_id, position=position,
                text='Question ' + str(position), options=['Correct', 'Wrong'], correct_option=0))
        db.session.commit()
        self.headers = self.as_user(self.user_id)
        self.quiz_url = f'/api/academy/courses/{self.course_id}/quiz'

    def finish_lessons(self):
        for lesson in db.session.get(Course, self.course_id).lessons:
            self.client.post(f'/api/academy/lessons/{lesson.id}/complete', headers=self.headers)

    def submit_answers(self, correct, submission_id=None):
        questions = db.session.scalars(db.select(QuizQuestion).order_by(QuizQuestion.position)).all()
        answers = {str(question.id): (0 if index < correct else 1) for index, question in enumerate(questions)}
        return self.client.post(self.quiz_url, headers=self.headers,
            json={'answers':answers, 'submission_id':submission_id or secrets.token_hex(24)})

    def test_quiz_locks_until_lessons_finished_and_hides_answers(self):
        self.assertEqual(self.client.get(self.quiz_url).status_code, 409)
        self.assertEqual(self.submit_answers(5).status_code, 409)
        self.finish_lessons()
        progress = self.client.get(f'/api/academy/courses/{self.course_id}/progress').json
        self.assertEqual(progress['status'], 'test_pending')
        response = self.client.get(self.quiz_url)
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('correct_option', response.get_data(as_text=True))
        self.assertEqual(len(response.json['questions']), 5)
        html = self.client.get(f'/academy/courses/{self.course_id}')
        self.assertIn('Итоговый тест', html.get_data(as_text=True))
        self.assertNotIn('Курс завершён.</div>', html.get_data(as_text=True))

    def test_scores_retries_and_duplicate_submission(self):
        self.finish_lessons()
        self.assertEqual(self.submit_answers(3).json['score_percent'], 60)
        token = secrets.token_hex(24)
        response = self.submit_answers(4, token)
        self.assertTrue(response.json['passed'])
        self.assertEqual(response.json['score_percent'], 80)
        self.assertEqual(self.submit_answers(4, token).json['quiz']['attempts'], 2)
        response = self.submit_answers(0)
        self.assertFalse(response.json['passed'])
        self.assertTrue(response.json['quiz']['passed'])
        self.assertEqual(response.json['quiz']['best_score'], 80)
        self.assertEqual(response.json['quiz']['last_score'], 0)
        self.assertEqual(response.json['quiz']['attempts'], 3)
        self.assertEqual(self.client.get(f'/api/academy/courses/{self.course_id}/progress').json['status'], 'completed')

    def test_invalid_answers_do_not_create_attempts(self):
        self.finish_lessons()
        for answers in [{}, [], {'1':True}, {'1':-1}, {'1':'0'}]:
            response = self.client.post(self.quiz_url, headers=self.headers,
                json={'answers':answers,'submission_id':secrets.token_hex(24)})
            self.assertEqual(response.status_code, 400)
        self.assertEqual(db.session.query(QuizAttempt).count(), 0)
        self.assertEqual(self.client.post(self.quiz_url, json={}).status_code, 400)

    def test_quiz_roles_and_report_scope(self):
        self.finish_lessons()
        self.submit_answers(5)
        hr, _ = self.add_account('quiz_hr', UserRole.HR)
        self.as_user(hr.id)
        report = self.client.get('/api/academy/assignments').json['assignments'][0]
        self.assertTrue(report['quiz']['passed'])
        self.assertEqual(report['quiz']['best_score'], 100)
        self.assertEqual(report['quiz']['attempts'], 1)
        self.assertIsNotNone(report['quiz']['last_attempt_at'])
        self.assertEqual(self.client.get(self.quiz_url).status_code, 403)
        self.assertEqual(self.client.get('/academy/').status_code, 200)
        manager, manager_employee = self.add_account('quiz_manager', UserRole.MANAGER)
        self.as_user(manager.id)
        self.assertEqual(self.client.get('/api/academy/assignments').json['assignments'], [])
        worker, _ = self.add_account('quiz_unassigned')
        self.as_user(worker.id)
        self.assertEqual(self.client.get(self.quiz_url).status_code, 404)

    def test_html_quiz_submission_and_refresh(self):
        self.finish_lessons()
        url = f'/academy/courses/{self.course_id}/quiz'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        questions = db.session.scalars(db.select(QuizQuestion)).all()
        data = {'csrf_token':self.headers['X-CSRF-Token'], 'submission_id':secrets.token_hex(24)}
        data.update({'question_'+str(question.id):'0' for question in questions})
        response = self.client.post(url, data=data, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn('100%', response.get_data(as_text=True))
        self.client.get(url)
        self.assertEqual(db.session.query(QuizAttempt).count(), 1)
