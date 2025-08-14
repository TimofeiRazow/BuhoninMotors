# app/tasks/notifications.py
"""
Задачи для отправки уведомлений
"""

from celery import Celery
from flask import current_app
from app.extensions import db
from app.models.user import User, DeviceRegistration
from app.models.notification import Notification, NotificationTemplate
import requests
import json


celery = Celery('kolesa_notifications')


@celery.task(bind=True, max_retries=3)
def send_push_notification(self, user_id, title, message, data=None):
    """
    Отправка push-уведомления
    
    Args:
        user_id: ID пользователя
        title: Заголовок уведомления
        message: Текст уведомления
        data: Дополнительные данные
    """
    try:
        user = User.query.get(user_id)
        if not user:
            return {'error': 'User not found'}
        
        # Получаем устройства пользователя
        devices = DeviceRegistration.get_user_devices(user_id)
        
        results = []
        for device in devices:
            if device.device_type == 'ios':
                result = send_apns_notification(device.device_token, title, message, data)
            elif device.device_type == 'android':
                result = send_fcm_notification(device.device_token, title, message, data)
            else:
                continue
            
            results.append({
                'device_id': device.device_id,
                'device_type': device.device_type,
                'result': result
            })
        
        return {'sent_to_devices': len(results), 'results': results}
        
    except Exception as exc:
        # Повторяем задачу с экспоненциальной задержкой
        self.retry(countdown=60 * (2 ** self.request.retries), exc=exc)


def send_fcm_notification(device_token, title, message, data=None):
    """Отправка FCM уведомления для Android"""
    fcm_url = "https://fcm.googleapis.com/fcm/send"
    
    headers = {
        'Authorization': f'key={current_app.config["FCM_SERVER_KEY"]}',
        'Content-Type': 'application/json'
    }
    
    payload = {
        'to': device_token,
        'notification': {
            'title': title,
            'body': message,
            'icon': 'ic_notification',
            'sound': 'default'
        },
        'data': data or {}
    }
    
    try:
        response = requests.post(fcm_url, headers=headers, json=payload)
        return {
            'success': response.status_code == 200,
            'response': response.json() if response.status_code == 200 else response.text
        }
    except Exception as e:
        return {'success': False, 'error': str(e)}


def send_apns_notification(device_token, title, message, data=None):
    """Отправка APNS уведомления для iOS"""
    # Здесь должна быть интеграция с APNS
    # Для примера возвращаем успешный результат
    return {'success': True, 'message': 'APNS integration not implemented'}


@celery.task(bind=True, max_retries=3)
def send_email_notification(self, user_id, template_code, template_data=None):
    """
    Отправка email уведомления
    
    Args:
        user_id: ID пользователя
        template_code: Код шаблона
        template_data: Данные для шаблона
    """
    try:
        from flask_mail import Message
        from app.extensions import mail
        
        user = User.query.get(user_id)
        if not user or not user.email:
            return {'error': 'User not found or no email'}
        
        # Получаем шаблон
        template = NotificationTemplate.query.filter_by(
            template_code=template_code,
            channel_id=2  # email channel
        ).first()
        
        if not template:
            return {'error': 'Template not found'}
        
        # Рендерим шаблон
        subject = template.render_subject(template_data or {})
        body = template.render_body(template_data or {})
        
        # Отправляем email
        msg = Message(
            subject=subject,
            recipients=[user.email],
            html=body,
            sender=current_app.config['MAIL_DEFAULT_SENDER']
        )
        
        mail.send(msg)
        
        return {'success': True, 'email': user.email}
        
    except Exception as exc:
        self.retry(countdown=60 * (2 ** self.request.retries), exc=exc)


@celery.task(bind=True, max_retries=3)
def send_sms_notification(self, user_id, message_text):
    """
    Отправка SMS уведомления
    
    Args:
        user_id: ID пользователя
        message_text: Текст сообщения
    """
    try:
        user = User.query.get(user_id)
        if not user:
            return {'error': 'User not found'}
        
        # Здесь должна быть интеграция с SMS провайдером (SMSC, Twilio, etc.)
        # Для примера возвращаем успешный результат
        
        return {
            'success': True,
            'phone': user.phone_number,
            'message': 'SMS integration not implemented'
        }
        
    except Exception as exc:
        self.retry(countdown=60 * (2 ** self.request.retries), exc=exc)


@celery.task
def send_bulk_notifications(user_ids, notification_type, template_code, template_data=None):
    """
    Массовая отправка уведомлений
    
    Args:
        user_ids: Список ID пользователей
        notification_type: Тип уведомления (push, email, sms)
        template_code: Код шаблона
        template_data: Данные для шаблона
    """
    results = []
    
    for user_id in user_ids:
        if notification_type == 'push':
            result = send_push_notification.delay(
                user_id, 
                template_data.get('title', ''), 
                template_data.get('message', ''),
                template_data.get('data', {})
            )
        elif notification_type == 'email':
            result = send_email_notification.delay(user_id, template_code, template_data)
        elif notification_type == 'sms':
            result = send_sms_notification.delay(user_id, template_data.get('message', ''))
        
        results.append({'user_id': user_id, 'task_id': result.id})
    
    return {'sent_to_users': len(results), 'task_results': results}


@celery.task(bind=True, max_retries=3)
def send_notification_task(self, notification_id):
    """Отправка уведомления"""
    session = get_db_session()
    
    try:
        notification = session.query(Notification).filter(
            Notification.notification_id == notification_id
        ).first()
        
        if not notification:
            logger.error(f"Notification {notification_id} not found")
            return False
        
        if notification.status != 'pending':
            logger.info(f"Notification {notification_id} already processed")
            return True
        
        # Получаем канал уведомления
        channel = session.query(NotificationChannel).filter(
            NotificationChannel.channel_id == notification.channel_id
        ).first()
        
        if not channel or not channel.is_active:
            logger.error(f"Channel {notification.channel_id} not found or inactive")
            return False
        
        # Отправляем уведомление в зависимости от канала
        success = False
        if channel.channel_code == 'push':
            success = send_push_notification(session, notification)
        elif channel.channel_code == 'email':
            success = send_email_notification(session, notification)
        elif channel.channel_code == 'sms':
            success = send_sms_notification(session, notification)
        elif channel.channel_code == 'in_app':
            success = True  # Внутренние уведомления сразу считаются отправленными
        
        if success:
            notification.mark_as_sent()
            log_notification_event(session, notification.notification_id, 'sent')
        else:
            notification.mark_as_failed("Delivery failed")
            log_notification_event(session, notification.notification_id, 'failed')
        
        session.commit()
        return success
        
    except Exception as e:
        logger.error(f"Error sending notification {notification_id}: {e}")
        session.rollback()
        
        # Повторная попытка
        if self.request.retries < 3:
            raise self.retry(countdown=60 * (self.request.retries + 1))
        
        return False
    finally:
        session.close()