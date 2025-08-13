# app/blueprints/notifications/push.py
"""
Сервис для отправки push-уведомлений
"""

import json
import requests
from flask import current_app
from pyfcm import FCMNotification


class PushNotificationService:
    """Сервис для отправки push-уведомлений"""
    
    @staticmethod
    def send_push(device_token, device_type, title, message, data=None):
        """Отправка push-уведомления на устройство"""
        try:
            if device_type in ['ios', 'android']:
                return PushNotificationService._send_fcm_push(
                    device_token, title, message, data
                )
            elif device_type == 'web':
                return PushNotificationService._send_web_push(
                    device_token, title, message, data
                )
            else:
                current_app.logger.warning(f"Unknown device type: {device_type}")
                return False
                
        except Exception as e:
            current_app.logger.error(f"Error sending push notification: {e}")
            return False
    
    @staticmethod
    def _send_fcm_push(device_token, title, message, data=None):
        """Отправка push через Firebase Cloud Messaging"""
        try:
            fcm_api_key = current_app.config.get('FCM_API_KEY')
            if not fcm_api_key:
                current_app.logger.error("FCM_API_KEY not configured")
                return False
            
            push_service = FCMNotification(api_key=fcm_api_key)
            
            extra_data = data or {}
            extra_data.update({
                'click_action': 'FLUTTER_NOTIFICATION_CLICK',
                'sound': 'default'
            })
            
            result = push_service.notify_single_device(
                registration_id=device_token,
                message_title=title,
                message_body=message,
                data_message=extra_data
            )
            
            return result.get('success', 0) > 0
            
        except Exception as e:
            current_app.logger.error(f"Error sending FCM push: {e}")
            return False
    
    @staticmethod
    def _send_web_push(device_token, title, message, data=None):
        """Отправка web push-уведомления"""
        try:
            vapid_private_key = current_app.config.get('VAPID_PRIVATE_KEY')
            vapid_claims = current_app.config.get('VAPID_CLAIMS', {})
            
            if not vapid_private_key:
                current_app.logger.error("VAPID keys not configured")
                return False
            
            from pywebpush import webpush
            
            payload = json.dumps({
                'title': title,
                'body': message,
                'data': data or {}
            })
            
            webpush(
                subscription_info=json.loads(device_token),
                data=payload,
                vapid_private_key=vapid_private_key,
                vapid_claims=vapid_claims
            )
            
            return True
            
        except Exception as e:
            current_app.logger.error(f"Error sending web push: {e}")
            return False
    
    @staticmethod
    def send_bulk_push(notifications_data):
        """Массовая отправка push-уведомлений"""
        success_count = 0
        
        for notification in notifications_data:
            if PushNotificationService.send_push(
                notification['device_token'],
                notification['device_type'],
                notification['title'],
                notification['message'],
                notification.get('data')
            ):
                success_count += 1
        
        return success_count
    
    @staticmethod
    def validate_device_token(device_token, device_type):
        """Валидация токена устройства"""
        try:
            if device_type in ['ios', 'android']:
                # FCM токены обычно длинной 152+ символов
                return len(device_token) > 100
            elif device_type == 'web':
                # Web push токены в формате JSON
                json.loads(device_token)
                return True
            return False
        except:
            return False