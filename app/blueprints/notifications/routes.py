# app/blueprints/notifications/routes.py
"""
Роуты для управления уведомлениями
"""

from flask import request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from marshmallow import ValidationError

from app.blueprints.notifications import notifications_bp
from app.blueprints.notifications.services import NotificationService
from app.blueprints.notifications.schemas import (
    NotificationSchema, NotificationListSchema, NotificationSettingsSchema,
    SendNotificationSchema, NotificationTemplateSchema
)
from app.utils.decorators import admin_required, validate_json
from app.utils.pagination import paginate
from app.database import get_db


@notifications_bp.route('/', methods=['GET'])
@jwt_required()
def get_notifications():
    """Получение списка уведомлений пользователя"""
    try:
        user_id = get_jwt_identity()
        db = get_db()
        
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        status = request.args.get('status')
        notification_type = request.args.get('type')
        
        notifications = NotificationService.get_user_notifications(
            db, user_id, page, per_page, status, notification_type
        )
        
        schema = NotificationListSchema(many=True)
        
        return jsonify({
            'success': True,
            'data': {
                'notifications': schema.dump(notifications['items']),
                'pagination': {
                    'page': notifications['page'],
                    'per_page': notifications['per_page'],
                    'total': notifications['total'],
                    'pages': notifications['pages']
                }
            }
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting notifications: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@notifications_bp.route('/<int:notification_id>', methods=['GET'])
@jwt_required()
def get_notification(notification_id):
    """Получение конкретного уведомления"""
    try:
        user_id = get_jwt_identity()
        db = get_db()
        
        notification = NotificationService.get_notification(db, notification_id, user_id)
        if not notification:
            return jsonify({'error': 'Notification not found'}), 404
        
        schema = NotificationSchema()
        return jsonify({
            'success': True,
            'data': schema.dump(notification)
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting notification: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@notifications_bp.route('/<int:notification_id>/read', methods=['PUT'])
@jwt_required()
def mark_as_read(notification_id):
    """Отметить уведомление как прочитанное"""
    try:
        user_id = get_jwt_identity()
        db = get_db()
        
        success = NotificationService.mark_as_read(db, notification_id, user_id)
        if not success:
            return jsonify({'error': 'Notification not found'}), 404
        
        return jsonify({
            'success': True,
            'message': 'Notification marked as read'
        })
        
    except Exception as e:
        current_app.logger.error(f"Error marking notification as read: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@notifications_bp.route('/mark-all-read', methods=['PUT'])
@jwt_required()
def mark_all_as_read():
    """Отметить все уведомления как прочитанные"""
    try:
        user_id = get_jwt_identity()
        db = get_db()
        
        count = NotificationService.mark_all_as_read(db, user_id)
        
        return jsonify({
            'success': True,
            'message': f'Marked {count} notifications as read'
        })
        
    except Exception as e:
        current_app.logger.error(f"Error marking all notifications as read: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@notifications_bp.route('/unread-count', methods=['GET'])
@jwt_required()
def get_unread_count():
    """Получение количества непрочитанных уведомлений"""
    try:
        user_id = get_jwt_identity()
        db = get_db()
        
        count = NotificationService.get_unread_count(db, user_id)
        
        return jsonify({
            'success': True,
            'data': {'unread_count': count}
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting unread count: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@notifications_bp.route('/settings', methods=['GET'])
@jwt_required()
def get_notification_settings():
    """Получение настроек уведомлений пользователя"""
    try:
        user_id = get_jwt_identity()
        db = get_db()
        
        settings = NotificationService.get_notification_settings(db, user_id)
        schema = NotificationSettingsSchema(many=True)
        
        return jsonify({
            'success': True,
            'data': schema.dump(settings)
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting notification settings: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@notifications_bp.route('/settings', methods=['PUT'])
@jwt_required()
@validate_json
def update_notification_settings():
    """Обновление настроек уведомлений"""
    try:
        user_id = get_jwt_identity()
        db = get_db()
        
        schema = NotificationSettingsSchema(many=True)
        settings_data = schema.load(request.json)
        
        updated_settings = NotificationService.update_notification_settings(
            db, user_id, settings_data
        )
        
        return jsonify({
            'success': True,
            'message': 'Notification settings updated successfully',
            'data': schema.dump(updated_settings)
        })
        
    except ValidationError as e:
        return jsonify({'error': 'Validation error', 'details': e.messages}), 400
    except Exception as e:
        current_app.logger.error(f"Error updating notification settings: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@notifications_bp.route('/send', methods=['POST'])
@jwt_required()
@admin_required
@validate_json
def send_notification():
    """Отправка уведомления (только для админов)"""
    try:
        db = get_db()
        
        schema = SendNotificationSchema()
        data = schema.load(request.json)
        
        notification = NotificationService.send_notification(db, data)
        
        response_schema = NotificationSchema()
        return jsonify({
            'success': True,
            'message': 'Notification sent successfully',
            'data': response_schema.dump(notification)
        }), 201
        
    except ValidationError as e:
        return jsonify({'error': 'Validation error', 'details': e.messages}), 400
    except Exception as e:
        current_app.logger.error(f"Error sending notification: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@notifications_bp.route('/broadcast', methods=['POST'])
@jwt_required()
@admin_required
@validate_json
def broadcast_notification():
    """Массовая отправка уведомлений"""
    try:
        db = get_db()
        
        title = request.json.get('title', '')
        message = request.json.get('message', '')
        notification_type = request.json.get('type', 'system')
        user_filter = request.json.get('user_filter', {})
        
        count = NotificationService.broadcast_notification(
            db, title, message, notification_type, user_filter
        )
        
        return jsonify({
            'success': True,
            'message': f'Notification sent to {count} users'
        })
        
    except Exception as e:
        current_app.logger.error(f"Error broadcasting notification: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@notifications_bp.route('/templates', methods=['GET'])
@jwt_required()
@admin_required
def get_notification_templates():
    """Получение шаблонов уведомлений"""
    try:
        db = get_db()
        
        templates = NotificationService.get_notification_templates(db)
        schema = NotificationTemplateSchema(many=True)
        
        return jsonify({
            'success': True,
            'data': schema.dump(templates)
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting notification templates: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@notifications_bp.route('/test-push', methods=['POST'])
@jwt_required()
def test_push_notification():
    """Тестовая отправка push-уведомления"""
    try:
        user_id = get_jwt_identity()
        db = get_db()
        
        success = NotificationService.send_test_push(db, user_id)
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Test push notification sent'
            })
        else:
            return jsonify({
                'success': False,
                'message': 'No active devices found for push notifications'
            }), 400
        
    except Exception as e:
        current_app.logger.error(f"Error sending test push: {e}")
        return jsonify({'error': 'Internal server error'}), 500
