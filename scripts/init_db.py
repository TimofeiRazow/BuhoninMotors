#!/usr/bin/env python3
"""
Скрипт инициализации базы данных для Kolesa.kz Backend
Создает все таблицы и заполняет базовыми данными
"""

import os
import sys
import logging
from datetime import datetime

# Добавляем корневую директорию в Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask
from app import create_app
from app.database import db_manager, init_db, reset_db
from app.models import *  # Импортируем все модели

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('init_db.log')
    ]
)

logger = logging.getLogger(__name__)


def create_tables():
    """Создание всех таблиц"""
    try:
        logger.info("Creating database tables...")
        
        # Импортируем все модели для регистрации в SQLAlchemy
        from app.models.base import GlobalEntity
        from app.models.user import User, UserProfile, UserSettings, DeviceRegistration
        from app.models.location import Country, Region, City
        from app.models.category import CategoryTree, Category, StatusGroup, Status
        from app.models.listing import Listing, ListingDetails, ListingAttributes, ListingFeatures
        from app.models.car import (
            CarBrand, CarModel, CarGeneration, CarAttributeGroup, CarAttribute,
            CarBodyType, CarEngineType, CarTransmissionType, CarDriveType, 
            CarColor, CarFeature
        )
        from app.models.conversation import Conversation, ConversationParticipant, Message, MessageAttachment
        from app.models.media import MediaStorage
        from app.models.notification import (
            NotificationChannel, NotificationTemplate, Notification, 
            UserNotificationSettings
        )
        from app.models.payment import (
            Currency, PromotionService, EntityPromotion, PaymentTransaction
        )
        from app.models.review import UserReview, CarOwnerReview
        from app.models.support import SupportTicket
        
        # Создаем таблицы
        from app.database import Base, engine
        Base.metadata.create_all(bind=engine)
        
        logger.info("Database tables created successfully!")
        return True
        
    except Exception as e:
        logger.error(f"Error creating tables: {e}")
        return False


def seed_countries_and_regions():
    """Заполнение стран и регионов"""
    from app.models.location import Country, Region, City
    from app.database import get_db
    
    db = get_db()
    
    try:
        logger.info("Seeding countries and regions...")
        
        # Проверяем, не заполнено ли уже
        if db.query(Country).first():
            logger.info("Countries already exist, skipping...")
            return True
        
        # Страны
        countries_data = [
            {'country_code': 'KZ', 'country_name': 'Казахстан', 'phone_code': '+7'},
            {'country_code': 'RU', 'country_name': 'Россия', 'phone_code': '+7'},
            {'country_code': 'BY', 'country_name': 'Беларусь', 'phone_code': '+375'},
            {'country_code': 'UZ', 'country_name': 'Узбекистан', 'phone_code': '+998'},
            {'country_code': 'KG', 'country_name': 'Кыргызстан', 'phone_code': '+996'},
        ]
        
        for country_data in countries_data:
            country = Country(**country_data)
            db.add(country)
        
        db.flush()
        
        # Получаем Казахстан для добавления регионов
        kz_country = db.query(Country).filter_by(country_code='KZ').first()
        
        # Регионы Казахстана
        regions_data = [
            {'region_name': 'Алматинская область', 'country_id': kz_country.country_id, 'region_code': 'ALM'},
            {'region_name': 'Нур-Султан', 'country_id': kz_country.country_id, 'region_code': 'NUR'},
            {'region_name': 'Алматы', 'country_id': kz_country.country_id, 'region_code': 'ALA'},
            {'region_name': 'Шымкент', 'country_id': kz_country.country_id, 'region_code': 'SHY'},
            {'region_name': 'Актобе', 'country_id': kz_country.country_id, 'region_code': 'AKT'},
            {'region_name': 'Караганда', 'country_id': kz_country.country_id, 'region_code': 'KAR'},
            {'region_name': 'Атырау', 'country_id': kz_country.country_id, 'region_code': 'ATY'},
            {'region_name': 'Костанай', 'country_id': kz_country.country_id, 'region_code': 'KOS'},
            {'region_name': 'Павлодар', 'country_id': kz_country.country_id, 'region_code': 'PAV'},
            {'region_name': 'Петропавловск', 'country_id': kz_country.country_id, 'region_code': 'PET'},
            {'region_name': 'Усть-Каменогорск', 'country_id': kz_country.country_id, 'region_code': 'UST'},
            {'region_name': 'Уральск', 'country_id': kz_country.country_id, 'region_code': 'URA'},
            {'region_name': 'Тараз', 'country_id': kz_country.country_id, 'region_code': 'TAR'},
            {'region_name': 'Кызылорда', 'country_id': kz_country.country_id, 'region_code': 'KYZ'},
            {'region_name': 'Актау', 'country_id': kz_country.country_id, 'region_code': 'AKA'},
        ]
        
        for region_data in regions_data:
            region = Region(**region_data)
            db.add(region)
        
        db.flush()
        
        # Добавляем крупные города
        alm_region = db.query(Region).filter_by(region_name='Алматы').first()
        nur_region = db.query(Region).filter_by(region_name='Нур-Султан').first()
        shy_region = db.query(Region).filter_by(region_name='Шымкент').first()
        
        cities_data = [
            # Алматы
            {'city_name': 'Алматы', 'region_id': alm_region.region_id, 'latitude': 43.2220, 'longitude': 76.8512, 'population': 2000000},
            # Нур-Султан
            {'city_name': 'Нур-Султан', 'region_id': nur_region.region_id, 'latitude': 51.1694, 'longitude': 71.4491, 'population': 1200000},
            # Шымкент
            {'city_name': 'Шымкент', 'region_id': shy_region.region_id, 'latitude': 42.3000, 'longitude': 69.6000, 'population': 1000000},
        ]
        
        for city_data in cities_data:
            city = City(**city_data)
            db.add(city)
        
        db.commit()
        logger.info("Countries and regions seeded successfully!")
        return True
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error seeding countries and regions: {e}")
        return False


def seed_currencies():
    """Заполнение валют"""
    from app.models.payment import Currency
    from app.database import get_db
    
    db = get_db()
    
    try:
        logger.info("Seeding currencies...")
        
        if db.query(Currency).first():
            logger.info("Currencies already exist, skipping...")
            return True
        
        currencies_data = [
            {
                'currency_code': 'KZT',
                'currency_name': 'Казахстанский тенге',
                'symbol': '₸',
                'is_base_currency': True,
                'exchange_rate_to_kzt': 1.0
            },
            {
                'currency_code': 'USD',
                'currency_name': 'Доллар США',
                'symbol': '$',
                'is_base_currency': False,
                'exchange_rate_to_kzt': 480.0
            },
            {
                'currency_code': 'EUR',
                'currency_name': 'Евро',
                'symbol': '€',
                'is_base_currency': False,
                'exchange_rate_to_kzt': 520.0
            },
            {
                'currency_code': 'RUB',
                'currency_name': 'Российский рубль',
                'symbol': '₽',
                'is_base_currency': False,
                'exchange_rate_to_kzt': 5.2
            }
        ]
        
        for currency_data in currencies_data:
            currency = Currency(**currency_data)
            db.add(currency)
        
        db.commit()
        logger.info("Currencies seeded successfully!")
        return True
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error seeding currencies: {e}")
        return False


def seed_categories_and_statuses():
    """Заполнение категорий и статусов"""
    from app.models.category import CategoryTree, Category, StatusGroup, Status
    from app.database import get_db
    
    db = get_db()
    
    try:
        logger.info("Seeding categories and statuses...")
        
        # Деревья категорий
        if not db.query(CategoryTree).first():
            trees_data = [
                {'tree_code': 'auto_categories', 'tree_name': 'Категории автомобилей'},
                {'tree_code': 'parts_categories', 'tree_name': 'Категории запчастей'},
                {'tree_code': 'service_categories', 'tree_name': 'Категории услуг'},
                {'tree_code': 'support_categories', 'tree_name': 'Категории поддержки'},
            ]
            
            for tree_data in trees_data:
                tree = CategoryTree(**tree_data)
                db.add(tree)
            
            db.flush()
        
        # Группы статусов
        if not db.query(StatusGroup).first():
            groups_data = [
                {'group_code': 'listing_status', 'group_name': 'Статусы объявлений'},
                {'group_code': 'user_status', 'group_name': 'Статусы пользователей'},
                {'group_code': 'payment_status', 'group_name': 'Статусы платежей'},
                {'group_code': 'ticket_status', 'group_name': 'Статусы тикетов'},
                {'group_code': 'moderation_status', 'group_name': 'Статусы модерации'},
                {'group_code': 'notification_status', 'group_name': 'Статусы уведомлений'},
            ]
            
            for group_data in groups_data:
                group = StatusGroup(**group_data)
                db.add(group)
            
            db.flush()
            
            # Статусы объявлений
            listing_group = db.query(StatusGroup).filter_by(group_code='listing_status').first()
            listing_statuses = [
                {'group_id': listing_group.group_id, 'status_code': 'draft', 'status_name': 'Черновик', 'status_color': '#gray'},
                {'group_id': listing_group.group_id, 'status_code': 'moderation', 'status_name': 'На модерации', 'status_color': '#orange'},
                {'group_id': listing_group.group_id, 'status_code': 'active', 'status_name': 'Активно', 'status_color': '#green'},
                {'group_id': listing_group.group_id, 'status_code': 'sold', 'status_name': 'Продано', 'status_color': '#blue', 'is_final': True},
                {'group_id': listing_group.group_id, 'status_code': 'archived', 'status_name': 'В архиве', 'status_color': '#gray', 'is_final': True},
                {'group_id': listing_group.group_id, 'status_code': 'rejected', 'status_name': 'Отклонено', 'status_color': '#red', 'is_final': True},
                {'group_id': listing_group.group_id, 'status_code': 'expired', 'status_name': 'Истек срок', 'status_color': '#orange'},
            ]
            
            for status_data in listing_statuses:
                status = Status(**status_data)
                db.add(status)
            
            # Статусы пользователей
            user_group = db.query(StatusGroup).filter_by(group_code='user_status').first()
            user_statuses = [
                {'group_id': user_group.group_id, 'status_code': 'active', 'status_name': 'Активный', 'status_color': '#green'},
                {'group_id': user_group.group_id, 'status_code': 'blocked', 'status_name': 'Заблокирован', 'status_color': '#red'},
                {'group_id': user_group.group_id, 'status_code': 'suspended', 'status_name': 'Приостановлен', 'status_color': '#orange'},
                {'group_id': user_group.group_id, 'status_code': 'pending', 'status_name': 'Ожидает верификации', 'status_color': '#yellow'},
            ]
            
            for status_data in user_statuses:
                status = Status(**status_data)
                db.add(status)
            
            # Статусы платежей
            payment_group = db.query(StatusGroup).filter_by(group_code='payment_status').first()
            payment_statuses = [
                {'group_id': payment_group.group_id, 'status_code': 'pending', 'status_name': 'Ожидает оплаты', 'status_color': '#yellow'},
                {'group_id': payment_group.group_id, 'status_code': 'success', 'status_name': 'Успешно', 'status_color': '#green'},
                {'group_id': payment_group.group_id, 'status_code': 'failed', 'status_name': 'Неудачно', 'status_color': '#red'},
                {'group_id': payment_group.group_id, 'status_code': 'refunded', 'status_name': 'Возвращено', 'status_color': '#blue'},
            ]
            
            for status_data in payment_statuses:
                status = Status(**status_data)
                db.add(status)
            
            # Статусы тикетов
            ticket_group = db.query(StatusGroup).filter_by(group_code='ticket_status').first()
            ticket_statuses = [
                {'group_id': ticket_group.group_id, 'status_code': 'open', 'status_name': 'Открыт', 'status_color': '#orange'},
                {'group_id': ticket_group.group_id, 'status_code': 'in_progress', 'status_name': 'В работе', 'status_color': '#blue'},
                {'group_id': ticket_group.group_id, 'status_code': 'resolved', 'status_name': 'Решен', 'status_color': '#green'},
                {'group_id': ticket_group.group_id, 'status_code': 'closed', 'status_name': 'Закрыт', 'status_color': '#gray'},
            ]
            
            for status_data in ticket_statuses:
                status = Status(**status_data)
                db.add(status)
        
        db.commit()
        logger.info("Categories and statuses seeded successfully!")
        return True
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error seeding categories and statuses: {e}")
        return False


def seed_car_references():
    """Заполнение автомобильных справочников"""
    from app.models.car import (
        CarBrand, CarModel, CarBodyType, CarEngineType, 
        CarTransmissionType, CarDriveType, CarColor, CarAttributeGroup, CarAttribute
    )
    from app.database import get_db
    
    db = get_db()
    
    try:
        logger.info("Seeding car references...")
        
        # Типы кузова
        if not db.query(CarBodyType).first():
            body_types = [
                'Седан', 'Хэтчбек', 'Универсал', 'Лифтбек', 'Купе', 'Кабриолет',
                'Родстер', 'Тарга', 'Лимузин', 'Внедорожник', 'Кроссовер', 
                'Пикап', 'Фургон', 'Минивэн', 'Компактвэн'
            ]
            
            for i, body_type in enumerate(body_types, 1):
                bt = CarBodyType(body_type_name=body_type, sort_order=i)
                db.add(bt)
        
        # Типы двигателей
        if not db.query(CarEngineType).first():
            engine_types = ['Бензин', 'Дизель', 'Гибрид', 'Электро', 'Газ', 'Газ/Бензин']
            
            for i, engine_type in enumerate(engine_types, 1):
                et = CarEngineType(engine_type_name=engine_type, sort_order=i)
                db.add(et)
        
        # Типы трансмиссии
        if not db.query(CarTransmissionType).first():
            transmission_types = ['Механика', 'Автомат', 'Робот', 'Вариатор']
            
            for i, transmission in enumerate(transmission_types, 1):
                tt = CarTransmissionType(transmission_name=transmission, sort_order=i)
                db.add(tt)
        
        # Типы привода
        if not db.query(CarDriveType).first():
            drive_types = ['Передний', 'Задний', 'Полный']
            
            for i, drive_type in enumerate(drive_types, 1):
                dt = CarDriveType(drive_type_name=drive_type, sort_order=i)
                db.add(dt)
        
        # Цвета
        if not db.query(CarColor).first():
            colors = [
                ('Белый', '#FFFFFF'), ('Черный', '#000000'), ('Серый', '#808080'),
                ('Серебристый', '#C0C0C0'), ('Красный', '#FF0000'), ('Синий', '#0000FF'),
                ('Зеленый', '#008000'), ('Желтый', '#FFFF00'), ('Оранжевый', '#FFA500'),
                ('Коричневый', '#8B4513'), ('Бежевый', '#F5F5DC'), ('Золотистый', '#FFD700'),
                ('Фиолетовый', '#800080'), ('Розовый', '#FFC0CB')
            ]
            
            for i, (color_name, color_hex) in enumerate(colors, 1):
                color = CarColor(color_name=color_name, color_hex=color_hex, sort_order=i)
                db.add(color)
        
        # Группы атрибутов
        if not db.query(CarAttributeGroup).first():
            groups = [
                ('basic', 'Основные характеристики', 1),
                ('engine', 'Двигатель', 2),
                ('transmission', 'Трансмиссия', 3),
                ('exterior', 'Экстерьер', 4),
                ('interior', 'Интерьер', 5),
                ('safety', 'Безопасность', 6),
                ('comfort', 'Комфорт', 7),
                ('multimedia', 'Мультимедиа', 8),
            ]
            
            for group_code, group_name, sort_order in groups:
                group = CarAttributeGroup(
                    group_code=group_code,
                    group_name=group_name,
                    sort_order=sort_order
                )
                db.add(group)
            
            db.flush()
            
            # Атрибуты
            basic_group = db.query(CarAttributeGroup).filter_by(group_code='basic').first()
            engine_group = db.query(CarAttributeGroup).filter_by(group_code='engine').first()
            transmission_group = db.query(CarAttributeGroup).filter_by(group_code='transmission').first()
            
            attributes = [
                # Основные
                (basic_group.group_id, 'year', 'Год выпуска', 'number', True, True, True),
                (basic_group.group_id, 'mileage', 'Пробег (км)', 'number', True, True, True),
                (basic_group.group_id, 'condition', 'Состояние', 'string', True, True, True),
                (basic_group.group_id, 'brand_id', 'Марка', 'reference', True, True, True),
                (basic_group.group_id, 'model_id', 'Модель', 'reference', True, True, True),
                (basic_group.group_id, 'generation_id', 'Поколение', 'reference', False, True, True),
                (basic_group.group_id, 'body_type_id', 'Тип кузова', 'reference', True, True, True),
                (basic_group.group_id, 'color_id', 'Цвет', 'reference', False, True, True),
                (basic_group.group_id, 'vin_number', 'VIN номер', 'string', False, False, False),
                (basic_group.group_id, 'customs_cleared', 'Растаможен', 'boolean', False, True, True),
                
                # Двигатель
                (engine_group.group_id, 'engine_volume', 'Объем двигателя (л)', 'number', False, True, True),
                (engine_group.group_id, 'engine_type_id', 'Тип двигателя', 'reference', False, True, True),
                (engine_group.group_id, 'power_hp', 'Мощность (л.с.)', 'number', False, True, True),
                (engine_group.group_id, 'fuel_consumption', 'Расход топлива', 'number', False, False, False),
                
                # Трансмиссия
                (transmission_group.group_id, 'transmission_id', 'Коробка передач', 'reference', False, True, True),
                (transmission_group.group_id, 'drive_type_id', 'Привод', 'reference', False, True, True),
            ]
            
            for group_id, attr_code, attr_name, attr_type, required, searchable, filterable in attributes:
                attribute = CarAttribute(
                    group_id=group_id,
                    attribute_code=attr_code,
                    attribute_name=attr_name,
                    attribute_type=attr_type,
                    is_required=required,
                    is_searchable=searchable,
                    is_filterable=filterable
                )
                db.add(attribute)
        
        # Популярные марки
        if not db.query(CarBrand).first():
            brands = [
                'Toyota', 'Volkswagen', 'Hyundai', 'Kia', 'Nissan', 'Honda', 'Mazda',
                'Subaru', 'Mitsubishi', 'Suzuki', 'BMW', 'Mercedes-Benz', 'Audi',
                'Lexus', 'Infiniti', 'Acura', 'Ford', 'Chevrolet', 'Opel', 'Skoda',
                'Peugeot', 'Renault', 'Citroen', 'Volvo', 'LADA', 'UAZ', 'GAZ',
                'Daewoo', 'SsangYong', 'Geely', 'Chery', 'BYD', 'Great Wall'
            ]
            
            for i, brand_name in enumerate(brands, 1):
                brand = CarBrand(
                    brand_name=brand_name,
                    brand_slug=brand_name.lower().replace('-', '_').replace(' ', '_'),
                    sort_order=i
                )
                db.add(brand)
            
            db.flush()
            
            # Добавляем популярные модели для Toyota
            toyota = db.query(CarBrand).filter_by(brand_name='Toyota').first()
            if toyota:
                toyota_models = [
                    'Camry', 'Corolla', 'RAV4', 'Highlander', 'Prius', 'Land Cruiser',
                    'Prado', 'Avensis', 'Yaris', 'Auris', 'C-HR', 'Fortuner'
                ]
                
                for i, model_name in enumerate(toyota_models, 1):
                    model = CarModel(
                        brand_id=toyota.brand_id,
                        model_name=model_name,
                        model_slug=f"toyota_{model_name.lower().replace('-', '_')}",
                        start_year=2000,
                        sort_order=i
                    )
                    db.add(model)
        
        db.commit()
        logger.info("Car references seeded successfully!")
        return True
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error seeding car references: {e}")
        return False


def seed_notification_channels():
    """Заполнение каналов уведомлений"""
    from app.models.notification import NotificationChannel, NotificationTemplate
    from app.database import get_db
    
    db = get_db()
    
    try:
        logger.info("Seeding notification channels...")
        
        if not db.query(NotificationChannel).first():
            channels = [
                ('push', 'Push-уведомления'),
                ('email', 'Email'),
                ('sms', 'SMS'),
                ('in_app', 'Внутри приложения'),
            ]
            
            for channel_code, channel_name in channels:
                channel = NotificationChannel(
                    channel_code=channel_code,
                    channel_name=channel_name
                )
                db.add(channel)
            
            db.flush()
            
            # Шаблоны уведомлений
            email_channel = db.query(NotificationChannel).filter_by(channel_code='email').first()
            push_channel = db.query(NotificationChannel).filter_by(channel_code='push').first()
            
            templates = [
                {
                    'template_code': 'welcome_email',
                    'template_name': 'Добро пожаловать',
                    'channel_id': email_channel.channel_id,
                    'subject_template': 'Добро пожаловать на Kolesa.kz!',
                    'body_template': 'Здравствуйте, {{first_name}}! Добро пожаловать на Kolesa.kz!',
                    'variables': {'first_name': 'Имя пользователя'}
                },
                {
                    'template_code': 'new_message',
                    'template_name': 'Новое сообщение',
                    'channel_id': push_channel.channel_id,
                    'body_template': 'У вас новое сообщение от {{sender_name}}',
                    'variables': {'sender_name': 'Имя отправителя'}
                },
                {
                    'template_code': 'listing_expired',
                    'template_name': 'Объявление истекло',
                    'channel_id': push_channel.channel_id,
                    'body_template': 'Срок действия вашего объявления "{{listing_title}}" истек',
                    'variables': {'listing_title': 'Заголовок объявления'}
                }
            ]
            
            for template_data in templates:
                template = NotificationTemplate(**template_data)
                db.add(template)
        
        db.commit()
        logger.info("Notification channels seeded successfully!")
        return True
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error seeding notification channels: {e}")
        return False


def seed_promotion_services():
    """Заполнение услуг продвижения"""
    from app.models.payment import PromotionService, Currency
    from app.database import get_db
    
    db = get_db()
    
    try:
        logger.info("Seeding promotion services...")
        
        if not db.query(PromotionService).first():
            kzt_currency = db.query(Currency).filter_by(currency_code='KZT').first()
            
            services = [
                {
                    'service_code': 'vip',
                    'service_name': 'VIP размещение',
                    'description': 'Объявление в топе результатов поиска',
                    'price': 2000,
                    'currency_id': kzt_currency.currency_id,
                    'duration_days': 30,
                    'features': {'top_placement': True, 'highlight': True},
                    'sort_order': 1
                },
                {
                    'service_code': 'featured',
                    'service_name': 'Выделенное объявление',
                    'description': 'Выделение цветом в списке',
                    'price': 1000,
                    'currency_id': kzt_currency.currency_id,
                    'duration_days': 15,
                    'features': {'highlight': True},
                    'sort_order': 2
                },
                {
                    'service_code': 'boost',
                    'service_name': 'Поднятие в поиске',
                    'description': 'Обновление даты публикации',
                    'price': 500,
                    'currency_id': kzt_currency.currency_id,
                    'duration_days': 7,
                    'features': {'date_boost': True},
                    'sort_order': 3
                },
                {
                    'service_code': 'urgent',
                    'service_name': 'Срочная продажа',
                    'description': 'Отметка "Срочно"',
                    'price': 300,
                    'currency_id': kzt_currency.currency_id,
                    'duration_days': 7,
                    'features': {'urgent_badge': True},
                    'sort_order': 4
                }
            ]
            
            for service_data in services:
                service = PromotionService(**service_data)
                db.add(service)
        
        db.commit()
        logger.info("Promotion services seeded successfully!")
        return True
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error seeding promotion services: {e}")
        return False


def create_admin_user():
    """Создание администратора"""
    from app.models.user import User, UserProfile
    from app.models.base import GlobalEntity
    from app.database import get_db
    from werkzeug.security import generate_password_hash
    
    db = get_db()
    
    try:
        logger.info("Creating admin user...")
        
        # Проверяем, не создан ли уже админ
        admin = db.query(User).filter_by(user_type='admin').first()
        if admin:
            logger.info("Admin user already exists, skipping...")
            return True
        
        # Создаем сущность
        entity = GlobalEntity(entity_type='user')
        db.add(entity)
        db.flush()
        
        # Создаем администратора
        admin_user = User(
            entity_id=entity.entity_id,
            phone_number='+77001234567',
            email='admin@kolesa.kz',
            password_hash=generate_password_hash('admin123456'),
            first_name='Администратор',
            last_name='Системы',
            user_type='admin',
            verification_status='fully_verified'
        )
        
        db.add(admin_user)
        db.flush()
        
        # Создаем профиль
        admin_profile = UserProfile(
            user_id=admin_user.user_id,
            company_name='Kolesa.kz',
            description='Системный администратор'
        )
        
        db.add(admin_profile)
        db.commit()
        
        logger.info(f"Admin user created with ID: {admin_user.user_id}")
        logger.info("Login: admin@kolesa.kz / +77001234567")
        logger.info("Password: admin123456")
        
        return True
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating admin user: {e}")
        return False


def seed_sample_data():
    """Заполнение примерами данных для демонстрации"""
    from app.models.user import User, UserProfile
    from app.models.listing import Listing, ListingDetails
    from app.models.base import GlobalEntity
    from app.models.car import CarBrand, CarModel
    from app.models.location import City
    from app.models.category import Status, StatusGroup
    from app.database import get_db
    from werkzeug.security import generate_password_hash
    import random
    
    db = get_db()
    
    try:
        logger.info("Seeding sample data...")
        
        # Проверяем, есть ли уже тестовые пользователи
        if db.query(User).filter(User.user_type != 'admin').first():
            logger.info("Sample data already exists, skipping...")
            return True
        
        # Получаем необходимые данные
        cities = db.query(City).all()
        brands = db.query(CarBrand).all()
        active_status = db.query(Status).join(StatusGroup).filter(
            StatusGroup.group_code == 'listing_status',
            Status.status_code == 'active'
        ).first()
        
        if not all([cities, brands, active_status]):
            logger.warning("Required reference data not found, skipping sample data")
            return True
        
        # Создаем тестовых пользователей
        sample_users = [
            {
                'phone_number': '+77012345678',
                'email': 'user1@example.com',
                'first_name': 'Айдар',
                'last_name': 'Нурланов',
                'company_name': 'Auto Sale KZ'
            },
            {
                'phone_number': '+77012345679',
                'email': 'user2@example.com',
                'first_name': 'Мария',
                'last_name': 'Петрова',
                'company_name': None
            },
            {
                'phone_number': '+77012345680',
                'email': 'dealer@example.com',
                'first_name': 'Сергей',
                'last_name': 'Иванов',
                'company_name': 'Premium Motors',
                'user_type': 'dealer'
            }
        ]
        
        created_users = []
        for user_data in sample_users:
            # Создаем сущность
            entity = GlobalEntity(entity_type='user')
            db.add(entity)
            db.flush()
            
            # Создаем пользователя
            user = User(
                entity_id=entity.entity_id,
                phone_number=user_data['phone_number'],
                email=user_data['email'],
                password_hash=generate_password_hash('password123'),
                first_name=user_data['first_name'],
                last_name=user_data['last_name'],
                user_type=user_data.get('user_type', 'regular'),
                verification_status='fully_verified'
            )
            db.add(user)
            db.flush()
            
            # Создаем профиль
            profile = UserProfile(
                user_id=user.user_id,
                company_name=user_data.get('company_name'),
                city_id=random.choice(cities).city_id,
                description=f"Продаю автомобили в {random.choice(cities).city_name}"
            )
            db.add(profile)
            created_users.append(user)
        
        db.flush()
        
        # Создаем тестовые объявления
        sample_listings = [
            {
                'title': 'Toyota Camry 2018, отличное состояние',
                'description': 'Продается Toyota Camry 2018 года в отличном состоянии. Один владелец, все ТО пройдены вовремя.',
                'price': 8500000,
                'brand_name': 'Toyota',
                'model_name': 'Camry',
                'year': 2018,
                'mileage': 85000
            },
            {
                'title': 'Hyundai Elantra 2020, как новая',
                'description': 'Почти новая Hyundai Elantra 2020 года. Пробег всего 25000 км.',
                'price': 7200000,
                'brand_name': 'Hyundai',
                'model_name': 'Elantra',
                'year': 2020,
                'mileage': 25000
            },
            {
                'title': 'BMW X5 2017, полная комплектация',
                'description': 'BMW X5 в максимальной комплектации. Состояние отличное, все опции работают.',
                'price': 15000000,
                'brand_name': 'BMW',
                'model_name': 'X5',
                'year': 2017,
                'mileage': 120000
            }
        ]
        
        for i, listing_data in enumerate(sample_listings):
            # Находим марку и модель
            brand = db.query(CarBrand).filter_by(brand_name=listing_data['brand_name']).first()
            if not brand:
                continue
            
            model = db.query(CarModel).filter_by(
                brand_id=brand.brand_id,
                model_name=listing_data['model_name']
            ).first()
            
            # Создаем сущность объявления
            entity = GlobalEntity(entity_type='listing')
            db.add(entity)
            db.flush()
            
            # Создаем объявление
            listing = Listing(
                entity_id=entity.entity_id,
                user_id=created_users[i % len(created_users)].user_id,
                listing_type_id=1,  # car_listing
                title=listing_data['title'],
                description=listing_data['description'],
                price=listing_data['price'],
                currency_id=1,  # KZT
                city_id=random.choice(cities).city_id,
                status_id=active_status.status_id,
                published_date=datetime.utcnow(),
                view_count=random.randint(10, 500)
            )
            db.add(listing)
            db.flush()
            
            # Создаем детали объявления
            details = ListingDetails(
                listing_id=listing.listing_id,
                listing_type_id=1,
                searchable_fields={
                    'brand_id': brand.brand_id if brand else None,
                    'model_id': model.model_id if model else None,
                    'year': listing_data['year'],
                    'mileage': listing_data['mileage'],
                    'condition': 'excellent'
                }
            )
            db.add(details)
        
        db.commit()
        logger.info("Sample data seeded successfully!")
        return True
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error seeding sample data: {e}")
        return False


def verify_database_integrity():
    """Проверка целостности базы данных"""
    from app.database import get_db
    
    db = get_db()
    
    try:
        logger.info("Verifying database integrity...")
        
        # Проверяем основные таблицы
        from app.models.user import User
        from app.models.location import Country, Region, City
        from app.models.car import CarBrand
        from app.models.payment import Currency
        from app.models.category import StatusGroup, Status
        
        checks = [
            ('Users', User),
            ('Countries', Country),
            ('Regions', Region), 
            ('Cities', City),
            ('Car Brands', CarBrand),
            ('Currencies', Currency),
            ('Status Groups', StatusGroup),
            ('Statuses', Status)
        ]
        
        for check_name, model in checks:
            count = db.query(model).count()
            logger.info(f"{check_name}: {count} records")
            
            if count == 0 and check_name != 'Users':
                logger.warning(f"No records found in {check_name}")
        
        # Проверяем связи
        admin_count = db.query(User).filter_by(user_type='admin').count()
        logger.info(f"Admin users: {admin_count}")
        
        if admin_count == 0:
            logger.warning("No admin users found!")
        
        logger.info("Database integrity check completed!")
        return True
        
    except Exception as e:
        logger.error(f"Error checking database integrity: {e}")
        return False


def cleanup_and_optimize():
    """Очистка и оптимизация базы данных"""
    from app.database import get_db, engine
    
    try:
        logger.info("Performing database cleanup and optimization...")
        
        # Обновляем статистику PostgreSQL
        with engine.connect() as conn:
            conn.execute("ANALYZE;")
            conn.commit()
        
        logger.info("Database optimization completed!")
        return True
        
    except Exception as e:
        logger.error(f"Error during database optimization: {e}")
        return False


def main():
    """Основная функция инициализации"""
    logger.info("Starting database initialization...")
    logger.info("=" * 60)
    
    # Создаем приложение
    app = create_app()
    
    with app.app_context():
        try:
            # Пошаговая инициализация
            steps = [
                ("Creating tables", create_tables),
                ("Seeding countries and regions", seed_countries_and_regions),
                ("Seeding currencies", seed_currencies),
                ("Seeding categories and statuses", seed_categories_and_statuses),
                ("Seeding car references", seed_car_references),
                ("Seeding notification channels", seed_notification_channels),
                ("Seeding promotion services", seed_promotion_services),
                ("Creating admin user", create_admin_user),
                ("Seeding sample data", seed_sample_data),
                ("Verifying database integrity", verify_database_integrity),
                ("Cleanup and optimization", cleanup_and_optimize),
            ]
            
            success_count = 0
            total_steps = len(steps)
            
            for i, (step_name, step_func) in enumerate(steps, 1):
                logger.info(f"[{i}/{total_steps}] {step_name}...")
                try:
                    if step_func():
                        success_count += 1
                        logger.info(f"✓ {step_name} completed successfully")
                    else:
                        logger.error(f"✗ {step_name} failed")
                        if step_name in ["Creating tables", "Creating admin user"]:
                            logger.error("Critical step failed, aborting...")
                            return False
                except Exception as e:
                    logger.error(f"✗ {step_name} failed with exception: {e}")
                    if step_name in ["Creating tables", "Creating admin user"]:
                        logger.error("Critical step failed, aborting...")
                        return False
                
                logger.info("-" * 40)
            
            logger.info("=" * 60)
            logger.info(f"Database initialization completed!")
            logger.info(f"Successfully completed: {success_count}/{total_steps} steps")
            
            if success_count == total_steps:
                logger.info("🎉 All steps completed successfully!")
                logger.info("")
                logger.info("Admin credentials:")
                logger.info("  Email: admin@kolesa.kz")
                logger.info("  Phone: +77001234567")
                logger.info("  Password: admin123456")
                logger.info("")
                logger.info("Sample user credentials:")
                logger.info("  Email: user1@example.com")
                logger.info("  Phone: +77012345678") 
                logger.info("  Password: password123")
                return True
            else:
                logger.warning(f"Some steps failed ({total_steps - success_count} failures)")
                return False
            
        except Exception as e:
            logger.error(f"Database initialization failed: {e}")
            return False


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Initialize Kolesa.kz database',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/init_db.py                    # Initialize database
  python scripts/init_db.py --reset            # Reset and initialize
  python scripts/init_db.py --reset --force    # Reset without confirmation
  python scripts/init_db.py --sample-only      # Only create sample data
  python scripts/init_db.py --verify           # Only verify integrity
        """
    )
    
    parser.add_argument('--reset', action='store_true', 
                       help='Reset database before initialization')
    parser.add_argument('--force', action='store_true', 
                       help='Force initialization without confirmation')
    parser.add_argument('--sample-only', action='store_true',
                       help='Only create sample data (requires existing DB)')
    parser.add_argument('--verify', action='store_true',
                       help='Only verify database integrity')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Enable verbose logging')
    
    args = parser.parse_args()
    
    # Настройка уровня логирования
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Обработка флагов
    if args.verify:
        app = create_app()
        with app.app_context():
            if verify_database_integrity():
                logger.info("Database verification completed successfully!")
                sys.exit(0)
            else:
                logger.error("Database verification failed!")
                sys.exit(1)
    
    if args.sample_only:
        app = create_app()
        with app.app_context():
            if seed_sample_data():
                logger.info("Sample data creation completed successfully!")
                sys.exit(0)
            else:
                logger.error("Sample data creation failed!")
                sys.exit(1)
    
    if args.reset:
        if not args.force:
            print("⚠️  WARNING: This will delete all existing data!")
            print("   - All user accounts will be removed")
            print("   - All listings will be deleted") 
            print("   - All messages and conversations will be lost")
            print("   - All payment history will be removed")
            print("")
            confirm = input("Are you sure you want to continue? (y/N): ")
            if confirm.lower() != 'y':
                logger.info("Operation cancelled by user")
                sys.exit(0)
        
        logger.info("Resetting database...")
        app = create_app()
        with app.app_context():
            if not reset_db():
                logger.error("Failed to reset database")
                sys.exit(1)
    
    # Запускаем инициализацию
    start_time = datetime.now()
    
    if main():
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        logger.info(f"Database initialization completed in {duration:.2f} seconds!")
        sys.exit(0)
    else:
        logger.error("Database initialization failed!")
        sys.exit(1)