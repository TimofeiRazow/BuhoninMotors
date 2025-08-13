# app/blueprints/users/services.py
"""
Сервисы для работы с пользователями
"""

from datetime import datetime
from sqlalchemy.orm import joinedload
from sqlalchemy import or_, and_, func
from werkzeug.security import check_password_hash, generate_password_hash

from app.models.user import User, UserProfile, UserSettings, DeviceRegistration
from app.models.review import UserReview
from app.models.listing import Listing
from app.utils.pagination import paginate


class UserService:
    """Сервис для работы с пользователями"""
    
    @staticmethod
    def update_user_profile(db, user_id, data):
        """Обновление профиля пользователя"""
        user = db.query(User).options(joinedload(User.profile)).filter(
            User.user_id == user_id,
            User.is_active == True
        ).first()
        
        if not user:
            return None
        
        # Обновляем основные данные пользователя
        if 'first_name' in data:
            user.first_name = data['first_name']
        if 'last_name' in data:
            user.last_name = data['last_name']
        if 'email' in data:
            user.email = data['email']
        
        # Обновляем или создаем профиль
        if not user.profile:
            user.profile = UserProfile(user_id=user_id)
        
        profile_fields = [
            'company_name', 'address', 'city_id', 'avatar_url',
            'description', 'website', 'business_hours'
        ]
        
        for field in profile_fields:
            if field in data:
                setattr(user.profile, field, data[field])
        
        user.updated_date = datetime.utcnow()
        db.commit()
        return user
    
    @staticmethod
    def get_user_settings(db, user_id):
        """Получение настроек пользователя"""
        settings = db.query(UserSettings).filter_by(user_id=user_id).first()
        
        if not settings:
            # Создаем настройки по умолчанию
            settings = UserSettings(user_id=user_id)
            db.add(settings)
            db.commit()
        
        return settings
    
    @staticmethod
    def update_user_settings(db, user_id, data):
        """Обновление настроек пользователя"""
        settings = UserService.get_user_settings(db, user_id)
        
        settings_fields = [
            'notifications_enabled', 'email_notifications', 'sms_notifications',
            'push_notifications', 'auto_renewal_enabled', 'privacy_settings',
            'preferred_language', 'timezone'
        ]
        
        for field in settings_fields:
            if field in data:
                setattr(settings, field, data[field])
        
        settings.updated_date = datetime.utcnow()
        db.commit()
        return settings
    
    @staticmethod
    def change_password(db, user_id, current_password, new_password):
        """Смена пароля пользователя"""
        user = db.query(User).filter_by(user_id=user_id, is_active=True).first()
        
        if not user or not check_password_hash(user.password_hash, current_password):
            return False
        
        user.password_hash = generate_password_hash(new_password)
        user.updated_date = datetime.utcnow()
        db.commit()
        return True
    
    @staticmethod
    def get_user_statistics(db, user_id):
        """Получение статистики пользователя"""
        # Статистика объявлений
        listings_stats = db.query(
            func.count(Listing.listing_id).label('total_listings'),
            func.sum(func.case([(Listing.status_id == 3, 1)], else_=0)).label('active_listings'),
            func.sum(func.case([(Listing.status_id == 4, 1)], else_=0)).label('sold_listings'),
            func.sum(Listing.view_count).label('total_views')
        ).filter(Listing.user_id == user_id).first()
        
        # Статистика отзывов
        reviews_stats = db.query(
            func.count(UserReview.review_id).label('reviews_count'),
            func.avg(UserReview.rating).label('avg_rating')
        ).filter(
            UserReview.reviewed_user_id == user_id,
            UserReview.is_public == True
        ).first()
        
        return {
            'listings': {
                'total': listings_stats.total_listings or 0,
                'active': listings_stats.active_listings or 0,
                'sold': listings_stats.sold_listings or 0,
                'total_views': listings_stats.total_views or 0
            },
            'reviews': {
                'count': reviews_stats.reviews_count or 0,
                'average_rating': float(reviews_stats.avg_rating or 0)
            }
        }
    
    @staticmethod
    def get_user_reviews(db, user_id, page=1, per_page=10):
        """Получение отзывов о пользователе"""
        query = db.query(UserReview).options(
            joinedload(UserReview.reviewer)
        ).filter(
            UserReview.reviewed_user_id == user_id,
            UserReview.is_public == True
        ).order_by(UserReview.created_date.desc())
        
        return paginate(query, page, per_page)
    
    @staticmethod
    def get_public_profile(db, user_id):
        """Получение публичного профиля пользователя"""
        user = db.query(User).options(
            joinedload(User.profile)
        ).filter(
            User.user_id == user_id,
            User.is_active == True
        ).first()
        
        if not user:
            return None
        
        # Статистика для публичного профиля
        stats = UserService.get_user_statistics(db, user_id)
        
        return {
            'user_id': user.user_id,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'user_type': user.user_type,
            'registration_date': user.registration_date.isoformat(),
            'profile': {
                'company_name': user.profile.company_name if user.profile else None,
                'avatar_url': user.profile.avatar_url if user.profile else None,
                'description': user.profile.description if user.profile else None,
                'rating_average': user.profile.rating_average if user.profile else 0,
                'reviews_count': user.profile.reviews_count if user.profile else 0
            },
            'statistics': stats
        }
    
    @staticmethod
    def is_admin(db, user_id):
        """Проверка прав администратора"""
        user = db.query(User).filter_by(user_id=user_id, is_active=True).first()
        return user and user.user_type == 'admin'
    
    @staticmethod
    def search_users(db, query, page=1, per_page=20):
        """Поиск пользователей"""
        search_query = db.query(User).options(
            joinedload(User.profile)
        ).filter(
            User.is_active == True,
            or_(
                User.first_name.ilike(f'%{query}%'),
                User.last_name.ilike(f'%{query}%'),
                User.email.ilike(f'%{query}%'),
                User.phone_number.ilike(f'%{query}%')
            )
        ).order_by(User.registration_date.desc())
        
        return paginate(search_query, page, per_page)
    
    @staticmethod
    def block_user(db, user_id, admin_id, reason=''):
        """Блокировка пользователя"""
        user = db.query(User).filter_by(user_id=user_id, is_active=True).first()
        
        if not user or user.user_type == 'admin':
            return False
        
        # Здесь можно добавить логику записи в лог блокировки
        user.is_active = False
        user.updated_date = datetime.utcnow()
        db.commit()
        return True
    
    @staticmethod
    def unblock_user(db, user_id, admin_id):
        """Разблокировка пользователя"""
        user = db.query(User).filter_by(user_id=user_id, is_active=False).first()
        
        if not user:
            return False
        
        user.is_active = True
        user.updated_date = datetime.utcnow()
        db.commit()
        return True
    
    @staticmethod
    def get_user_devices(db, user_id):
        """Получение устройств пользователя"""
        devices = db.query(DeviceRegistration).filter(
            DeviceRegistration.user_id == user_id,
            DeviceRegistration.is_active == True
        ).order_by(DeviceRegistration.last_active_date.desc()).all()
        
        return [{
            'device_id': device.device_id,
            'device_type': device.device_type,
            'device_model': device.device_model,
            'registration_date': device.registration_date.isoformat(),
            'last_active_date': device.last_active_date.isoformat()
        } for device in devices]
    
    @staticmethod
    def remove_user_device(db, user_id, device_id):
        """Удаление устройства пользователя"""
        device = db.query(DeviceRegistration).filter(
            DeviceRegistration.device_id == device_id,
            DeviceRegistration.user_id == user_id,
            DeviceRegistration.is_active == True
        ).first()
        
        if not device:
            return False
        
        device.is_active = False
        db.commit()
        return True