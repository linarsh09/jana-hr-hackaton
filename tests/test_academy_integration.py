"""Academy + current shared schema. External AI provider is isolated in these tests."""
import os
import secrets
import sys
import types
import unittest
from datetime import date
from unittest.mock import patch

from app import create_app
from app.extensions import db
from app.models import (Role, User, Department, Position, Employee, Course, Lesson,
                        CourseAssignment, LessonCompletion, QuizQuestion, QuizAttempt)


class AcademyIntegrationTests(unittest.TestCase):
    def setUp(self):
        provider = types.ModuleType('app.api.assistant.ai_helper')
        provider.ask_jana_ai = lambda *args, **kwargs: {'success': False, 'answer': 'External AI not exercised'}
        previous_provider = sys.modules.get('app.api.assistant.ai_helper')
        sys.modules['app.api.assistant.ai_helper'] = provider
        try:
            with patch.dict(os.environ, DATABASE_URL='sqlite:///:memory:', SECRET_KEY='integration-test-only'):
                self.app = create_app()
        finally:
            if previous_provider is None:
                sys.modules.pop('app.api.assistant.ai_helper', None)
            else:
                sys.modules['app.api.assistant.ai_helper'] = previous_provider
        self.app.config['TESTING'] = True
        self.ctx = self.app.app_context()
        self.ctx.push()
        db.create_all()
        self.roles = {name: Role(name=name) for name in ('hr', 'manager', 'employee')}
        self.department = Department(name='Test')
        self.position = Position(name='Test position')
        db.session.add_all([*self.roles.values(), self.department, self.position])
        db.session.flush()
        self.hr = self.account('hr', 'hr')
        self.manager = self.account('manager', 'manager')
        self.worker = self.account('worker', 'employee', self.manager.employee.id)
        self.outside = self.account('outside', 'employee')
        self.course = Course(title='Test course', description='Test material')
        self.course.lessons = [Lesson(title='First', content='A', position=1),
                               Lesson(title='Second', content='B', position=2)]
        db.session.add(self.course)
        db.session.commit()
        self.client = self.app.test_client()

    def account(self, name, role, manager_id=None):
        employee = Employee(first_name=name, last_name='Test', email=name+'@example.test',
            hire_date=date(2026, 1, 1), department=self.department, position=self.position,
            manager_id=manager_id, vacation_balance=24)
        user = User(username=name, role=self.roles[role], employee=employee)
        user.set_password('TestPassword123!')
        db.session.add(user)
        db.session.flush()
        return user

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        db.engine.dispose()
        self.ctx.pop()

    def login(self, user):
        with self.client.session_transaction() as session:
            session.clear()
            session['user_id'] = user.id
        token = self.client.get('/api/academy/csrf-token').json['csrf_token']
        return {'X-CSRF-Token': token}

    def assign(self, user, actor=None):
        headers = self.login(actor or self.hr)
        response = self.client.post('/api/academy/assignments', headers=headers,
            json={'course_id': self.course.id, 'employee_id': user.employee.id})
        self.assertEqual(response.status_code, 200, response.get_data(as_text=True))

    def test_menu_courses_redirects_to_live_academy(self):
        for user in (self.hr, self.manager, self.worker):
            self.login(user)
            page = self.client.get('/account/courses', follow_redirects=True)
            self.assertEqual(page.status_code, 200)
            self.assertEqual(page.request.path, '/academy/')
            self.assertEqual(self.client.get('/account/profile').status_code, 200)

    def test_hr_assigns_and_sees_employee_progress(self):
        self.assign(self.worker)
        headers = self.login(self.worker)
        self.assertEqual(len(self.client.get('/api/academy/courses').json['courses']), 1)
        lesson = self.course.lessons[0]
        self.assertEqual(self.client.get(f'/academy/courses/{self.course.id}/lessons/{lesson.id}').status_code, 200)
        for _ in range(2):
            result = self.client.post(f'/api/academy/lessons/{lesson.id}/complete', headers=headers)
            self.assertEqual(result.json['progress_percent'], 50)
        self.assertEqual(db.session.query(LessonCompletion).count(), 1)
        self.login(self.hr)
        report = self.client.get('/api/academy/assignments').json['assignments']
        self.assertEqual(report[0]['employee_id'], self.worker.employee.id)
        self.assertEqual(report[0]['progress_percent'], 50)
        self.assertEqual(self.client.get('/academy/').status_code, 200)

    def test_manager_only_assigns_direct_reports(self):
        headers = self.login(self.manager)
        targets = self.client.get('/api/academy/employees').json['employees']
        self.assertEqual([row['id'] for row in targets], [self.worker.employee.id])
        for target, status in [(self.worker, 200), (self.outside, 403)]:
            result = self.client.post('/api/academy/assignments', headers=headers,
                json={'course_id': self.course.id, 'employee_id': target.employee.id})
            self.assertEqual(result.status_code, status)
        self.assertEqual(self.client.get('/academy/').status_code, 200)

    def test_unassigned_and_anonymous_access_denied(self):
        self.assertEqual(self.client.get('/academy/').status_code, 302)
        self.assertEqual(self.client.get('/api/academy/courses').status_code, 401)
        headers = self.login(self.worker)
        self.assertEqual(self.client.get('/api/academy/courses').json['courses'], [])
        self.assertEqual(self.client.get(f'/academy/courses/{self.course.id}').status_code, 404)
        self.assertEqual(self.client.post(f'/api/academy/lessons/{self.course.lessons[0].id}/complete', headers=headers).status_code, 404)
        self.assertEqual(self.client.get('/api/academy/assignments').status_code, 403)

    def test_final_quiz_retries_and_hr_results(self):
        self.assign(self.worker)
        for i in range(5):
            db.session.add(QuizQuestion(course_id=self.course.id, position=i+1,
                text='Q'+str(i), options=['Correct', 'Wrong'], correct_option=0))
        db.session.commit()
        headers = self.login(self.worker)
        path = f'/api/academy/courses/{self.course.id}/quiz'
        self.assertEqual(self.client.get(path).status_code, 409)
        for lesson in self.course.lessons:
            self.client.post(f'/api/academy/lessons/{lesson.id}/complete', headers=headers)
        quiz = self.client.get(path).json
        self.assertNotIn('correct_option', str(quiz))
        answers = {str(q['id']): 0 if i < 4 else 1 for i, q in enumerate(quiz['questions'])}
        data = {'answers': answers, 'submission_id': quiz['submission_id']}
        for _ in range(2):
            result = self.client.post(path, headers=headers, json=data)
            self.assertEqual(result.status_code, 200)
            self.assertEqual(result.json['score_percent'], 80)
        self.assertEqual(db.session.query(QuizAttempt).count(), 1)
        self.assertEqual(self.client.get(f'/academy/courses/{self.course.id}/quiz').status_code, 200)
        self.login(self.hr)
        report = self.client.get('/api/academy/assignments').json['assignments'][0]
        self.assertEqual(report['status'], 'completed')
        self.assertTrue(report['quiz']['passed'])
        self.assertEqual(report['quiz']['best_score'], 80)
        self.assertEqual(self.client.get('/academy/').status_code, 200)

    def test_csrf_and_inactive_user(self):
        self.login(self.hr)
        self.assertEqual(self.client.post('/api/academy/assignments', json={}).status_code, 400)
        self.hr.is_active = False
        db.session.commit()
        self.assertEqual(self.client.get('/api/academy/assignments').status_code, 401)

    def test_existing_login_and_request_pages(self):
        result = self.client.post('/account/login', data={'username':'worker', 'password':'TestPassword123!'})
        self.assertEqual(result.status_code, 302)
        self.assertEqual(self.client.get('/account/requests').status_code, 200)
        self.assertEqual(self.client.get('/api/list').status_code, 200)


if __name__ == '__main__':
    unittest.main()
