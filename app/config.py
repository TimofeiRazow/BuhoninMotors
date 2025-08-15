# app/config.py
import os
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Базовая конфигурация"""
    # Основные настройки
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    
    # База данных
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'postgresql://postgres:password@localhost/kolesa_db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_size': 10,
        'pool_recycle': 120,
        'pool_pre_ping': True
    }
    
    # JWT настройки
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY') or SECRET_KEY
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=1)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=30)
    JWT_BLACKLIST_ENABLED = True
    JWT_BLACKLIST_TOKEN_CHECKS = ['access', 'refresh']
    
    # Redis настройки (для кэша и Celery)
    REDIS_URL = os.environ.get('REDIS_URL') or 'redis://localhost:6379/0'
    CACHE_TYPE = "SimpleCache"
    CACHE_REDIS_URL = REDIS_URL
    CACHE_DEFAULT_TIMEOUT = 300
    
    # Celery настройки
    CELERY_BROKER_URL = os.environ.get('CELERY_BROKER_URL') or 'redis://localhost:6379/1'
    CELERY_RESULT_BACKEND = REDIS_URL
    
    # Загрузка файлов
    UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER') or 'uploads'
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf', 'doc', 'docx'}
    
    # Email настройки
    MAIL_SERVER = os.environ.get('MAIL_SERVER') or 'smtp.gmail.com'
    MAIL_PORT = int(os.environ.get('MAIL_PORT') or 587)
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'true').lower() in ['true', 'on', '1']
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER') or 'noreply@kolesa.kz'
    
    # SMS настройки
    SMS_PROVIDER = os.environ.get('SMS_PROVIDER') or 'smsc'
    SMS_LOGIN = os.environ.get('SMS_LOGIN')
    SMS_PASSWORD = os.environ.get('SMS_PASSWORD')
    
    # Push уведомления
    FCM_SERVER_KEY = os.environ.get('FCM_SERVER_KEY')
    APNS_CERT_PATH = os.environ.get('APNS_CERT_PATH')
    
    # Платежные системы
    KASPI_MERCHANT_ID = os.environ.get('KASPI_MERCHANT_ID')
    KASPI_SECRET_KEY = os.environ.get('KASPI_SECRET_KEY')
    PAYBOX_MERCHANT_ID = os.environ.get('PAYBOX_MERCHANT_ID')
    PAYBOX_SECRET_KEY = os.environ.get('PAYBOX_SECRET_KEY')
    
    # Лимиты запросов
    RATELIMIT_STORAGE_URL = REDIS_URL
    RATELIMIT_DEFAULT = "1000 per hour"
    
    # Поиск и индексация
    ELASTICSEARCH_URL = os.environ.get('ELASTICSEARCH_URL')
    
    # Мониторинг
    SENTRY_DSN = os.environ.get('SENTRY_DSN')
    
    # Безопасность
    SECURITY_PASSWORD_SALT = os.environ.get('SECURITY_PASSWORD_SALT') or 'salt'
    BCRYPT_LOG_ROUNDS = 12
    
    # Локализация
    LANGUAGES = ['ru', 'kk', 'en']
    BABEL_DEFAULT_LOCALE = 'ru'
    BABEL_DEFAULT_TIMEZONE = 'Asia/Almaty'


class DevelopmentConfig(Config):
    """Конфигурация для разработки"""
    DEBUG = True
    TESTING = False
    WTF_CSRF_ENABLED = False


class TestingConfig(Config):
    """Конфигурация для тестирования"""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(minutes=5)
    WTF_CSRF_ENABLED = False


class ProductionConfig(Config):
    """Конфигурация для продакшена"""
    DEBUG = False
    TESTING = False
    
    # Более строгие настройки безопасности
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    
    # Строгие лимиты
    RATELIMIT_DEFAULT = "200 per hour"


config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}