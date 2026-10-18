from app.extensions import db
from app.models import Notification

def get_user_notifications(user_id):
    """Возвращает отсортированные уведомления пользователя из базы данных (сначала непрочитанные)"""
    return Notification.query.filter_by(user_id=user_id)\
        .order_by(Notification.is_read.asc(), Notification.created_at.desc())\
        .all()

def add_notification(user_id, message):
    """Универсальная функция для добавления уведомления в базу данных"""
    try:
        new_notif = Notification(
            user_id=user_id,
            message=message,
            is_read=False
        )
        db.session.add(new_notif)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        print(f"Ошибка при создании уведомления: {e}")

def mark_all_as_read(user_id):
    """Помечает все уведомления конкретного пользователя как прочитанные в БД"""
    try:
        Notification.query.filter_by(user_id=user_id, is_read=False).update({"is_read": True})
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        print(f"Ошибка при обновлении статуса уведомлений: {e}")

def get_unread_count(user_id):
    """Возвращает количество непрочитанных уведомлений для бейджа в шапке"""
    return Notification.query.filter_by(user_id=user_id, is_read=False).count()