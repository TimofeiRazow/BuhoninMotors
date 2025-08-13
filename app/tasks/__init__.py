# app/tasks/__init__.py
from app.extensions import make_celery
from flask import current_app


def init_celery(app):
    """Инициализация Celery с Flask приложением"""
    celery = make_celery(app)
    
    # Импортируем все задачи
    from . import notifications
    from . import cleanup
    from . import indexing
    from . import analytics
    
    return celery


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


# app/tasks/cleanup.py
"""
Задачи для очистки данных
"""

from celery import Celery
from datetime import datetime, timedelta
from app.extensions import db
from app.models.listing import Listing
from app.models.user import UserSession, LoginAttempt, PhoneVerification
from app.models.media import MediaStorage

celery = Celery('kolesa_cleanup')


@celery.task
def cleanup_expired_listings():
    """Очистка истекших объявлений"""
    expired_date = datetime.utcnow()
    
    # Находим истекшие объявления
    expired_listings = Listing.query.filter(
        Listing.expires_date <= expired_date,
        Listing.is_active == True
    ).all()
    
    count = 0
    for listing in expired_listings:
        # Переводим в статус "истек"
        from app.models.base import get_status_by_code
        expired_status = get_status_by_code('listing_status', 'expired')
        if expired_status:
            listing.status_id = expired_status.status_id
            listing.save()
            count += 1
    
    return {'expired_listings': count}


@celery.task
def cleanup_old_sessions():
    """Очистка старых сессий"""
    expiry_date = datetime.utcnow()
    
    deleted_count = UserSession.query.filter(
        UserSession.expires_at <= expiry_date
    ).delete()
    
    db.session.commit()
    
    return {'deleted_sessions': deleted_count}


@celery.task
def cleanup_old_login_attempts():
    """Очистка старых попыток входа"""
    cutoff_date = datetime.utcnow() - timedelta(days=30)
    
    deleted_count = LoginAttempt.query.filter(
        LoginAttempt.attempted_at <= cutoff_date
    ).delete()
    
    db.session.commit()
    
    return {'deleted_attempts': deleted_count}


@celery.task
def cleanup_old_verifications():
    """Очистка старых кодов верификации"""
    cutoff_date = datetime.utcnow() - timedelta(hours=24)
    
    deleted_count = PhoneVerification.query.filter(
        PhoneVerification.created_at <= cutoff_date
    ).delete()
    
    db.session.commit()
    
    return {'deleted_verifications': deleted_count}


@celery.task
def cleanup_orphaned_media():
    """Очистка медиа файлов без связанных сущностей"""
    import os
    
    # Находим медиа файлы, у которых нет активной связанной сущности
    orphaned_media = db.session.query(MediaStorage).join(
        GlobalEntity, MediaStorage.entity_id == GlobalEntity.entity_id
    ).filter(
        GlobalEntity.is_active == False
    ).all()
    
    count = 0
    for media in orphaned_media:
        # Удаляем файл с диска
        if media.delete_file():
            media.delete()
            count += 1
    
    return {'deleted_media_files': count}


@celery.task
def daily_cleanup():
    """Ежедневная очистка данных"""
    results = {}
    
    # Запускаем все задачи очистки
    results['expired_listings'] = cleanup_expired_listings()
    results['old_sessions'] = cleanup_old_sessions()
    results['old_login_attempts'] = cleanup_old_login_attempts()
    results['old_verifications'] = cleanup_old_verifications()
    results['orphaned_media'] = cleanup_orphaned_media()
    
    return results


# app/tasks/indexing.py
"""
Задачи для индексации и поиска
"""

from celery import Celery
from app.extensions import db
from app.models.listing import Listing
from sqlalchemy import text

celery = Celery('kolesa_indexing')


@celery.task
def update_search_vectors():
    """Обновление поисковых векторов для объявлений"""
    # Обновляем search_vector для всех активных объявлений
    query = text("""
        UPDATE listings 
        SET search_vector = to_tsvector('russian', COALESCE(title, '') || ' ' || COALESCE(description, ''))
        WHERE is_active = true AND search_vector IS NULL
    """)
    
    result = db.session.execute(query)
    db.session.commit()
    
    return {'updated_vectors': result.rowcount}


@celery.task
def reindex_listing(listing_id):
    """Переиндексация конкретного объявления"""
    listing = Listing.query.get(listing_id)
    if not listing:
        return {'error': 'Listing not found'}
    
    # Обновляем поисковый вектор
    search_text = f"{listing.title or ''} {listing.description or ''}"
    
    query = text("""
        UPDATE listings 
        SET search_vector = to_tsvector('russian', :search_text)
        WHERE listing_id = :listing_id
    """)
    
    db.session.execute(query, {
        'search_text': search_text,
        'listing_id': listing_id
    })
    db.session.commit()
    
    return {'listing_id': listing_id, 'reindexed': True}


@celery.task
def rebuild_search_index():
    """Полная переиндексация всех объявлений"""
    query = text("""
        UPDATE listings 
        SET search_vector = to_tsvector('russian', COALESCE(title, '') || ' ' || COALESCE(description, ''))
        WHERE is_active = true
    """)
    
    result = db.session.execute(query)
    db.session.commit()
    
    return {'reindexed_listings': result.rowcount}


# app/tasks/analytics.py
"""
Задачи для аналитики и статистики
"""

from celery import Celery
from datetime import datetime, timedelta
from app.extensions import db
from app.models.listing import Listing
from app.models.user import User
from sqlalchemy import func

celery = Celery('kolesa_analytics')


@celery.task
def calculate_daily_stats():
    """Вычисление ежедневной статистики"""
    today = datetime.utcnow().date()
    yesterday = today - timedelta(days=1)
    
    stats = {
        'date': today.isoformat(),
        'new_users': User.query.filter(
            func.date(User.registration_date) == yesterday,
            User.is_active == True
        ).count(),
        'new_listings': Listing.query.filter(
            func.date(Listing.created_date) == yesterday,
            Listing.is_active == True
        ).count(),
        'active_users': User.query.filter(
            func.date(User.last_login) == yesterday,
            User.is_active == True
        ).count()
    }
    
    # Сохраняем статистику в БД или отправляем в систему аналитики
    # Здесь можно интегрироваться с Google Analytics, Mixpanel и т.д.
    
    return stats


@celery.task
def update_listing_scores():
    """Обновление рейтингов объявлений"""
    from app.utils.helpers import calculate_listing_score
    
    listings = Listing.query.filter(Listing.is_active == True).all()
    
    updated_count = 0
    for listing in listings:
        # Вычисляем новый рейтинг
        score = calculate_listing_score(listing.to_dict())
        
        # Сохраняем в метаданных или отдельном поле
        if hasattr(listing, 'search_score'):
            listing.search_score = score
            listing.save()
            updated_count += 1
    
    return {'updated_scores': updated_count}


@celery.task
def generate_user_recommendations(user_id):
    """Генерация рекомендаций для пользователя"""
    user = User.query.get(user_id)
    if not user:
        return {'error': 'User not found'}
    
    # Простая логика рекомендаций на основе:
    # 1. Избранных объявлений пользователя
    # 2. Истории поиска
    # 3. Популярных объявлений в его городе
    
    recommendations = []
    
    # Получаем город пользователя
    if user.profile and user.profile.city_id:
        city_listings = Listing.query.filter(
            Listing.city_id == user.profile.city_id,
            Listing.is_active == True
        ).order_by(Listing.view_count.desc()).limit(10).all()
        
        recommendations.extend([listing.listing_id for listing in city_listings])
    
    return {
        'user_id': user_id,
        'recommendations': recommendations,
        'generated_at': datetime.utcnow().isoformat()
    }


@celery.task
def send_weekly_digest():
    """Отправка еженедельного дайджеста пользователям"""
    # Получаем пользователей, подписанных на дайджест
    users = User.query.join(UserSettings).filter(
        UserSettings.email_notifications == True,
        User.email.isnot(None),
        User.is_active == True
    ).all()
    
    sent_count = 0
    for user in users:
        # Генерируем персональный дайджест
        digest_data = {
            'user_name': user.full_name,
            'new_listings_count': get_new_listings_count_for_user(user),
            'recommendations': generate_user_recommendations.delay(user.user_id),
            'popular_listings': get_popular_listings_for_user(user)
        }
        
        # Отправляем email
        from app.tasks.notifications import send_email_notification
        send_email_notification.delay(
            user.user_id,
            'weekly_digest',
            digest_data
        )
        sent_count += 1
    
    return {'digest_sent_to': sent_count}


def get_new_listings_count_for_user(user):
    """Получение количества новых объявлений для пользователя"""
    week_ago = datetime.utcnow() - timedelta(days=7)
    
    # Считаем новые объявления в городе пользователя
    count = 0
    if user.profile and user.profile.city_id:
        count = Listing.query.filter(
            Listing.city_id == user.profile.city_id,
            Listing.created_date >= week_ago,
            Listing.is_active == True
        ).count()
    
    return count


def get_popular_listings_for_user(user):
    """Получение популярных объявлений для пользователя"""
    query = Listing.query.filter(Listing.is_active == True)
    
    if user.profile and user.profile.city_id:
        query = query.filter(Listing.city_id == user.profile.city_id)
    
    popular = query.order_by(
        Listing.view_count.desc(),
        Listing.favorite_count.desc()
    ).limit(5).all()
    
    return [listing.to_dict() for listing in popular]


# Периодические задачи (настраиваются в Celery Beat)
from celery.schedules import crontab

celery.conf.beat_schedule = {
    'daily-cleanup': {
        'task': 'app.tasks.cleanup.daily_cleanup',
        'schedule': crontab(hour=2, minute=0),  # Каждый день в 2:00
    },
    'update-search-vectors': {
        'task': 'app.tasks.indexing.update_search_vectors',
        'schedule': crontab(hour=3, minute=0),  # Каждый день в 3:00
    },
    'calculate-daily-stats': {
        'task': 'app.tasks.analytics.calculate_daily_stats',
        'schedule': crontab(hour=1, minute=0),  # Каждый день в 1:00
    },
    'update-listing-scores': {
        'task': 'app.tasks.analytics.update_listing_scores',
        'schedule': crontab(hour=4, minute=0),  # Каждый день в 4:00
    },
    'weekly-digest': {
        'task': 'app.tasks.analytics.send_weekly_digest',
        'schedule': crontab(hour=9, minute=0, day_of_week=1),  # Понедельник в 9:00
    },
}