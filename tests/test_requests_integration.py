import test_academy_integration as fixtures
from app.models import VacationRequest
from app.extensions import db

class RequestsTests(fixtures.AcademyIntegrationTests):
    def token(self, user):
        self.login(user)
        self.assertEqual(self.client.get('/account/requests').status_code, 200)
        with self.client.session_transaction() as session:
            return session['requests_csrf']

    def submit(self, user, **extra):
        data = dict(csrf_token=self.token(user), start_date='2026-12-01', end_date='2026-12-03', comment='Integration vacation')
        data.update(extra)
        return self.client.post('/account/requests', data=data, follow_redirects=True)

    def test_submit_render_and_approve(self):
        result = self.submit(self.worker)
        self.assertIn('Integration vacation', result.get_data(as_text=True))
        item = VacationRequest.query.one()
        self.assertEqual(item.days, 3)
        token = self.token(self.manager)
        result = self.client.post(f'/account/requests/{item.id}/approve', data={'csrf_token': token}, follow_redirects=True)
        self.assertEqual(result.status_code, 200)
        db.session.refresh(item)
        self.assertEqual(item.status, 'approved')
        self.client.post(f'/account/requests/{item.id}/reject', data={'csrf_token': token})
        db.session.refresh(item)
        self.assertEqual(item.status, 'approved')

    def test_scoped_visibility_and_review(self):
        self.submit(self.outside)
        item = VacationRequest.query.one()
        token = self.token(self.manager)
        self.assertNotIn('Integration vacation', self.client.get('/account/requests').get_data(as_text=True))
        self.assertEqual(self.client.post(f'/account/requests/{item.id}/approve', data={'csrf_token': token}).status_code, 403)
        token = self.token(self.hr)
        self.assertIn('Integration vacation', self.client.get('/account/requests').get_data(as_text=True))
        self.assertEqual(self.client.post(f'/account/requests/{item.id}/reject', data={'csrf_token': token}).status_code, 302)
        db.session.refresh(item)
        self.assertEqual(item.status, 'rejected')
        self.token(self.worker)
        self.assertNotIn('Integration vacation', self.client.get('/account/requests').get_data(as_text=True))

    def test_invalid_and_overlapping_requests(self):
        self.submit(self.worker, start_date='invalid')
        self.submit(self.worker, end_date='2026-11-01')
        self.submit(self.worker, request_type='certificate')
        self.assertEqual(VacationRequest.query.count(), 0)
        self.submit(self.worker)
        self.submit(self.worker)
        self.assertEqual(VacationRequest.query.count(), 1)
        self.submit(self.worker, start_date='2027-01-01', end_date='2027-03-01')
        self.assertEqual(VacationRequest.query.count(), 1)

    def test_mutations_require_csrf_and_employee_role(self):
        self.token(self.worker)
        self.assertEqual(self.client.post('/account/requests', data={}).status_code, 400)
        token = self.token(self.hr)
        self.assertEqual(self.client.post('/account/requests', data={'csrf_token': token}).status_code, 403)
        self.submit(self.worker)
        item = VacationRequest.query.one()
        self.token(self.hr)
        self.assertEqual(self.client.post(f'/account/requests/{item.id}/approve').status_code, 400)
