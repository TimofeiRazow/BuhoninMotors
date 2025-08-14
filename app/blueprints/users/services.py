# app/blueprints/users/services.py
"""
Сервисы для работы с пользователями
"""

from datetime import datetime
from sqlalchemy.orm import joinedload
from sqlalchemy import or_, and_, func
from werkzeug.security import check_password_hash, generate_password_hash

from app.models.user import User, UserProfile, UserSettings, DeviceRegistration
# Временно закомментируем импорт UserReview до создания модели
# from app.models.review import UserReview
from app.utils.pagination import paginate_query


class UserService:
    """Сервис для работы с пользователями"""
    
    @staticmethod
    def get_user_profile(db, user_id):
        """Получение полного профиля пользователя"""
        return db.query(User).options(
            joinedload(User.profile),
            joinedload(User.settings)
        ).filter(
            User.user_id == user_id,
            User.is_active == True
        ).first()
    
    @staticmethod
    def update_user_profile(db, user_id, data):
        """Обновление профиля пользователя"""
        user = db.query(User).options(joinedload(User.profile)).filter(
            User.user_id == user_id,
            User.is_active == True
        ).first()
        
        if not user:
            return None
        
        # Проверяем уникальность email
        if 'email' in data and data['email']:
            existing_user = db.query(User).filter(
                User.email == data['email'],
                User.user_id != user_id,
                User.is_active == True
            ).first()
            if existing_user:
                from app.utils.exceptions import APIException
                raise APIException('Email already exists', 400)
        
        # Обновляем основные данные пользователя
        user_fields = ['first_name', 'last_name', 'email']
        for field in user_fields:
            if field in data:
                setattr(user, field, data[field])
        
        # Обновляем или создаем профиль
        if not user.profile:
            user.profile = UserProfile(user_id=user_id)
            db.add(user.profile)
        
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
        # Пока что возвращаем базовую статистику без отзывов и объявлений
        # Это можно будет дополнить когда создадим соответствующие модели
        
        # Получаем дату регистрации
        user = db.query(User).filter_by(user_id=user_id).first()
        
        return {
            'listings': {
                'total': 0,
                'active': 0,
                'sold': 0,
                'total_views': 0
            },
            'reviews': {
                'count': 0,
                'average_rating': 0.0
            },
            'join_date': user.registration_date if user else None,
            'last_activity': user.last_login if user else None
        }
    
    @staticmethod
    def get_user_reviews(db, user_id, page=1, per_page=10):
        """Получение отзывов о пользователе"""
        # Временная заглушка - возвращаем пустой результат
        return {
            'items': [],
            'total': 0,
            'page': page,
            'per_page': per_page,
            'pages': 0
        }
    
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
            'registration_date': user.registration_date,
            'profile': {
                'company_name': user.profile.company_name if user.profile else None,
                'avatar_url': user.profile.avatar_url if user.profile else None,
                'description': user.profile.description if user.profile else None,
                'website': user.profile.website if user.profile else None,
                'rating_average': user.profile.rating_average if user.profile else 0,
                'reviews_count': user.profile.reviews_count if user.profile else 0,
                'city_name': None  # Добавим когда создадим модель City
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
        
        return paginate_query(search_query, page, per_page)
    
    @staticmethod
    def block_user(db, user_id, admin_id, reason=''):
        """Блокировка пользователя"""
        user = db.query(User).filter_by(user_id=user_id, is_active=True).first()
        
        if not user or user.user_type == 'admin':
            return False
        
        # Записываем в лог блокировки (можно добавить отдельную таблицу)
        user.is_active = False
        user.updated_date = datetime.utcnow()
        
        # Здесь можно будет добавить деактивацию объявлений когда создадим модель Listing
        
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
            'os_version': device.os_version,
            'app_version': device.app_version,
            'registration_date': device.registration_date,
            'last_active_date': device.last_active_date,
            'is_active': device.is_active
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
    
    @staticmethod
    def update_user_activity(db, user_id):
        """Обновление времени последней активности пользователя"""
        db.query(User).filter_by(user_id=user_id).update({
            'last_login': datetime.utcnow()
        })
        db.commit()
    
    @staticmethod
    def get_user_by_phone_or_email(db, phone_or_email):
        """Получение пользователя по телефону или email"""
        return db.query(User).filter(
            or_(
                User.phone_number == phone_or_email,
                User.email == phone_or_email
            ),
            User.is_active == True
        ).first()
    
    @staticmethod
    def verify_user_email(db, user_id):
        """Верификация email пользователя"""
        user = db.query(User).filter_by(user_id=user_id).first()
        if user:
            if user.verification_status == 'phone_verified':
                user.verification_status = 'fully_verified'
            else:
                user.verification_status = 'email_verified'
            db.commit()
            return True
        return False
    
    @staticmethod
    def verify_user_phone(db, user_id):
        """Верификация телефона пользователя"""
        user = db.query(User).filter_by(user_id=user_id).first()
        if user:
            if user.verification_status == 'email_verified':
                user.verification_status = 'fully_verified'
            else:
                user.verification_status = 'phone_verified'
            db.commit()
            return True
        return False