# app/models/__init__.py
"""
Модели данных для Kolesa.kz
"""

from .favorite import (
    Favorite
)

# Базовые модели
from .base import (
    BaseModel, 
    TimestampMixin, 
    SoftDeleteMixin, 
    EntityBasedModel,
    GlobalEntity, 
    EntityType, 
    StatusGroup, 
    Status, 
    Currency, 
    CategoryTree, 
    Category,
    get_or_create,
    get_status_by_code,
    get_active_statuses
)

# Географические модели
from .location import Country, Region, City

# Пользовательские модели
from .user import (
    User, 
    UserProfile, 
    UserSettings, 
    DeviceRegistration,
    PhoneVerification, 
    EmailVerification, 
    UserSession, 
    LoginAttempt, 
    RevokedToken
)

# Автомобильные модели
from .car import (
    CarBrand, 
    CarModel, 
    CarGeneration, 
    CarAttributeGroup, 
    CarAttribute,
    CarBodyType, 
    CarEngineType, 
    CarTransmissionType, 
    CarDriveType, 
    CarColor, 
    CarFeature,
    get_car_brands_with_models,
    get_car_hierarchy,
    get_car_attributes_grouped,
    get_car_reference_data,
    validate_car_year,
    get_years_range
)

# Модели объявлений
from .listing import (
    Listing, 
    ListingDetails, 
    ListingAttribute, 
    ListingFeature
)

# Медиа модели
from .media import (
    MediaStorage, 
    MediaUploadHelper,
    get_allowed_extensions,
    is_allowed_file,
    get_media_type_from_filename,
    validate_file_size,
    clean_filename,
    generate_unique_filename
)

# Экспортируем все модели для удобства импорта
__all__ = [
    # Базовые
    'BaseModel', 'TimestampMixin', 'SoftDeleteMixin', 'EntityBasedModel',
    'GlobalEntity', 'EntityType', 'StatusGroup', 'Status', 'Currency', 
    'CategoryTree', 'Category',
    
    # Географические
    'Country', 'Region', 'City',
    
    # Пользователи
    'User', 'UserProfile', 'UserSettings', 'DeviceRegistration',
    'PhoneVerification', 'EmailVerification', 'UserSession', 'LoginAttempt', 'RevokedToken',
    
    # Автомобили
    'CarBrand', 'CarModel', 'CarGeneration', 'CarAttributeGroup', 'CarAttribute',
    'CarBodyType', 'CarEngineType', 'CarTransmissionType', 'CarDriveType', 
    'CarColor', 'CarFeature',
    
    # Объявления
    'Listing', 'ListingDetails', 'ListingAttribute', 'ListingFeature',
    
    'Favorite'
    # Медиа
    'MediaStorage', 'MediaUploadHelper',
    
    # Утилиты
    'get_or_create', 'get_status_by_code', 'get_active_statuses',
    'get_car_brands_with_models', 'get_car_hierarchy', 'get_car_attributes_grouped',
    'get_car_reference_data', 'validate_car_year', 'get_years_range',
    'get_allowed_extensions', 'is_allowed_file', 'get_media_type_from_filename',
    'validate_file_size', 'clean_filename', 'generate_unique_filename'
]