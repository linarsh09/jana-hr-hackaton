import os
import unittest
import importlib.util
from pathlib import Path
from unittest.mock import patch
from datetime import date

from app import create_app
from app.extensions import db
from app.models import User, Employee, Department, UserRole
from app.api.academy.models import Course, Lesson, LessonCompletion, CourseAssignment


class AcademyCatalogTests(unittest.TestCase):
    def setUp(self):
        with patch.dict(os.environ, {"DATABASE_URL": "sqlite:///:memory:", "SECRET_KEY": "test-only"}):
            self.app = create_app()
        self.app.config["TESTING"] = True
        self.context = self.app.app_context()
        self.context.push()
        db.create_all()
        user = User(username="learner", password_hash="unused")
        course = Course(title="Introduction", description="First course")
        course.lessons = [Lesson(title="Second", content="B", position=2),
                          Lesson(title="First", content="A", position=1)]
        db.session.add_all([user, course])
        db.session.commit()
        department = Department(name='Test department')
        employee = Employee(first_name='Test', last_name='Learner', email='learner@example.test',
                            position='Test', hire_date=date(2026, 1, 1), department=department, user=user)
        db.session.add(employee)
        db.session.flush()
        db.session.add(CourseAssignment(employee_id=employee.id, course_id=course.id, assigned_by=user.id))
        db.session.commit()
        self.employee_id = employee.id
        self.user_id = user.id
        self.course_id = course.id
        self.lesson_id = course.lessons[0].id
        self.client = self.app.test_client()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        db.engine.dispose()
        self.context.pop()

    def login(self):
        with self.client.session_transaction() as session:
            session["user_id"] = self.user_id

    def test_anonymous_requests_return_json_401(self):
        for path in ["/courses", "/courses/1", "/courses/1/lessons/1"]:
            response = self.client.get("/api/academy" + path)
            self.assertEqual(response.status_code, 401)
            self.assertEqual(response.json, {"error": "authentication_required"})

    def test_catalog_and_ordered_lessons(self):
        self.login()
        self.assertEqual(len(self.client.get("/api/academy/courses").json["courses"]), 1)
        response = self.client.get(f"/api/academy/courses/{self.course_id}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual([lesson["position"] for lesson in response.json["lessons"]], [1, 2])
        lesson = self.client.get(f"/api/academy/courses/{self.course_id}/lessons/{self.lesson_id}")
        self.assertEqual(lesson.json["content"], "A")

    def test_missing_course_and_mismatched_lesson(self):
        self.login()
        self.assertEqual(self.client.get("/api/academy/courses/999").status_code, 404)
        self.assertEqual(self.client.get(f"/api/academy/courses/999/lessons/{self.lesson_id}").status_code, 404)

    def test_inactive_user_is_denied(self):
        self.login()
        db.session.get(User, self.user_id).is_active = False
        db.session.commit()
        self.assertEqual(self.client.get("/api/academy/courses").status_code, 401)

    def test_pages_and_saved_completion(self):
        self.login()
        response = self.client.get('/account/courses', follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        with self.client.session_transaction() as session:
            token = session['academy_csrf']
        path = f'/academy/lessons/{self.lesson_id}/complete'
        self.assertEqual(self.client.post(path).status_code, 400)
        for _ in range(2):
            response = self.client.post(path, data={'csrf_token': token}, follow_redirects=True)
            self.assertEqual(response.status_code, 200)
        self.assertEqual(db.session.query(LessonCompletion).count(), 1)
        self.assertIn('width:50%', response.get_data(as_text=True))
        other = User(username='other', password_hash='unused')
        db.session.add(other)
        db.session.commit()
        with self.client.session_transaction() as session:
            session['user_id'] = other.id
        page = self.client.get(f'/academy/courses/{self.course_id}')
        self.assertEqual(page.status_code, 404)

    def test_page_auth_and_course_lesson_scope(self):
        self.assertEqual(self.client.get('/academy/').status_code, 302)
        self.login()
        self.assertEqual(self.client.get(f'/academy/courses/999/lessons/{self.lesson_id}').status_code, 404)

    def add_account(self, name, role=UserRole.EMPLOYEE, manager_id=None):
        account = User(username=name, password_hash='unused', role=role)
        employee = Employee(first_name=name, last_name='Person', email=name+'@example.test',
                            position='Test', hire_date=date(2026, 1, 1),
                            department_id=db.session.get(Employee, self.employee_id).department_id,
                            user=account, manager_id=manager_id)
        db.session.add(employee)
        db.session.commit()
        return account, employee

    def as_user(self, account_id):
        with self.client.session_transaction() as session:
            session.clear()
            session['user_id'] = account_id
        response = self.client.get('/api/academy/csrf-token')
        return {'X-CSRF-Token': response.json['csrf_token']}

    def test_unassigned_employee_blocked_on_all_entry_points(self):
        account, employee = self.add_account('unassigned')
        headers = self.as_user(account.id)
        self.assertEqual(self.client.get('/api/academy/courses').json, {'courses': []})
        for path in [f'/api/academy/courses/{self.course_id}',
                     f'/api/academy/courses/{self.course_id}/lessons/{self.lesson_id}',
                     f'/api/academy/courses/{self.course_id}/progress',
                     f'/academy/courses/{self.course_id}']:
            self.assertEqual(self.client.get(path).status_code, 404, path)
        self.assertEqual(self.client.post(f'/api/academy/lessons/{self.lesson_id}/complete', headers=headers).status_code, 404)
        self.assertEqual(self.client.get('/api/academy/assignments').status_code, 403)
        self.assertEqual(self.client.post('/api/academy/assignments', headers=headers,
            json={'employee_id':employee.id,'course_id':self.course_id}).status_code, 403)

    def test_hr_assignment_enables_employee_and_repeat_preserves_progress(self):
        hr, _ = self.add_account('hr', UserRole.HR)
        account, employee = self.add_account('new_worker')
        headers = self.as_user(hr.id)
        data = {'employee_id':employee.id, 'course_id':self.course_id}
        self.assertEqual(self.client.post('/api/academy/assignments', json=data).status_code, 400)
        self.assertEqual(self.client.post('/api/academy/assignments', json=data, headers=headers).status_code, 200)
        self.assertEqual(self.client.get('/academy/').status_code, 200)
        headers_worker = self.as_user(account.id)
        for lesson in db.session.get(Course, self.course_id).lessons:
            response = self.client.post(f'/api/academy/lessons/{lesson.id}/complete', headers=headers_worker)
            self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json['status'], 'completed')
        self.assertEqual(response.json['progress_percent'], 100)
        self.assertEqual(self.client.get(f'/api/academy/courses/{self.course_id}/progress').json['completed_lessons'], 2)
        headers = self.as_user(hr.id)
        self.client.post('/api/academy/assignments', json=data, headers=headers)
        self.assertEqual(db.session.query(CourseAssignment).filter_by(employee_id=employee.id).count(), 1)
        report = self.client.get('/api/academy/assignments').json['assignments']
        self.assertEqual(next(row for row in report if row['employee_id']==employee.id)['progress_percent'], 100)
        self.assertEqual(self.client.post(f'/api/academy/lessons/{self.lesson_id}/complete', headers=headers).status_code, 403)

    def test_manager_scope_in_lists_assignment_and_report(self):
        manager, manager_employee = self.add_account('manager', UserRole.MANAGER)
        subordinate, subordinate_employee = self.add_account('subordinate', manager_id=manager_employee.id)
        outsider, outsider_employee = self.add_account('outsider')
        headers = self.as_user(manager.id)
        employees = self.client.get('/api/academy/employees').json['employees']
        self.assertEqual([row['id'] for row in employees], [subordinate_employee.id])
        for employee_id, expected in [(outsider_employee.id, 403), (subordinate_employee.id, 200)]:
            response = self.client.post('/api/academy/assignments', headers=headers,
                json={'employee_id':employee_id, 'course_id':self.course_id})
            self.assertEqual(response.status_code, expected)
        report = self.client.get('/api/academy/assignments').json['assignments']
        self.assertEqual([row['employee_id'] for row in report], [subordinate_employee.id])
        page = self.client.get('/academy/').get_data(as_text=True)
        self.assertIn('subordinate Person', page)
        self.assertNotIn('outsider Person', page)

    def test_assignment_validation_and_inactive_target(self):
        hr, hr_employee = self.add_account('hr', UserRole.HR)
        headers = self.as_user(hr.id)
        for data in [None, [], {}, {'employee_id':True,'course_id':1},
                     {'employee_id':'1','course_id':1}, {'employee_id':1,'course_id':0}]:
            self.assertEqual(self.client.post('/api/academy/assignments', json=data, headers=headers).status_code, 400)
        self.assertEqual(self.client.post('/api/academy/assignments', headers=headers,
            json={'employee_id':hr_employee.id,'course_id':self.course_id}).status_code, 400)
        db.session.get(User, self.user_id).is_active = False
        db.session.commit()
        self.assertEqual(self.client.post('/api/academy/assignments', headers=headers,
            json={'employee_id':self.employee_id,'course_id':self.course_id}).status_code, 400)

    def test_empty_course_is_not_completed(self):
        empty = Course(title='Empty')
        db.session.add(empty)
        db.session.flush()
        db.session.add(CourseAssignment(employee_id=self.employee_id, course_id=empty.id, assigned_by=self.user_id))
        db.session.commit()
        self.login()
        response = self.client.get(f'/api/academy/courses/{empty.id}/progress')
        self.assertEqual(response.json['progress_percent'], 0)
        self.assertEqual(response.json['status'], 'not_started')

    def test_html_assignment_flow(self):
        hr, _ = self.add_account('hr', UserRole.HR)
        account, employee = self.add_account('target')
        headers = self.as_user(hr.id)
        response = self.client.post('/academy/assignments', data={
            'employee_id':employee.id, 'course_id':self.course_id,
            'csrf_token':headers['X-CSRF-Token']}, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn('target Person', response.get_data(as_text=True))
        self.as_user(account.id)
        self.assertEqual(self.client.get(f'/academy/courses/{self.course_id}').status_code, 200)

    def test_academy_migrations_upgrade_and_downgrade(self):
        from sqlalchemy import create_engine, inspect
        from alembic.migration import MigrationContext
        from alembic.operations import Operations
        engine = create_engine('sqlite:///:memory:')
        try:
            base_tables = [table for name, table in db.metadata.tables.items() if not name.startswith('academy_')]
            db.metadata.create_all(engine, tables=base_tables)
            modules = []
            for filename in ['a10c20261017_academy_catalog.py', 'a11c20261017_academy_completion.py',
                             'a12c20261017_academy_assignments.py', 'a13c20261017_academy_quizzes.py']:
                path = Path(__file__).resolve().parents[1] / 'migrations' / 'versions' / filename
                spec = importlib.util.spec_from_file_location(filename[:-3], path)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                modules.append(module)
            with engine.begin() as connection:
                with Operations.context(MigrationContext.configure(connection)):
                    for module in modules:
                        module.upgrade()
                    inspector = inspect(connection)
                    for name, table in db.metadata.tables.items():
                        if name.startswith('academy_'):
                            self.assertEqual({column['name'] for column in inspector.get_columns(name)}, set(table.columns.keys()))
                    for module in reversed(modules):
                        module.downgrade()
                    self.assertNotIn('academy_courses', inspect(connection).get_table_names())
                    self.assertIn('users', inspect(connection).get_table_names())
        finally:
            engine.dispose()


if __name__ == "__main__":
    unittest.main()
