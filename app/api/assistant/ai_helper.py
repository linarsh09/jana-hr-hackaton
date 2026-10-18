import os
from google import genai
from google.genai import types
from dotenv import load_dotenv

from app.extensions import db
from app.models import KnowledgeArticle, AIChatLog, AIFallbackLog

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
MODEL_NAME = os.getenv("MODEL_NAME", "gemini-3.1-flash-lite")
GEMINI_TEMPERATURE = float(os.getenv("GEMINI_TEMPERATURE", 0.3))
MAX_OUTPUT_TOKENS = int(os.getenv("MAX_OUTPUT_TOKENS", 500))

client = genai.Client(api_key=GEMINI_API_KEY)

FALLBACK_MESSAGE = os.getenv("FALLBACK_MESSAGE") or "К сожалению, в доступной мне информации нет ответа по вашему вопросу. Пожалуйста, обратитесь напрямую в HR-департамент."

def load_kb_from_db():
    """Загружает актуальные статьи базы знаний из базы данных"""
    try:
        articles = KnowledgeArticle.query.all()
        return [
            {
                "title": art.title,
                "content": art.content,
                "category": art.category.name if art.category else "Общие"
            }
            for art in articles
        ]
    except Exception as e:
        print(f"Ошибка загрузки базы знаний из БД: {e}")
        return []

def ask_jana_ai(user_query, user_id=None):
    """
    Отправляет вопрос сотрудника в Gemini, опираясь на статьи базы знаний из БД.
    Логирует успешные ответы и эскалации при отсутствии информации.
    """
    clean_query = user_query.strip()
    if not clean_query:
        return {"answer": "Пожалуйста, введите корректный вопрос.", "success": False, "fallback": False}

    # Загружаем базу знаний
    kb_documents = load_kb_from_db()
    
    if not kb_documents:
        kb_text = "База знаний компании временно пуста."
    else:
        kb_text = "\n\n".join([
            f"Источник (Категория: {doc['category']} | Документ: {doc['title']}):\n{doc['content']}"
            for doc in kb_documents
        ])
    
    system_instruction = f"""
Ты — корпоративный HR-ассистент AI Jana. Отвечай на вопросы сотрудников строго и профессионально.
Используй информацию ТОЛЬКО из приведенной ниже базы знаний компании.
Если ответа на вопрос нет в базе знаний или вопрос не относится к внутренним кадровым процедурам компании, ты обязан ответить СТРОГО этой фразой:
"{FALLBACK_MESSAGE}"
Ни в коем случае не выдумывай правила и не генерируй ответы от себя. Если сработала фраза-заглушка выше, источник не указывать.
Если ответ найден, в самом конце ответа укажи точный источник (название статьи/документа).
Запрещено разглашать персональные данные.

БАЗА ЗНАНИЙ КОМПАНИИ:
{kb_text}
"""

    try:
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=user_query,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=GEMINI_TEMPERATURE,
                max_output_tokens=MAX_OUTPUT_TOKENS,
            ),
        )
        answer_text = response.text.strip()
        
        # Определяем, ушел ли вопрос в заглушку (галлюцинация предотвращена)
        triggered_fallback = FALLBACK_MESSAGE in answer_text

        # Сохранение логов в базу данных (если передан идентификатор пользователя)
        if user_id:
            try:
                chat_log = AIChatLog(
                    user_id=user_id,
                    query=clean_query,
                    response=answer_text,
                    triggered_fallback=triggered_fallback
                )
                db.session.add(chat_log)

                # Если ИИ не нашел ответ, фиксируем эскалацию для HR-админки
                if triggered_fallback:
                    fallback_log = AIFallbackLog(
                        user_id=user_id,
                        unanswered_query=clean_query,
                        status="pending"
                    )
                    db.session.add(fallback_log)

                db.session.commit()
            except Exception as db_err:
                db.session.rollback()
                print(f"Ошибка при сохранении лога ИИ в БД: {db_err}")

        return {
            "answer": answer_text,
            "success": True,
            "fallback": triggered_fallback
        }
        
    except Exception as e:
        print(f"Ошибка при вызове Gemini API: {e}")
        return {
            "answer": "К сожалению, сервис ИИ временно недоступен. Пожалуйста, обратитесь в HR-департамент.",
            "success": False,
            "fallback": True
        }
