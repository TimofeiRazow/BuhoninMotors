# app/blueprints/notifications/services.py
"""
Сервисы для работы с уведомлениями
"""

from datetime import datetime, timedelta
from sqlalchemy import and_, or_, func
from sqlalchemy.orm import joinedload

from app.models.notification import (
    Notification, NotificationChannel, NotificationTemplate,
    UserNotificationSettings
)
from app.models.user import User, DeviceRegistration
from app.blueprints.notifications.push import PushNotificationService
from app.utils.pagination import paginate_query
from app.tasks.notifications import send_notification_task


class NotificationService:
    """Сервис для работы с уведомлениями"""
    
    @staticmethod
    def get_user_notifications(db, user_id, page=1, per_page=20, status=None, notification_type=None):
        """Получение уведомлений пользователя"""
        query = db.query(Notification).filter(
            Notification.user_id == user_id
        )
        
        if status:
            query = query.filter(Notification.status == status)
        
        if notification_type:
            query = query.filter(Notification.notification_type == notification_type)
        
        query = query.order_by(Notification.scheduled_date.desc())
        
        return paginate_query(query, page, per_page)
    
    @staticmethod
    def get_notification(db, notification_id, user_id):
        """Получение конкретного уведомления"""
        notification = db.query(Notification).filter(
            Notification.notification_id == notification_id,
            Notification.user_id == user_id
        ).first()
        
        if notification and notification.status == 'sent' and not notification.opened_date:
            notification.status = 'opened'
            notification.opened_date = datetime.utcnow()
            db.commit()
        
        return notification
    
    @staticmethod
    def mark_as_read(db, notification_id, user_id):
        """Отметить уведомление как прочитанное"""
        notification = db.query(Notification).filter(
            Notification.notification_id == notification_id,
            Notification.user_id == user_id
        ).first()
        
        if not notification:
            return False
        
        notification.status = 'opened'
        notification.opened_date = datetime.utcnow()
        db.commit()
        return True
    
    @staticmethod
    def mark_all_as_read(db, user_id):
        """Отметить все уведомления как прочитанные"""
        count = db.query(Notification).filter(
            Notification.user_id == user_id,
            Notification.status.in_(['sent', 'delivered'])
        ).update({
            'status': 'opened',
            'opened_date': datetime.utcnow()
        })
        
        db.commit()
        return count
    
    @staticmethod
    def get_unread_count(db, user_id):
        """Получение количества непрочитанных уведомлений"""
        return db.query(Notification).filter(
            Notification.user_id == user_id,
            Notification.status.in_(['sent', 'delivered'])
        ).count()
    
    @staticmethod
    def get_notification_settings(db, user_id):
        """Получение настроек уведомлений пользователя"""
        settings = db.query(UserNotificationSettings).options(
            joinedload(UserNotificationSettings.channel)
        ).filter(
            UserNotificationSettings.user_id == user_id
        ).all()
        
        # Если настроек нет, создаем базовые
        if not settings:
            settings = NotificationService._create_default_settings(db, user_id)
        
        return settings
    
    @staticmethod
    def _create_default_settings(db, user_id):
        """Создание настроек уведомлений по умолчанию"""
        channels = db.query(NotificationChannel).all()
        settings = []
        
        default_types = [
            'message_received', 'listing_responded', 'listing_expired',
            'payment_received', 'system_notification'
        ]
        
        for channel in channels:
            for notification_type in default_types:
                setting = UserNotificationSettings(
                    user_id=user_id,
                    channel_id=channel.channel_id,
                    notification_type=notification_type,
                    is_enabled=True,
                    frequency='instant'
                )
                settings.append(setting)
                db.add(setting)
        
        db.commit()
        return settings
    
    @staticmethod
    def update_notification_settings(db, user_id, settings_data):
        """Обновление настроек уведомлений"""
        # Удаляем старые настройки
        db.query(UserNotificationSettings).filter(
            UserNotificationSettings.user_id == user_id
        ).delete()
        
        # Создаем новые настройки
        updated_settings = []
        for setting_data in settings_data:
            setting = UserNotificationSettings(
                user_id=user_id,
                **setting_data
            )
            updated_settings.append(setting)
            db.add(setting)
        
        db.commit()
        return updated_settings
    
    @staticmethod
    def send_notification(db, data):
        """Отправка уведомления"""
        notification = Notification(
            user_id=data['user_id'],
            channel_id=data['channel_id'],
            template_id=data.get('template_id'),
            title=data['title'],
            message=data['message'],
            notification_type=data['notification_type'],
            related_entity_id=data.get('related_entity_id'),
            template_data=data.get('template_data', {}),
            scheduled_date=data.get('scheduled_date', datetime.utcnow())
        )
        
        db.add(notification)
        db.commit()
        
        # Отправляем уведомление в фоновой задаче
        send_notification_task.delay(notification.notification_id)
        
        return notification
    
    @staticmethod
    def broadcast_notification(db, title, message, notification_type, user_filter=None):
        """Массовая отправка уведомлений"""
        # Получаем список пользователей для отправки
        query = db.query(User).filter(User.is_active == True)
        
        if user_filter:
            if 'user_type' in user_filter:
                query = query.filter(User.user_type == user_filter['user_type'])
            if 'city_id' in user_filter:
                query = query.join(User.profile).filter(
                    User.profile.city_id == user_filter['city_id']
                )
        
        users = query.all()
        
        # Получаем канал push-уведомлений
        push_channel = db.query(NotificationChannel).filter(
            NotificationChannel.channel_code == 'push'
        ).first()
        
        count = 0
        for user in users:
            # Проверяем настройки пользователя
            if NotificationService._should_send_notification(
                db, user.user_id, push_channel.channel_id, notification_type
            ):
                notification = Notification(
                    user_id=user.user_id,
                    channel_id=push_channel.channel_id,
                    title=title,
                    message=message,
                    notification_type=notification_type
                )
                db.add(notification)
                count += 1
        
        db.commit()
        return count
    
    @staticmethod
    def _should_send_notification(db, user_id, channel_id, notification_type):
        """Проверка, нужно ли отправлять уведомление"""
        setting = db.query(UserNotificationSettings).filter(
            UserNotificationSettings.user_id == user_id,
            UserNotificationSettings.channel_id == channel_id,
            UserNotificationSettings.notification_type == notification_type
        ).first()
        
        return setting and setting.is_enabled
    
    @staticmethod
    def get_notification_templates(db):
        """Получение шаблонов уведомлений"""
        return db.query(NotificationTemplate).options(
            joinedload(NotificationTemplate.channel)
        ).filter(NotificationTemplate.is_active == True).all()
    
    @staticmethod
    def send_test_push(db, user_id):
        """Отправка тестового push-уведомления"""
        devices = db.query(DeviceRegistration).filter(
            DeviceRegistration.user_id == user_id,
            DeviceRegistration.is_active == True
        ).all()
        
        if not devices:
            return False
        
        # Получаем канал push-уведомлений
        push_channel = db.query(NotificationChannel).filter(
            NotificationChannel.channel_code == 'push'
        ).first()
        
        notification = Notification(
            user_id=user_id,
            channel_id=push_channel.channel_id,
            title='Тестовое уведомление',
            message='Это тестовое push-уведомление от Kolesa.kz',
            notification_type='test'
        )
        
        db.add(notification)
        db.commit()
        
        # Отправляем push-уведомление
        for device in devices:
            PushNotificationService.send_push(
                device.device_token,
                device.device_type,
                notification.title,
                notification.message
            )
        
        notification.status = 'sent'
        notification.sent_date = datetime.utcnow()
        db.commit()
        
        return True





