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

