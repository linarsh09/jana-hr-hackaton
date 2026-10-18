from unittest.mock import patch

import test_academy_integration as fixtures


class AssistantTests(fixtures.AcademyIntegrationTests):
    def test_chat_requires_login(self):
        self.assertEqual(self.client.get('/chat').status_code, 302)
        self.assertEqual(self.client.post('/chat', json={'query': 'Hi'}).status_code, 302)

    def test_chat_renders_and_calls_existing_helper(self):
        self.login(self.worker)
        page = self.client.get('/chat')
        self.assertEqual(page.status_code, 200)
        self.assertIn('aiChatForm', page.get_data(as_text=True))
        self.assertIn('bubble.textContent = text', page.get_data(as_text=True))
        with self.client.session_transaction() as session:
            token = session['assistant_csrf']
        with patch('app.api.assistant.routes.ask_jana_ai', return_value={
            'answer': 'Test answer', 'success': True
        }) as helper:
            result = self.client.post('/chat', json={'query': 'Question'},
                                      headers={'X-CSRF-Token': token})
            self.assertEqual(result.json['answer'], 'Test answer')
            helper.assert_called_once_with('Question', user_id=self.worker.id)

    def test_chat_rejects_invalid_input_and_csrf(self):
        self.login(self.worker)
        self.client.get('/chat')
        self.assertEqual(self.client.post('/chat', json={'query': 'Hi'}).status_code, 400)
        with self.client.session_transaction() as session:
            headers = {'X-CSRF-Token': session['assistant_csrf']}
        with patch('app.api.assistant.routes.ask_jana_ai') as helper:
            for data in ({'query': ''}, {'query': 123}, {'query': 'x' * 4001}, []):
                self.assertEqual(self.client.post('/chat', json=data, headers=headers).status_code, 400)
            helper.assert_not_called()
