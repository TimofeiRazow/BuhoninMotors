# app/models/base.py
from datetime import datetime
from sqlalchemy import Column, Integer, DateTime, Boolean, String, Text, DECIMAL, BigInteger
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.dialects.postgresql import JSONB
from app.extensions import db


class TimestampMixin:
    """Миксин для добавления временных меток"""
    
    @declared_attr
    def created_date(cls):
        return Column(DateTime, default=datetime.utcnow, nullable=False)
    
    @declared_attr
    def updated_date(cls):
        return Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class SoftDeleteMixin:
    """Миксин для мягкого удаления"""
    
    @declared_attr
    def is_active(cls):
        return Column(Boolean, default=True, nullable=False)
    
    def soft_delete(self):
        """Мягкое удаление записи"""
        self.is_active = False
        db.session.commit()
    
    def restore(self):
        """Восстановление записи"""
        self.is_active = True
        db.session.commit()


class BaseModel(TimestampMixin, SoftDeleteMixin, db.Model):
    """Базовая модель с общими полями"""
    __abstract__ = True
    
    def save(self):
        """Сохранение записи"""
        db.session.add(self)
        db.session.commit()
        return self
    
    def delete(self):
        """Жесткое удаление записи"""
        db.session.delete(self)
        db.session.commit()
    
    def to_dict(self, exclude=None):
        """Преобразование в словарь"""
        exclude = exclude or []
        return {
            column.name: getattr(self, column.name)
            for column in self.__table__.columns
            if column.name not in exclude
        }
    
    @classmethod
    def create(cls, **kwargs):
        """Создание новой записи"""
        instance = cls(**kwargs)
        return instance.save()


class GlobalEntity(BaseModel):
    """Глобальный реестр всех сущностей системы"""
    __tablename__ = 'global_entities'
    
    entity_id = Column(BigInteger, primary_key=True)
    entity_type = Column(String(50), nullable=False)
    support_tickets = db.relationship("SupportTicket", back_populates="entity")
    
    __table_args__ = (
        db.CheckConstraint(
            "entity_type IN ('listing', 'user', 'message', 'conversation', 'ticket')",
            name='check_entity_type'
        ),
    )


class EntityType(BaseModel):
    """Типы сущностей для гибкого расширения"""
    __tablename__ = 'entity_types'
    
    type_id = Column(Integer, primary_key=True)
    type_code = Column(String(50), unique=True, nullable=False)
    type_name = Column(String(100), nullable=False)
    parent_type_id = Column(Integer, db.ForeignKey('entity_types.type_id'))
    sort_order = Column(Integer, default=0)
    
    # Отношения
    parent = db.relationship('EntityType', remote_side=[type_id], backref='children')


class StatusGroup(BaseModel):
    """Группы статусов"""
    __tablename__ = 'status_groups'
    
    group_id = Column(Integer, primary_key=True)
    group_code = Column(String(50), unique=True, nullable=False)
    group_name = Column(String(100), nullable=False)
    description = Column(Text)


class Status(BaseModel):
    """Универсальная система статусов"""
    __tablename__ = 'statuses'
    
    status_id = Column(Integer, primary_key=True)
    group_id = Column(Integer, db.ForeignKey('status_groups.group_id'), nullable=False)
    status_code = Column(String(50), nullable=False)
    status_name = Column(String(100), nullable=False)
    status_color = Column(String(7))  # HEX цвет
    is_final = Column(Boolean, default=False)
    sort_order = Column(Integer, default=0)
    
    # Отношения
    group = db.relationship('StatusGroup', backref='statuses')
    
    __table_args__ = (
        db.UniqueConstraint('group_id', 'status_code', name='unique_group_status'),
    )


class Currency(BaseModel):
    """Валюты и курсы"""
    __tablename__ = 'currencies'
    
    currency_id = Column(Integer, primary_key=True)
    currency_code = Column(String(3), unique=True, nullable=False)
    currency_name = Column(String(50), nullable=False)
    symbol = Column(String(10))
    exchange_rate_to_kzt = Column(DECIMAL(15, 6), default=1)
    is_base_currency = Column(Boolean, default=False)
    last_updated = Column(DateTime, default=datetime.utcnow)


class CategoryTree(BaseModel):
    """Деревья категорий"""
    __tablename__ = 'category_trees'
    
    tree_id = Column(Integer, primary_key=True)
    tree_code = Column(String(50), unique=True, nullable=False)
    tree_name = Column(String(100), nullable=False)
    description = Column(Text)


class Category(BaseModel):
    """Универсальная система категорий с поддержкой ltree"""
    __tablename__ = 'categories'
    
    category_id = Column(Integer, primary_key=True)
    tree_id = Column(Integer, db.ForeignKey('category_trees.tree_id'), nullable=False)
    parent_category_id = Column(Integer, db.ForeignKey('categories.category_id'))
    category_name = Column(String(100), nullable=False)
    category_slug = Column(String(100))
    level = Column(Integer, default=0)
    full_path = Column(Text)  # ltree path для PostgreSQL
    sort_order = Column(Integer, default=0)
    icon_url = Column(String(500))
    description = Column(Text)
    
    # Отношения
    tree = db.relationship('CategoryTree', backref='categories')
    parent = db.relationship('Category', remote_side=[category_id], backref='children')
    
    def get_breadcrumbs(self):
        """Получение хлебных крошек до корневой категории"""
        breadcrumbs = []
        current = self
        while current:
            breadcrumbs.insert(0, current)
            current = current.parent
        return breadcrumbs
    
    def get_descendants(self):
        """Получение всех потомков категории"""
        return Category.query.filter(
            Category.full_path.like(f"{self.full_path}.%")
        ).all() if self.full_path else []


# Абстрактная модель для сущностей с entity_id
class EntityBasedModel(BaseModel):
    """Базовая модель для сущностей, связанных с Global_Entities"""
    __abstract__ = True
    
    @declared_attr
    def entity_id(cls):
        return Column(BigInteger, db.ForeignKey('global_entities.entity_id'), 
                     unique=True, nullable=False)
    
    @declared_attr
    def global_entity(cls):
        return db.relationship('GlobalEntity', backref=cls.__tablename__)


# Вспомогательные функции для работы с моделями
def get_or_create(model, **kwargs):
    """Получить или создать экземпляр модели"""
    instance = model.query.filter_by(**kwargs).first()
    if instance:
        return instance, False
    else:
        instance = model(**kwargs)
        db.session.add(instance)
        db.session.commit()
        return instance, True


def get_status_by_code(group_code, status_code):
    """Получить статус по коду группы и коду статуса"""
    return Status.query.join(StatusGroup).filter(
        StatusGroup.group_code == group_code,
        Status.status_code == status_code
    ).first()


def get_active_statuses(group_code):
    """Получить все активные статусы группы"""
    return Status.query.join(StatusGroup).filter(
        StatusGroup.group_code == group_code,
        Status.is_active == True
    ).order_by(Status.sort_order).all()

# app/models/base.py
"""
Базовые модели для всех таблиц
"""

from datetime import datetime
from sqlalchemy import Column, Integer, DateTime, Boolean, String
from app.extensions import db


class BaseModel(db.Model):
    """Базовая модель с общими полями"""
    __abstract__ = True
    
    created_date = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_date = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    
    def save(self):
        """Сохранение объекта в базе данных"""
        db.session.add(self)
        db.session.commit()
        return self
    
    def delete(self):
        """Мягкое удаление объекта (установка is_active = False)"""
        self.is_active = False
        self.updated_date = datetime.utcnow()
        db.session.commit()
        return self
    
    def hard_delete(self):
        """Жесткое удаление объекта из базы данных"""
        db.session.delete(self)
        db.session.commit()
    
    def update(self, **kwargs):
        """Обновление полей объекта"""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
        self.updated_date = datetime.utcnow()
        db.session.commit()
        return self
    
    def to_dict(self):
        """Преобразование объекта в словарь"""
        result = {}
        for column in self.__table__.columns:
            value = getattr(self, column.name)
            if isinstance(value, datetime):
                value = value.isoformat()
            result[column.name] = value
        return result
    
    @classmethod
    def get_by_id(cls, id_value):
        """Получение объекта по ID"""
        return cls.query.filter_by(id=id_value, is_active=True).first()
    
    @classmethod
    def get_all_active(cls):
        """Получение всех активных объектов"""
        return cls.query.filter_by(is_active=True).all()
    
    def __repr__(self):
        return f'<{self.__class__.__name__} {getattr(self, "id", "unknown")}>'


class EntityBasedModel(BaseModel):
    """Модель с поддержкой мультитенантности через entity_id"""
    __abstract__ = True
    
    entity_id = Column(Integer, nullable=True, index=True)  # ID сущности (для мультитенантности)
    
    @classmethod
    def get_by_entity(cls, entity_id):
        """Получение объектов по entity_id"""
        return cls.query.filter_by(entity_id=entity_id, is_active=True).all()
    
    @classmethod
    def get_by_id_and_entity(cls, id_value, entity_id):
        """Получение объекта по ID и entity_id"""
        return cls.query.filter_by(
            id=id_value,
            entity_id=entity_id,
            is_active=True
        ).first()


class TimestampMixin:
    """Миксин для добавления временных меток"""
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class SoftDeleteMixin:
    """Миксин для мягкого удаления"""
    deleted_at = Column(DateTime, nullable=True)
    is_deleted = Column(Boolean, default=False, nullable=False)
    
    def soft_delete(self):
        """Мягкое удаление объекта"""
        self.is_deleted = True
        self.deleted_at = datetime.utcnow()
        db.session.commit()
    
    def restore(self):
        """Восстановление удаленного объекта"""
        self.is_deleted = False
        self.deleted_at = None
        db.session.commit()
    
    @classmethod
    def get_active(cls):
        """Получение только не удаленных объектов"""
        return cls.query.filter_by(is_deleted=False)


class AuditMixin:
    """Миксин для аудита изменений"""
    created_by = Column(Integer, nullable=True)  # ID пользователя, создавшего запись
    updated_by = Column(Integer, nullable=True)  # ID пользователя, обновившего запись
    
    def set_created_by(self, user_id):
        """Установка создателя записи"""
        self.created_by = user_id
    
    def set_updated_by(self, user_id):
        """Установка пользователя, обновившего запись"""
        self.updated_by = user_id
        self.updated_date = datetime.utcnow()