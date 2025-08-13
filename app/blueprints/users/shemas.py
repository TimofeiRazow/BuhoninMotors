# app/blueprints/users/schemas.py (ИСПРАВЛЕННАЯ ВЕРСИЯ)
"""
Marshmallow схемы для пользователей
"""

from marshmallow import Schema, fields, validate, validates, ValidationError, post_load
from marshmallow.validate import Length, Email, OneOf, Range


class UserProfileSchema(Schema):
    """Схема для профиля пользователя"""
    user_id = fields.Int(dump_only=True)
    phone_number = fields.Str(dump_only=True)
    email = fields.Email(allow_none=True)
    first_name = fields.Str(allow_none=True)
    last_name = fields.Str(allow_none=True)
    user_type = fields.Str(dump_only=True)
    registration_date = fields.DateTime(dump_only=True)
    last_login = fields.DateTime(dump_only=True)
    verification_status = fields.Str(dump_only=True)
    
    # Поля профиля
    company_name = fields.Str(allow_none=True, validate=Length(max=255))
    address = fields.Str(allow_none=True)
    city_id = fields.Int(allow_none=True)
    avatar_url = fields.Url(allow_none=True)
    description = fields.Str(allow_none=True, validate=Length(max=1000))
    website = fields.Url(allow_none=True)
    business_hours = fields.Raw(allow_none=True)
    rating_average = fields.Float(dump_only=True)
    reviews_count = fields.Int(dump_only=True)
    
    # Дополнительные поля
    city_name = fields.Str(dump_only=True, attribute='profile.city.city_name', allow_none=True)
    region_name = fields.Str(dump_only=True, attribute='profile.city.region.region_name', allow_none=True)


class UserProfileUpdateSchema(Schema):
    """Схема для обновления профиля пользователя"""
    first_name = fields.Str(validate=Length(min=1, max=100), allow_none=True)
    last_name = fields.Str(validate=Length(min=1, max=100), allow_none=True)
    email = fields.Email(allow_none=True)
    company_name = fields.Str(validate=Length(max=255), allow_none=True)
    address = fields.Str(allow_none=True)
    city_id = fields.Int(allow_none=True, validate=Range(min=1))
    avatar_url = fields.Url(allow_none=True)
    description = fields.Str(validate=Length(max=1000), allow_none=True)
    website = fields.Url(allow_none=True)
    business_hours = fields.Raw(allow_none=True)
    
    @validates('business_hours')
    def validate_business_hours(self, value):
        """Валидация рабочих часов"""
        if value and not isinstance(value, dict):
            raise ValidationError('Business hours must be a valid JSON object')


class UserSettingsSchema(Schema):
    """Схема для настроек пользователя"""
    notifications_enabled = fields.Bool(missing=True)
    email_notifications = fields.Bool(missing=True)
    sms_notifications = fields.Bool(missing=False)
    push_notifications = fields.Bool(missing=True)
    auto_renewal_enabled = fields.Bool(missing=False)
    privacy_settings = fields.Raw(missing={})
    preferred_language = fields.Str(
        missing='ru',
        validate=OneOf(['ru', 'kk', 'en'])
    )
    timezone = fields.Str(missing='Asia/Almaty')
    
    @validates('privacy_settings')
    def validate_privacy_settings(self, value):
        """Валидация настроек приватности"""
        if value and not isinstance(value, dict):
            raise ValidationError('Privacy settings must be a valid JSON object')


class ChangePasswordSchema(Schema):
    """Схема для смены пароля"""
    current_password = fields.Str(required=True, validate=Length(min=1))
    new_password = fields.Str(
        required=True,
        validate=Length(min=8, max=128)
    )
    confirm_password = fields.Str(required=True)
    
    @validates('new_password')
    def validate_password_strength(self, value):
        """Валидация силы пароля"""
        if not any(c.isdigit() for c in value):
            raise ValidationError('Password must contain at least one digit')
        if not any(c.isalpha() for c in value):
            raise ValidationError('Password must contain at least one letter')
        if not any(c.isupper() for c in value):
            raise ValidationError('Password must contain at least one uppercase letter')
    
    @post_load
    def validate_password_match(self, data, **kwargs):
        """Валидация совпадения паролей"""
        if data.get('new_password') != data.get('confirm_password'):
            raise ValidationError({'confirm_password': ['Passwords do not match']})
        return data


class UserStatsSchema(Schema):
    """Схема для статистики пользователя"""
    listings = fields.Dict(keys=fields.Str(), values=fields.Int())
    reviews = fields.Dict(keys=fields.Str(), values=fields.Raw())
    total_views = fields.Int()
    join_date = fields.DateTime()
    last_activity = fields.DateTime()


class UserListSchema(Schema):
    """Схема для списка пользователей (для админа)"""
    user_id = fields.Int()
    phone_number = fields.Str()
    email = fields.Email(allow_none=True)
    first_name = fields.Str(allow_none=True)
    last_name = fields.Str(allow_none=True)
    user_type = fields.Str()
    registration_date = fields.DateTime()
    last_login = fields.DateTime(allow_none=True)
    is_active = fields.Bool()
    verification_status = fields.Str()
    
    # Профиль
    company_name = fields.Str(allow_none=True)
    rating_average = fields.Float()
    reviews_count = fields.Int()
    
    # Статистика
    total_listings = fields.Int()
    active_listings = fields.Int()


class DeviceSchema(Schema):
    """Схема для устройств пользователя"""
    device_id = fields.Int()
    device_type = fields.Str(validate=OneOf(['ios', 'android', 'web']))
    device_model = fields.Str(allow_none=True)
    os_version = fields.Str(allow_none=True)
    app_version = fields.Str(allow_none=True)
    registration_date = fields.DateTime()
    last_active_date = fields.DateTime()
    is_active = fields.Bool()


class UserPublicProfileSchema(Schema):
    """Схема для публичного профиля пользователя"""
    user_id = fields.Int()
    first_name = fields.Str(allow_none=True)
    last_name = fields.Str(allow_none=True)
    user_type = fields.Str()
    registration_date = fields.DateTime()
    
    # Публичные поля профиля
    company_name = fields.Str(allow_none=True)
    avatar_url = fields.Url(allow_none=True)
    description = fields.Str(allow_none=True)
    website = fields.Url(allow_none=True)
    rating_average = fields.Float()
    reviews_count = fields.Int()
    
    # Статистика
    total_listings = fields.Int()
    active_listings = fields.Int()
    
    # Город (если публичный)
    city_name = fields.Str(allow_none=True)


# app/blueprints/users/services.py (ЗАВЕРШЕННАЯ ВЕРСИЯ)
"""
Сервисы для работы с пользователями
"""

from datetime import datetime, timedelta
from sqlalchemy.orm import joinedload
from sqlalchemy import or_, and_, func
from werkzeug.security import check_password_hash, generate_password_hash

from app.models.user import User, UserProfile, UserSettings, DeviceRegistration
from app.models.review import UserReview
from app.models.listing import Listing
from app.models.location import City, Region
from app.utils.pagination import paginate
from app.utils.exceptions import APIException


class UserService:
    """Сервис для работы с пользователями"""
    
    @staticmethod
    def get_user_profile(db, user_id):
        """Получение полного профиля пользователя"""
        return db.query(User).options(
            joinedload(User.profile).joinedload(UserProfile.city).joinedload(City.region),
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
        
        # Получаем дату регистрации
        user = db.query(User).filter_by(user_id=user_id).first()
        
        return {
            'listings': {
                'total': int(listings_stats.total_listings or 0),
                'active': int(listings_stats.active_listings or 0),
                'sold': int(listings_stats.sold_listings or 0),
                'total_views': int(listings_stats.total_views or 0)
            },
            'reviews': {
                'count': int(reviews_stats.reviews_count or 0),
                'average_rating': float(reviews_stats.avg_rating or 0)
            },
            'join_date': user.registration_date if user else None,
            'last_activity': user.last_login if user else None
        }
    
    @staticmethod
    def get_user_reviews(db, user_id, page=1, per_page=10):
        """Получение отзывов о пользователе"""
        query = db.query(UserReview).options(
            joinedload(UserReview.reviewer).load_only(
                User.user_id, User.first_name, User.last_name
            )
        ).filter(
            UserReview.reviewed_user_id == user_id,
            UserReview.is_public == True
        ).order_by(UserReview.created_date.desc())
        
        return paginate(query, page, per_page)
    
    @staticmethod
    def get_public_profile(db, user_id):
        """Получение публичного профиля пользователя"""
        user = db.query(User).options(
            joinedload(User.profile).joinedload(UserProfile.city)
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
                'city_name': user.profile.city.city_name if user.profile and user.profile.city else None
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
        
        # Записываем в лог блокировки (можно добавить отдельную таблицу)
        user.is_active = False
        user.updated_date = datetime.utcnow()
        
        # Деактивируем все активные объявления пользователя
        db.query(Listing).filter(
            Listing.user_id == user_id,
            Listing.status_id == 3  # active
        ).update({'status_id': 6})  # blocked
        
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