"""
Database connection and base models for Kolesa.kz Backend
"""

from datetime import datetime
from sqlalchemy import create_engine, MetaData, event
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.pool import StaticPool
from flask import current_app, g
import logging

# Настройка логирования для SQLAlchemy
logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)

# Метаданные для автоматического именования ограничений
metadata = MetaData(naming_convention={
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s"
})

# Базовая модель
Base = declarative_base(metadata=metadata)

# Глобальные переменные для сессий
engine = None
SessionLocal = None


class DatabaseManager:
    """Менеджер для управления подключениями к базе данных"""
    
    def __init__(self, app=None):
        self.app = app
        if app is not None:
            self.init_app(app)
    
    def init_app(self, app):
        """Инициализация расширения с приложением Flask"""
        global engine, SessionLocal
        
        database_url = app.config.get('DATABASE_URL')
        if not database_url:
            raise ValueError("DATABASE_URL must be set in configuration")
        
        # Создание движка
        engine_kwargs = {
            'echo': app.config.get('SQLALCHEMY_ECHO', False),
            'pool_pre_ping': True,
            'pool_recycle': 3600,
        }
        
        # Дополнительные настройки для PostgreSQL
        if 'postgresql' in database_url:
            engine_kwargs.update({
                'pool_size': app.config.get('SQLALCHEMY_POOL_SIZE', 10),
                'max_overflow': app.config.get('SQLALCHEMY_MAX_OVERFLOW', 20),
                'pool_timeout': app.config.get('SQLALCHEMY_POOL_TIMEOUT', 30),
            })
        
        engine = create_engine(database_url, **engine_kwargs)
        
        # Создание фабрики сессий
        SessionLocal = scoped_session(sessionmaker(
            bind=engine,
            expire_on_commit=False,
            autoflush=True,
            autocommit=False
        ))
        
        # Регистрация функций для работы с сессиями
        app.teardown_appcontext(self.close_db)
        
        # Регистрация команд CLI
        app.cli.add_command(init_db_command)
        app.cli.add_command(reset_db_command)
        
        # Настройка событий SQLAlchemy
        self._setup_events()
    
    def _setup_events(self):
        """Настройка событий SQLAlchemy"""
        @event.listens_for(engine, "connect")
        def set_sqlite_pragma(dbapi_connection, connection_record):
            if 'sqlite' in str(engine.url):
                cursor = dbapi_connection.cursor()
                cursor.execute("PRAGMA foreign_keys=ON")
                cursor.close()
        
        @event.listens_for(engine, "begin")
        def receive_begin(conn):
            # Можно добавить логику для начала транзакции
            pass
    
    def get_db(self):
        """Получение сессии базы данных"""
        if 'db' not in g:
            g.db = SessionLocal()
        return g.db
    
    def close_db(self, error=None):
        """Закрытие сессии базы данных"""
        db = g.pop('db', None)
        if db is not None:
            try:
                if error:
                    db.rollback()
                else:
                    db.commit()
            except Exception as e:
                current_app.logger.error(f"Error closing database session: {e}")
                db.rollback()
            finally:
                db.close()


# Глобальный экземпляр менеджера
db_manager = DatabaseManager()


def get_db():
    """Функция для получения сессии базы данных"""
    return db_manager.get_db()


def init_db():
    """Инициализация базы данных"""
    from app.models import (
        user, location, category, listing, car, 
        conversation, media, notification, payment, 
        review, support
    )
    
    try:
        # Создание всех таблиц
        Base.metadata.create_all(bind=engine)
        current_app.logger.info("Database tables created successfully")
        
        # Заполнение базовыми данными
        seed_basic_data()
        
        return True
    except Exception as e:
        current_app.logger.error(f"Error initializing database: {e}")
        return False


def reset_db():
    """Сброс базы данных"""
    try:
        Base.metadata.drop_all(bind=engine)
        current_app.logger.info("Database tables dropped successfully")
        return init_db()
    except Exception as e:
        current_app.logger.error(f"Error resetting database: {e}")
        return False


def seed_basic_data():
    """Заполнение базы данных базовыми справочными данными"""
    from app.models.location import Country, Region, City
    from app.models.category import CategoryTree, Status, StatusGroup
    from app.models.car import (
        CarBrand, CarBodyType, CarEngineType, 
        CarTransmissionType, CarDriveType, CarColor
    )
    
    db = SessionLocal()
    try:
        # Проверяем, не заполнена ли уже база
        if db.query(Country).first():
            current_app.logger.info("Database already seeded")
            return
        
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
        
        # Регионы Казахстана
        db.flush()  # Получаем ID стран
        kz_country = db.query(Country).filter_by(country_code='KZ').first()
        
        regions_data = [
            {'region_name': 'Алматинская область', 'country_id': kz_country.country_id},
            {'region_name': 'Нур-Султан', 'country_id': kz_country.country_id},
            {'region_name': 'Алматы', 'country_id': kz_country.country_id},
            {'region_name': 'Шымкент', 'country_id': kz_country.country_id},
            {'region_name': 'Актобе', 'country_id': kz_country.country_id},
            {'region_name': 'Караганда', 'country_id': kz_country.country_id},
        ]
        
        for region_data in regions_data:
            region = Region(**region_data)
            db.add(region)
        
        # Группы статусов
        status_groups_data = [
            {'group_code': 'listing_status', 'group_name': 'Статусы объявлений'},
            {'group_code': 'user_status', 'group_name': 'Статусы пользователей'},
            {'group_code': 'payment_status', 'group_name': 'Статусы платежей'},
            {'group_code': 'ticket_status', 'group_name': 'Статусы тикетов'},
            {'group_code': 'moderation_status', 'group_name': 'Статусы модерации'},
        ]
        
        for group_data in status_groups_data:
            group = StatusGroup(**group_data)
            db.add(group)
        
        # Деревья категорий
        category_trees_data = [
            {'tree_code': 'auto_categories', 'tree_name': 'Категории автомобилей'},
            {'tree_code': 'parts_categories', 'tree_name': 'Категории запчастей'},
            {'tree_code': 'service_categories', 'tree_name': 'Категории услуг'},
        ]
        
        for tree_data in category_trees_data:
            tree = CategoryTree(**tree_data)
            db.add(tree)
        
        # Типы кузова
        body_types_data = [
            'Седан', 'Хэтчбек', 'Универсал', 'Внедорожник', 
            'Кроссовер', 'Купе', 'Кабриолет', 'Минивэн', 'Пикап'
        ]
        
        for i, body_type in enumerate(body_types_data):
            bt = CarBodyType(body_type_name=body_type, sort_order=i+1)
            db.add(bt)
        
        # Типы двигателей
        engine_types_data = ['Бензин', 'Дизель', 'Гибрид', 'Электро', 'Газ']
        
        for i, engine_type in enumerate(engine_types_data):
            et = CarEngineType(engine_type_name=engine_type, sort_order=i+1)
            db.add(et)
        
        # Типы трансмиссии
        transmission_types_data = ['Механика', 'Автомат', 'Робот', 'Вариатор']
        
        for i, transmission_type in enumerate(transmission_types_data):
            tt = CarTransmissionType(transmission_name=transmission_type, sort_order=i+1)
            db.add(tt)
        
        # Типы привода
        drive_types_data = ['Передний', 'Задний', 'Полный']
        
        for i, drive_type in enumerate(drive_types_data):
            dt = CarDriveType(drive_type_name=drive_type, sort_order=i+1)
            db.add(dt)
        
        # Цвета
        colors_data = [
            ('Белый', '#FFFFFF'), ('Черный', '#000000'), ('Серый', '#808080'),
            ('Серебристый', '#C0C0C0'), ('Красный', '#FF0000'), ('Синий', '#0000FF'),
            ('Зеленый', '#008000'), ('Желтый', '#FFFF00')
        ]
        
        for i, (color_name, color_hex) in enumerate(colors_data):
            color = CarColor(color_name=color_name, color_hex=color_hex, sort_order=i+1)
            db.add(color)
        
        # Популярные марки автомобилей
        brands_data = [
            'Toyota', 'Volkswagen', 'Hyundai', 'Kia', 'Nissan',
            'Honda', 'Mazda', 'Subaru', 'Mitsubishi', 'Suzuki',
            'BMW', 'Mercedes-Benz', 'Audi', 'Lexus', 'Infiniti'
        ]
        
        for i, brand_name in enumerate(brands_data):
            brand = CarBrand(
                brand_name=brand_name,
                brand_slug=brand_name.lower().replace('-', '_'),
                sort_order=i+1
            )
            db.add(brand)
        
        db.commit()
        current_app.logger.info("Basic reference data seeded successfully")
        
    except Exception as e:
        db.rollback()
        current_app.logger.error(f"Error seeding basic data: {e}")
        raise
    finally:
        db.close()


# Команды CLI
import click

@click.command()
def init_db_command():
    """Создание таблиц базы данных"""
    if init_db():
        click.echo("Database initialized successfully!")
    else:
        click.echo("Error initializing database!")


@click.command()
def reset_db_command():
    """Сброс и пересоздание базы данных"""
    if click.confirm('This will delete all data. Are you sure?'):
        if reset_db():
            click.echo("Database reset successfully!")
        else:
            click.echo("Error resetting database!")


# Декоратор для автоматического управления сессиями
from functools import wraps

def with_db_session(func):
    """Декоратор для автоматического управления сессией БД"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        db = get_db()
        try:
            result = func(db, *args, **kwargs)
            db.commit()
            return result
        except Exception as e:
            db.rollback()
            current_app.logger.error(f"Database error in {func.__name__}: {e}")
            raise
    return wrapper


# Базовый миксин для моделей
class TimestampMixin:
    """Миксин для добавления временных меток"""
    created_date = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_date = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class SoftDeleteMixin:
    """Миксин для мягкого удаления"""
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    deleted_date = db.Column(db.DateTime)
    
    def soft_delete(self):
        self.is_active = False
        self.deleted_date = datetime.utcnow()
    
    def restore(self):
        self.is_active = True
        self.deleted_date = None


# Хелперы для работы с базой данных
class DatabaseHelpers:
    """Вспомогательные методы для работы с базой данных"""
    
    @staticmethod
    def safe_get_or_create(db, model, **kwargs):
        """Безопасное получение или создание объекта"""
        instance = db.query(model).filter_by(**kwargs).first()
        if instance:
            return instance, False
        else:
            instance = model(**kwargs)
            db.add(instance)
            return instance, True
    
    @staticmethod
    def bulk_insert_or_update(db, model, data_list, unique_fields):
        """Массовая вставка или обновление данных"""
        for data in data_list:
            # Формируем условие для поиска существующего объекта
            filter_dict = {field: data[field] for field in unique_fields if field in data}
            instance = db.query(model).filter_by(**filter_dict).first()
            
            if instance:
                # Обновляем существующий объект
                for key, value in data.items():
                    setattr(instance, key, value)
            else:
                # Создаем новый объект
                instance = model(**data)
                db.add(instance)
    
    @staticmethod
    def paginate_query(query, page=1, per_page=20, max_per_page=100):
        """Пагинация запроса"""
        if per_page > max_per_page:
            per_page = max_per_page
        
        total = query.count()
        items = query.offset((page - 1) * per_page).limit(per_page).all()
        
        return {
            'items': items,
            'total': total,
            'page': page,
            'per_page': per_page,
            'pages': (total + per_page - 1) // per_page,
            'has_prev': page > 1,
            'has_next': page * per_page < total
        }


# Экспорт основных компонентов
__all__ = [
    'Base', 'engine', 'SessionLocal', 'db_manager', 'get_db',
    'init_db', 'reset_db', 'with_db_session',
    'TimestampMixin', 'SoftDeleteMixin', 'DatabaseHelpers'
]