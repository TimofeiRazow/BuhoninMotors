# app/models/listing.py
from datetime import datetime, timedelta
from sqlalchemy import Column, Integer, String, Text, DECIMAL, Boolean, DateTime, ForeignKey, Index
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR
from sqlalchemy.sql import func
from app.models.base import BaseModel, EntityBasedModel
from app.extensions import db


class Listing(EntityBasedModel):
    """Модель объявления"""
    __tablename__ = 'listings'
    
    listing_id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.user_id'), nullable=False)
    listing_type_id = Column(Integer, ForeignKey('entity_types.type_id'), nullable=False)
    category_id = Column(Integer, ForeignKey('categories.category_id'))
    title = Column(String(255), nullable=False)
    description = Column(Text)
    price = Column(DECIMAL(15, 2))
    currency_id = Column(Integer, ForeignKey('currencies.currency_id'))
    city_id = Column(Integer, ForeignKey('cities.city_id'))
    address = Column(Text)
    latitude = Column(DECIMAL(10, 8))
    longitude = Column(DECIMAL(11, 8))
    contact_phone = Column(String(20))
    contact_name = Column(String(100))
    status_id = Column(Integer, ForeignKey('statuses.status_id'), nullable=False)
    published_date = Column(DateTime)
    expires_date = Column(DateTime)
    view_count = Column(Integer, default=0)
    favorite_count = Column(Integer, default=0)
    is_featured = Column(Boolean, default=False)
    is_urgent = Column(Boolean, default=False)
    is_negotiable = Column(Boolean, default=True)
    search_vector = Column(TSVECTOR)
    
    # Ограничения
    __table_args__ = (
        db.CheckConstraint('price IS NULL OR price >= 0', name='check_positive_price'),
        db.CheckConstraint(
            '(latitude IS NULL AND longitude IS NULL) OR (latitude IS NOT NULL AND longitude IS NOT NULL)',
            name='check_coordinates_pair'
        ),
        # Индексы для оптимизации поиска
        Index('idx_listings_search_main', 'listing_type_id', 'city_id', 'status_id', 'price', 'published_date'),
        Index('idx_listings_user_status', 'user_id', 'status_id', 'updated_date'),
        Index('idx_listings_featured', 'is_featured', 'published_date', postgresql_where=db.text('is_featured = true')),
        Index('idx_listings_expires', 'expires_date', postgresql_where=db.text('expires_date IS NOT NULL')),
        Index('idx_listings_search_vector', 'search_vector', postgresql_using='gin'),
    )
    
    # Отношения
    user = db.relationship('User', backref='listings')
    listing_type = db.relationship('EntityType', backref='listings')
    category = db.relationship('Category', backref='listings')
    currency = db.relationship('Currency', backref='listings')
    city = db.relationship('City', backref='listings')
    status = db.relationship('Status', backref='listings')
    
    def publish(self, duration_days=30):
        """Публикация объявления"""
        from app.models.base import get_status_by_code
        
        self.published_date = datetime.utcnow()
        self.expires_date = datetime.utcnow() + timedelta(days=duration_days)
        
        # Устанавливаем статус "активно"
        active_status = get_status_by_code('listing_status', 'active')
        if active_status:
            self.status_id = active_status.status_id
        
        self.save()
    
    def archive(self):
        """Архивирование объявления"""
        from app.models.base import get_status_by_code
        
        archived_status = get_status_by_code('listing_status', 'archived')
        if archived_status:
            self.status_id = archived_status.status_id
        
        self.save()
    
    def mark_as_sold(self):
        """Отметка как проданное"""
        from app.models.base import get_status_by_code
        
        sold_status = get_status_by_code('listing_status', 'sold')
        if sold_status:
            self.status_id = sold_status.status_id
        
        self.save()
    
    def increment_view_count(self):
        """Увеличение счетчика просмотров"""
        self.view_count = Listing.view_count + 1
        db.session.commit()
    
    def add_to_favorites(self, user_id):
        """Добавление в избранное"""
        from app.models.favorite import Favorite
        
        existing = Favorite.query.filter(
            Favorite.user_id == user_id,
            Favorite.entity_id == self.entity_id
        ).first()
        
        if not existing:
            favorite = Favorite(user_id=user_id, entity_id=self.entity_id)
            favorite.save()
            
            # Обновляем счетчик
            self.favorite_count = Listing.favorite_count + 1
            db.session.commit()
            
            return True
        
        return False
    
    def remove_from_favorites(self, user_id):
        """Удаление из избранного"""
        from app.models.favorite import Favorite
        
        favorite = Favorite.query.filter(
            Favorite.user_id == user_id,
            Favorite.entity_id == self.entity_id
        ).first()
        
        if favorite:
            favorite.delete()
            
            # Обновляем счетчик
            self.favorite_count = max(0, Listing.favorite_count - 1)
            db.session.commit()
            
            return True
        
        return False
    
    def is_favorited_by(self, user_id):
        """Проверка нахождения в избранном у пользователя"""
        from app.models.favorite import Favorite
        
        return Favorite.query.filter(
            Favorite.user_id == user_id,
            Favorite.entity_id == self.entity_id
        ).first() is not None
    
    def is_expired(self):
        """Проверка истечения срока объявления"""
        return (
            self.expires_date and 
            datetime.utcnow() > self.expires_date
        )
    
    def is_active(self):
        """Проверка активности объявления"""
        return (
            self.status and 
            self.status.status_code == 'active' and 
            not self.is_expired()
        )
    
    def get_main_image(self):
        """Получение главного изображения"""
        from app.models.media import MediaStorage
        
        return MediaStorage.query.filter(
            MediaStorage.entity_id == self.entity_id,
            MediaStorage.media_type == 'image',
            MediaStorage.is_primary == True
        ).first()
    
    def get_images(self):
        """Получение всех изображений"""
        from app.models.media import MediaStorage
        
        return MediaStorage.query.filter(
            MediaStorage.entity_id == self.entity_id,
            MediaStorage.media_type == 'image'
        ).order_by(MediaStorage.file_order).all()
    
    @property
    def price_kzt(self):
        """Цена в тенге"""
        if not self.price or not self.currency:
            return None
        
        return float(self.price * self.currency.exchange_rate_to_kzt)
    
    @property
    def days_since_published(self):
        """Количество дней с момента публикации"""
        if not self.published_date:
            return None
        
        return (datetime.utcnow() - self.published_date).days
    
    @property
    def days_until_expires(self):
        """Количество дней до истечения"""
        if not self.expires_date:
            return None
        
        delta = self.expires_date - datetime.utcnow()
        return max(0, delta.days)
    
    @classmethod
    def get_active_listings(cls):
        """Получение активных объявлений"""
        from app.models.base import get_status_by_code
        
        active_status = get_status_by_code('listing_status', 'active')
        
        return cls.query.filter(
            cls.status_id == active_status.status_id if active_status else None,
            cls.published_date.isnot(None),
            cls.expires_date > datetime.utcnow()
        )
    
    @classmethod
    def search_by_text(cls, query, listing_type=None):
        """Полнотекстовый поиск"""
        base_query = cls.get_active_listings()
        
        if listing_type:
            base_query = base_query.join(EntityType).filter(
                EntityType.type_code == listing_type
            )
        
        # PostgreSQL полнотекстовый поиск
        search_query = func.plainto_tsquery('russian', query)
        
        return base_query.filter(
            cls.search_vector.op('@@')(search_query)
        ).order_by(
            func.ts_rank(cls.search_vector, search_query).desc(),
            cls.published_date.desc()
        )
    
    @classmethod
    def search_by_location(cls, lat, lng, radius_km=50):
        """Поиск по геолокации"""
        from sqlalchemy import text
        
        # Используем PostgreSQL функции для работы с геолокацией
        distance_query = text("""
            earth_distance(
                ll_to_earth(:search_lat, :search_lng),
                ll_to_earth(latitude, longitude)
            ) / 1000
        """)
        
        return cls.get_active_listings().filter(
            cls.latitude.isnot(None),
            cls.longitude.isnot(None),
            text("""
                earth_box(ll_to_earth(:search_lat, :search_lng), :radius_m) @>
                ll_to_earth(latitude, longitude)
            """)
        ).params(
            search_lat=lat,
            search_lng=lng,
            radius_m=radius_km * 1000
        ).order_by(distance_query)
    
    def to_dict(self, include_details=False, user_id=None):
        """Преобразование в словарь"""
        main_image = self.get_main_image()
        
        data = {
            'listing_id': self.listing_id,
            'entity_id': self.entity_id,
            'title': self.title,
            'price': float(self.price) if self.price else None,
            'price_kzt': self.price_kzt,
            'currency_code': self.currency.currency_code if self.currency else None,
            'city_name': self.city.city_name if self.city else None,
            'region_name': self.city.region.region_name if self.city and self.city.region else None,
            'main_image_url': main_image.file_url if main_image else None,
            'images_count': len(self.get_images()),
            'view_count': self.view_count,
            'favorite_count': self.favorite_count,
            'is_featured': self.is_featured,
            'is_urgent': self.is_urgent,
            'is_negotiable': self.is_negotiable,
            'published_date': self.published_date.isoformat() if self.published_date else None,
            'days_since_published': self.days_since_published,
            'days_until_expires': self.days_until_expires,
            'status': self.status.status_name if self.status else None,
            'is_active': self.is_active()
        }
        
        if user_id:
            data['is_favorited'] = self.is_favorited_by(user_id)
        
        if include_details:
            data.update({
                'description': self.description,
                'address': self.address,
                'latitude': float(self.latitude) if self.latitude else None,
                'longitude': float(self.longitude) if self.longitude else None,
                'contact_phone': self.contact_phone,
                'contact_name': self.contact_name,
                'images': [img.to_dict() for img in self.get_images()],
                'user': self.user.to_dict() if self.user else None,
                'category': self.category.to_dict() if self.category else None
            })
        
        return data
    
    def __repr__(self):
        return f'<Listing {self.title[:50]}>'


class ListingDetails(BaseModel):
    """Детали объявления в JSONB формате для гибкости"""
    __tablename__ = 'listing_details'
    
    listing_id = Column(Integer, ForeignKey('listings.listing_id'), primary_key=True)
    listing_type_id = Column(Integer, ForeignKey('entity_types.type_id'), nullable=False)
    details = Column(JSONB, default={})
    searchable_fields = Column(JSONB, default={})
    
    # Индексы для быстрого поиска по JSONB
    __table_args__ = (
        Index('idx_listing_details_jsonb', 'searchable_fields', postgresql_using='gin'),
        Index('idx_listing_details_brand', 
              func.cast(searchable_fields['brand_id'], Integer),
              postgresql_where=db.text('listing_type_id = 1')),
        Index('idx_listing_details_model',
              func.cast(searchable_fields['model_id'], Integer),
              postgresql_where=db.text('listing_type_id = 1')),
    )
    
    # Отношения
    listing = db.relationship('Listing', backref=db.backref('details', uselist=False))
    listing_type = db.relationship('EntityType')
    
    def set_car_details(self, **kwargs):
        """Установка деталей для автомобильного объявления"""
        car_details = {
            'brand_id': kwargs.get('brand_id'),
            'model_id': kwargs.get('model_id'),
            'generation_id': kwargs.get('generation_id'),
            'year': kwargs.get('year'),
            'mileage': kwargs.get('mileage'),
            'condition': kwargs.get('condition'),
            'body_type_id': kwargs.get('body_type_id'),
            'color_id': kwargs.get('color_id'),
            'engine_volume': kwargs.get('engine_volume'),
            'engine_type_id': kwargs.get('engine_type_id'),
            'transmission_id': kwargs.get('transmission_id'),
            'drive_type_id': kwargs.get('drive_type_id'),
            'vin_number': kwargs.get('vin_number'),
            'customs_cleared': kwargs.get('customs_cleared'),
            'exchange_possible': kwargs.get('exchange_possible'),
            'credit_available': kwargs.get('credit_available')
        }
        
        # Убираем None значения
        car_details = {k: v for k, v in car_details.items() if v is not None}
        
        self.details = car_details
        self.searchable_fields = {
            k: v for k, v in car_details.items() 
            if k in ['brand_id', 'model_id', 'year', 'body_type_id', 'engine_type_id', 'transmission_id']
        }
        
        self.save()
    
    def get_car_info(self):
        """Получение информации об автомобиле с названиями"""
        if not self.details:
            return {}
        
        from app.models.car import CarBrand, CarModel, CarGeneration, CarBodyType, CarEngineType, CarTransmissionType, CarDriveType, CarColor
        
        info = dict(self.details)
        
        # Получаем названия для ID
        if info.get('brand_id'):
            brand = CarBrand.query.get(info['brand_id'])
            info['brand_name'] = brand.brand_name if brand else None
        
        if info.get('model_id'):
            model = CarModel.query.get(info['model_id'])
            info['model_name'] = model.model_name if model else None
        
        if info.get('generation_id'):
            generation = CarGeneration.query.get(info['generation_id'])
            info['generation_name'] = generation.generation_name if generation else None
        
        if info.get('body_type_id'):
            body_type = CarBodyType.query.get(info['body_type_id'])
            info['body_type_name'] = body_type.body_type_name if body_type else None
        
        if info.get('color_id'):
            color = CarColor.query.get(info['color_id'])
            info['color_name'] = color.color_name if color else None
        
        if info.get('engine_type_id'):
            engine_type = CarEngineType.query.get(info['engine_type_id'])
            info['engine_type_name'] = engine_type.engine_type_name if engine_type else None
        
        if info.get('transmission_id'):
            transmission = CarTransmissionType.query.get(info['transmission_id'])
            info['transmission_name'] = transmission.transmission_name if transmission else None
        
        if info.get('drive_type_id'):
            drive_type = CarDriveType.query.get(info['drive_type_id'])
            info['drive_type_name'] = drive_type.drive_type_name if drive_type else None
        
        return info
    
    def to_dict(self):
        """Преобразование в словарь"""
        return {
            'listing_id': self.listing_id,
            'listing_type_id': self.listing_type_id,
            'details': self.details,
            'searchable_fields': self.searchable_fields
        }


class ListingAttribute(BaseModel):
    """Атрибуты объявлений (альтернативный подход к JSONB)"""
    __tablename__ = 'listing_attributes'
    
    listing_id = Column(Integer, ForeignKey('listings.listing_id'), nullable=False)
    attribute_id = Column(Integer, ForeignKey('car_attributes.attribute_id'), nullable=False)
    string_value = Column(Text)
    numeric_value = Column(DECIMAL(15, 6))
    boolean_value = Column(Boolean)
    reference_id = Column(Integer)
    date_value = Column(DateTime)
    
    __table_args__ = (
        db.PrimaryKeyConstraint('listing_id', 'attribute_id'),
    )
    
    # Отношения
    listing = db.relationship('Listing', backref='attributes')
    attribute = db.relationship('CarAttribute', backref='listing_attributes')
    
    @property
    def value(self):
        """Получение значения в зависимости от типа атрибута"""
        if self.attribute.attribute_type == 'string':
            return self.string_value
        elif self.attribute.attribute_type == 'number':
            return float(self.numeric_value) if self.numeric_value else None
        elif self.attribute.attribute_type == 'boolean':
            return self.boolean_value
        elif self.attribute.attribute_type == 'reference':
            return self.reference_id
        elif self.attribute.attribute_type == 'date':
            return self.date_value
        
        return None
    
    def set_value(self, value):
        """Установка значения в зависимости от типа атрибута"""
        # Сброс всех значений
        self.string_value = None
        self.numeric_value = None
        self.boolean_value = None
        self.reference_id = None
        self.date_value = None
        
        if self.attribute.attribute_type == 'string':
            self.string_value = str(value) if value is not None else None
        elif self.attribute.attribute_type == 'number':
            self.numeric_value = float(value) if value is not None else None
        elif self.attribute.attribute_type == 'boolean':
            self.boolean_value = bool(value) if value is not None else None
        elif self.attribute.attribute_type == 'reference':
            self.reference_id = int(value) if value is not None else None
        elif self.attribute.attribute_type == 'date':
            self.date_value = value if isinstance(value, datetime) else None
    
    def to_dict(self):
        """Преобразование в словарь"""
        return {
            'listing_id': self.listing_id,
            'attribute_id': self.attribute_id,
            'attribute_code': self.attribute.attribute_code if self.attribute else None,
            'attribute_name': self.attribute.attribute_name if self.attribute else None,
            'attribute_type': self.attribute.attribute_type if self.attribute else None,
            'value': self.value
        }


class ListingFeature(BaseModel):
    """Связь объявлений с опциями/особенностями"""
    __tablename__ = 'listing_features'
    
    listing_id = Column(Integer, ForeignKey('listings.listing_id'), nullable=False)
    feature_id = Column(Integer, ForeignKey('car_features.feature_id'), nullable=False)
    
    __table_args__ = (
        db.PrimaryKeyConstraint('listing_id', 'feature_id'),
    )
    
    # Отношения
    listing = db.relationship('Listing', backref='features')
    feature = db.relationship('CarFeature', backref='listing_features')
    
    def to_dict(self):
        """Преобразование в словарь"""
        return {
            'listing_id': self.listing_id,
            'feature_id': self.feature_id,
            'feature_name': self.feature.feature_name if self.feature else None
        }