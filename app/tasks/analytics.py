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