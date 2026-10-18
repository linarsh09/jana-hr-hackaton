import secrets
from hmac import compare_digest
from flask import Blueprint, render_template, request, jsonify, session
from app.core.permissions import login_required
from app.api.assistant.ai_helper import ask_jana_ai

assistant_bp = Blueprint('assistant', __name__, template_folder='../../templates/assistant')

@assistant_bp.route('/chat', methods=['GET', 'POST'])
@login_required
def chat():
    if request.method == 'POST':
        token = session.get('assistant_csrf', '')
        if not token or not compare_digest(token, request.headers.get('X-CSRF-Token', '')):
            return jsonify(success=False, answer='Обновите страницу и повторите запрос.'), 400
        data = request.get_json(silent=True) if request.is_json else request.form
        if not isinstance(data, dict) and not hasattr(data, 'get'):
            return jsonify(success=False, answer='Некорректный запрос.'), 400
        user_query = data.get('query', '')
        
        if not isinstance(user_query, str) or not user_query.strip():
            return jsonify({"success": False, "answer": "Пожалуйста, введите текст вопроса."}), 400
        
        if len(user_query) > 4000:
            return jsonify(success=False, answer='Вопрос должен содержать не более 4000 символов.'), 400

        # Получаем ID текущего пользователя из сессии
        user_id = session.get('user_id')
        
        # Передаем запрос и user_id в хелпер для ответа и логирования в БД
        response = ask_jana_ai(user_query, user_id=user_id)
        
        return jsonify(response)
    
    token = session.setdefault('assistant_csrf', secrets.token_hex(32))
    return render_template('assistant/chat.html', csrf_token=token)
