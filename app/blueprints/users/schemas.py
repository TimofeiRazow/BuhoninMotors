# app/blueprints/users/schemas.py
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
    city_name = fields.Str(dump_only=True, allow_none=True)
    region_name = fields.Str(dump_only=True, allow_none=True)


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
    listings = fields.Dict(keys=fields.Str(), values=fields.Raw())
    reviews = fields.Dict(keys=fields.Str(), values=fields.Raw())
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


class UserReviewSchema(Schema):
    """Схема для отзывов о пользователе"""
    review_id = fields.Int(dump_only=True)
    reviewer_id = fields.Int(dump_only=True)
    reviewed_user_id = fields.Int()
    rating = fields.Int(required=True, validate=Range(min=1, max=5))
    comment = fields.Str(allow_none=True, validate=Length(max=1000))
    is_public = fields.Bool(missing=True)
    listing_id = fields.Int(allow_none=True)
    created_date = fields.DateTime(dump_only=True)
    reviewer_name = fields.Str(dump_only=True)