from flask import Blueprint, jsonify, session
from app.api.notifications.notification_helper import (
    get_user_notifications, 
    mark_all_as_read, 
    get_unread_count
)

notifications_bp = Blueprint('notifications', __name__)

@notifications_bp.route('/api/list', methods=['GET'])
def list_notifications():
    # Получаем id текущего пользователя из сессии (согласно общей архитектуре проекта)
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"success": False, "notifications": [], "unread_count": 0}), 401
    
    notifs = get_user_notifications(user_id)
    unread = get_unread_count(user_id)
    
    # Сериализуем объекты SQLAlchemy в словари для JSON
    notifs_data = [{
        "id": n.id,
        "message": n.message,
        "is_read": n.is_read,
        "created_at": n.created_at.strftime("%Y-%m-%d %H:%M") if n.created_at else ""
    } for n in notifs]
    
    return jsonify({
        "success": True,
        "notifications": notifs_data,
        "unread_count": unread
    })

@notifications_bp.route('/api/read-all', methods=['POST'])
def read_all():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"success": False}), 401
        
    mark_all_as_read(user_id)
    return jsonify({"success": True})