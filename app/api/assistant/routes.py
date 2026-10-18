from flask import Blueprint, render_template, request, jsonify, session
from app.api.assistant.ai_helper import ask_jana_ai

assistant_bp = Blueprint('assistant', __name__, template_folder='../../templates/assistant')

@assistant_bp.route('/chat', methods=['GET', 'POST'])
def chat():
    if request.method == 'POST':
        data = request.get_json() or request.form
        user_query = data.get('query', '')
        
        if not user_query.strip():
            return jsonify({"success": False, "answer": "Пожалуйста, введите текст вопроса."}), 400
        
        # Получаем ID текущего пользователя из сессии
        user_id = session.get('user_id')
        
        # Передаем запрос и user_id в хелпер для ответа и логирования в БД
        response = ask_jana_ai(user_query, user_id=user_id)
        
        return jsonify(response)
    
    return render_template('assistant/chat.html')