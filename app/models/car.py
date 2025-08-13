# app/models/car.py
from sqlalchemy import Column, Integer, String, Text, Boolean, ForeignKey, DECIMAL, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from app.models.base import BaseModel
from app.extensions import db


class CarBrand(BaseModel):
    """Марки автомобилей"""
    __tablename__ = 'car_brands'
    
    brand_id = Column(Integer, primary_key=True)
    brand_name = Column(String(100), unique=True, nullable=False)
    brand_slug = Column(String(100), unique=True, nullable=False)
    logo_url = Column(String(500))
    country_origin = Column(String(100))
    sort_order = Column(Integer, default=0)
    
    @classmethod
    def get_popular_brands(cls, limit=20):
        """Получение популярных марок"""
        return cls.query.filter(cls.is_active == True).order_by(
            cls.sort_order, cls.brand_name
        ).limit(limit).all()
    
    @classmethod
    def search_brands(cls, query):
        """Поиск марок по названию"""
        return cls.query.filter(
            cls.brand_name.ilike(f'%{query}%'),
            cls.is_active == True
        ).order_by(cls.brand_name).all()
    
    def to_dict(self):
        return {
            'brand_id': self.brand_id,
            'brand_name': self.brand_name,
            'brand_slug': self.brand_slug,
            'logo_url': self.logo_url,
            'country_origin': self.country_origin,
            'models_count': len(self.models) if hasattr(self, 'models') else 0
        }
    
    def __repr__(self):
        return f'<CarBrand {self.brand_name}>'


class CarModel(BaseModel):
    """Модели автомобилей"""
    __tablename__ = 'car_models'
    
    model_id = Column(Integer, primary_key=True)
    brand_id = Column(Integer, ForeignKey('car_brands.brand_id'), nullable=False)
    model_name = Column(String(100), nullable=False)
    model_slug = Column(String(150), unique=True, nullable=False)
    start_year = Column(Integer)
    end_year = Column(Integer)
    body_type_id = Column(Integer, ForeignKey('car_body_types.body_type_id'))
    
    __table_args__ = (
        UniqueConstraint('brand_id', 'model_name', name='unique_brand_model'),
    )
    
    # Отношения
    brand = db.relationship('CarBrand', backref='models')
    body_type = db.relationship('CarBodyType', backref='models')
    
    @classmethod
    def get_by_brand(cls, brand_id):
        """Получение моделей по марке"""
        return cls.query.filter(
            cls.brand_id == brand_id,
            cls.is_active == True
        ).order_by(cls.model_name).all()
    
    @classmethod
    def search_models(cls, brand_id, query):
        """Поиск моделей по названию в рамках марки"""
        return cls.query.filter(
            cls.brand_id == brand_id,
            cls.model_name.ilike(f'%{query}%'),
            cls.is_active == True
        ).order_by(cls.model_name).all()
    
    @property
    def full_name(self):
        """Полное название модели с маркой"""
        return f"{self.brand.brand_name} {self.model_name}" if self.brand else self.model_name
    
    def to_dict(self):
        return {
            'model_id': self.model_id,
            'brand_id': self.brand_id,
            'brand_name': self.brand.brand_name if self.brand else None,
            'model_name': self.model_name,
            'model_slug': self.model_slug,
            'full_name': self.full_name,
            'start_year': self.start_year,
            'end_year': self.end_year,
            'body_type_id': self.body_type_id,
            'body_type_name': self.body_type.body_type_name if self.body_type else None,
            'generations_count': len(self.generations) if hasattr(self, 'generations') else 0
        }
    
    def __repr__(self):
        return f'<CarModel {self.full_name}>'


class CarGeneration(BaseModel):
    """Поколения автомобилей"""
    __tablename__ = 'car_generations'
    
    generation_id = Column(Integer, primary_key=True)
    model_id = Column(Integer, ForeignKey('car_models.model_id'), nullable=False)
    generation_name = Column(String(100), nullable=False)
    start_year = Column(Integer)
    end_year = Column(Integer)
    description = Column(Text)
    
    # Отношения
    model = db.relationship('CarModel', backref='generations')
    
    @classmethod
    def get_by_model(cls, model_id):
        """Получение поколений по модели"""
        return cls.query.filter(
            cls.model_id == model_id,
            cls.is_active == True
        ).order_by(cls.start_year.desc()).all()
    
    @property
    def years_range(self):
        """Диапазон годов поколения"""
        if self.start_year and self.end_year:
            return f"{self.start_year}-{self.end_year}"
        elif self.start_year:
            return f"{self.start_year}-..."
        return ""
    
    def to_dict(self):
        return {
            'generation_id': self.generation_id,
            'model_id': self.model_id,
            'generation_name': self.generation_name,
            'start_year': self.start_year,
            'end_year': self.end_year,
            'years_range': self.years_range,
            'description': self.description
        }
    
    def __repr__(self):
        return f'<CarGeneration {self.generation_name}>'


class CarAttributeGroup(BaseModel):
    """Группы атрибутов автомобилей"""
    __tablename__ = 'car_attribute_groups'
    
    group_id = Column(Integer, primary_key=True)
    group_name = Column(String(100), nullable=False)
    group_code = Column(String(50), unique=True, nullable=False)
    sort_order = Column(Integer, default=0)
    
    def to_dict(self):
        return {
            'group_id': self.group_id,
            'group_name': self.group_name,
            'group_code': self.group_code,
            'sort_order': self.sort_order,
            'attributes': [attr.to_dict() for attr in self.attributes] if hasattr(self, 'attributes') else []
        }


class CarAttribute(BaseModel):
    """Атрибуты автомобилей"""
    __tablename__ = 'car_attributes'
    
    attribute_id = Column(Integer, primary_key=True)
    group_id = Column(Integer, ForeignKey('car_attribute_groups.group_id'), nullable=False)
    attribute_code = Column(String(100), unique=True, nullable=False)
    attribute_name = Column(String(100), nullable=False)
    attribute_type = Column(String(20), nullable=False)
    reference_table = Column(String(100))
    is_required = Column(Boolean, default=False)
    is_searchable = Column(Boolean, default=False)
    is_filterable = Column(Boolean, default=False)
    sort_order = Column(Integer, default=0)
    validation_rules = Column(JSONB)
    default_value = Column(Text)
    
    __table_args__ = (
        db.CheckConstraint(
            "attribute_type IN ('string', 'number', 'boolean', 'reference', 'multi_select')",
            name='check_attribute_type'
        ),
    )
    
    # Отношения
    group = db.relationship('CarAttributeGroup', backref='attributes')
    
    @classmethod
    def get_searchable_attributes(cls):
        """Получение атрибутов для поиска"""
        return cls.query.filter(
            cls.is_searchable == True,
            cls.is_active == True
        ).order_by(cls.sort_order).all()
    
    @classmethod
    def get_filterable_attributes(cls):
        """Получение атрибутов для фильтрации"""
        return cls.query.filter(
            cls.is_filterable == True,
            cls.is_active == True
        ).order_by(cls.sort_order).all()
    
    def to_dict(self):
        return {
            'attribute_id': self.attribute_id,
            'group_id': self.group_id,
            'attribute_code': self.attribute_code,
            'attribute_name': self.attribute_name,
            'attribute_type': self.attribute_type,
            'reference_table': self.reference_table,
            'is_required': self.is_required,
            'is_searchable': self.is_searchable,
            'is_filterable': self.is_filterable,
            'validation_rules': self.validation_rules,
            'default_value': self.default_value
        }


class CarBodyType(BaseModel):
    """Типы кузова автомобилей"""
    __tablename__ = 'car_body_types'
    
    body_type_id = Column(Integer, primary_key=True)
    body_type_name = Column(String(50), unique=True, nullable=False)
    icon_url = Column(String(500))
    sort_order = Column(Integer, default=0)
    
    @classmethod
    def get_all_active(cls):
        """Получение всех активных типов кузова"""
        return cls.query.filter(cls.is_active == True).order_by(cls.sort_order).all()
    
    def to_dict(self):
        return {
            'body_type_id': self.body_type_id,
            'body_type_name': self.body_type_name,
            'icon_url': self.icon_url,
            'sort_order': self.sort_order
        }
    
    def __repr__(self):
        return f'<CarBodyType {self.body_type_name}>'


class CarEngineType(BaseModel):
    """Типы двигателей"""
    __tablename__ = 'car_engine_types'
    
    engine_type_id = Column(Integer, primary_key=True)
    engine_type_name = Column(String(50), unique=True, nullable=False)
    sort_order = Column(Integer, default=0)
    
    @classmethod
    def get_all_active(cls):
        """Получение всех активных типов двигателей"""
        return cls.query.filter(cls.is_active == True).order_by(cls.sort_order).all()
    
    def to_dict(self):
        return {
            'engine_type_id': self.engine_type_id,
            'engine_type_name': self.engine_type_name,
            'sort_order': self.sort_order
        }
    
    def __repr__(self):
        return f'<CarEngineType {self.engine_type_name}>'


class CarTransmissionType(BaseModel):
    """Типы трансмиссий"""
    __tablename__ = 'car_transmission_types'
    
    transmission_id = Column(Integer, primary_key=True)
    transmission_name = Column(String(50), unique=True, nullable=False)
    sort_order = Column(Integer, default=0)
    
    @classmethod
    def get_all_active(cls):
        """Получение всех активных типов трансмиссий"""
        return cls.query.filter(cls.is_active == True).order_by(cls.sort_order).all()
    
    def to_dict(self):
        return {
            'transmission_id': self.transmission_id,
            'transmission_name': self.transmission_name,
            'sort_order': self.sort_order
        }
    
    def __repr__(self):
        return f'<CarTransmissionType {self.transmission_name}>'


class CarDriveType(BaseModel):
    """Типы приводов"""
    __tablename__ = 'car_drive_types'
    
    drive_type_id = Column(Integer, primary_key=True)
    drive_type_name = Column(String(50), unique=True, nullable=False)
    sort_order = Column(Integer, default=0)
    
    @classmethod
    def get_all_active(cls):
        """Получение всех активных типов приводов"""
        return cls.query.filter(cls.is_active == True).order_by(cls.sort_order).all()
    
    def to_dict(self):
        return {
            'drive_type_id': self.drive_type_id,
            'drive_type_name': self.drive_type_name,
            'sort_order': self.sort_order
        }
    
    def __repr__(self):
        return f'<CarDriveType {self.drive_type_name}>'


class CarColor(BaseModel):
    """Цвета автомобилей"""
    __tablename__ = 'car_colors'
    
    color_id = Column(Integer, primary_key=True)
    color_name = Column(String(50), unique=True, nullable=False)
    color_hex = Column(String(7))  # HEX код цвета
    sort_order = Column(Integer, default=0)
    
    @classmethod
    def get_all_active(cls):
        """Получение всех активных цветов"""
        return cls.query.filter(cls.is_active == True).order_by(cls.sort_order).all()
    
    @classmethod
    def get_popular_colors(cls, limit=10):
        """Получение популярных цветов"""
        return cls.query.filter(cls.is_active == True).order_by(cls.sort_order).limit(limit).all()
    
    def to_dict(self):
        return {
            'color_id': self.color_id,
            'color_name': self.color_name,
            'color_hex': self.color_hex,
            'sort_order': self.sort_order
        }
    
    def __repr__(self):
        return f'<CarColor {self.color_name}>'


class CarFeature(BaseModel):
    """Особенности и опции автомобилей"""
    __tablename__ = 'car_features'
    
    feature_id = Column(Integer, primary_key=True)
    feature_name = Column(String(100), unique=True, nullable=False)
    category_id = Column(Integer, ForeignKey('categories.category_id'))
    icon_url = Column(String(500))
    sort_order = Column(Integer, default=0)
    
    # Отношения
    category = db.relationship('Category', backref='car_features')
    
    @classmethod
    def get_by_category(cls, category_id):
        """Получение опций по категории"""
        return cls.query.filter(
            cls.category_id == category_id,
            cls.is_active == True
        ).order_by(cls.sort_order).all()
    
    @classmethod
    def get_popular_features(cls, limit=20):
        """Получение популярных опций"""
        return cls.query.filter(cls.is_active == True).order_by(
            cls.sort_order, cls.feature_name
        ).limit(limit).all()
    
    @classmethod
    def search_features(cls, query):
        """Поиск опций по названию"""
        return cls.query.filter(
            cls.feature_name.ilike(f'%{query}%'),
            cls.is_active == True
        ).order_by(cls.feature_name).all()
    
    def to_dict(self):
        return {
            'feature_id': self.feature_id,
            'feature_name': self.feature_name,
            'category_id': self.category_id,
            'category_name': self.category.category_name if self.category else None,
            'icon_url': self.icon_url,
            'sort_order': self.sort_order
        }
    
    def __repr__(self):
        return f'<CarFeature {self.feature_name}>'


# Вспомогательные функции для работы с автомобильными справочниками
def get_car_brands_with_models():
    """Получение марок с моделями"""
    brands = CarBrand.query.filter(CarBrand.is_active == True).order_by(CarBrand.sort_order).all()
    result = []
    
    for brand in brands:
        brand_dict = brand.to_dict()
        brand_dict['models'] = [model.to_dict() for model in brand.models if model.is_active]
        result.append(brand_dict)
    
    return result


def get_car_hierarchy(brand_id=None, model_id=None):
    """Получение иерархии марка -> модель -> поколение"""
    result = {}
    
    if brand_id:
        brand = CarBrand.query.filter(
            CarBrand.brand_id == brand_id,
            CarBrand.is_active == True
        ).first()
        
        if not brand:
            return None
        
        result['brand'] = brand.to_dict()
        
        if model_id:
            model = CarModel.query.filter(
                CarModel.model_id == model_id,
                CarModel.brand_id == brand_id,
                CarModel.is_active == True
            ).first()
            
            if not model:
                return None
            
            result['model'] = model.to_dict()
            result['generations'] = [gen.to_dict() for gen in model.generations if gen.is_active]
        else:
            result['models'] = [model.to_dict() for model in brand.models if model.is_active]
    else:
        brands = CarBrand.get_popular_brands()
        result['brands'] = [brand.to_dict() for brand in brands]
    
    return result


def get_car_attributes_grouped():
    """Получение атрибутов автомобилей, сгруппированных по группам"""
    groups = CarAttributeGroup.query.filter(
        CarAttributeGroup.is_active == True
    ).order_by(CarAttributeGroup.sort_order).all()
    
    result = []
    for group in groups:
        group_dict = group.to_dict()
        group_dict['attributes'] = [
            attr.to_dict() for attr in group.attributes 
            if attr.is_active
        ]
        result.append(group_dict)
    
    return result


def get_car_reference_data():
    """Получение всех справочных данных для автомобилей"""
    return {
        'body_types': [bt.to_dict() for bt in CarBodyType.get_all_active()],
        'engine_types': [et.to_dict() for et in CarEngineType.get_all_active()],
        'transmission_types': [tt.to_dict() for tt in CarTransmissionType.get_all_active()],
        'drive_types': [dt.to_dict() for dt in CarDriveType.get_all_active()],
        'colors': [c.to_dict() for c in CarColor.get_popular_colors()],
        'features': [f.to_dict() for f in CarFeature.get_popular_features()]
    }


def validate_car_year(year):
    """Валидация года автомобиля"""
    from datetime import datetime
    current_year = datetime.now().year
    
    if not isinstance(year, int):
        return False
    
    # Проверяем разумные границы
    return 1950 <= year <= current_year + 1


def get_years_range():
    """Получение диапазона доступных годов"""
    from datetime import datetime
    current_year = datetime.now().year
    
    return {
        'min_year': 1950,
        'max_year': current_year + 1,
        'years': list(range(current_year + 1, 1949, -1))  # От текущего года до 1950
    }