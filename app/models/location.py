# app/models/location.py
from sqlalchemy import Column, Integer, String, DECIMAL, ForeignKey
from app.models.base import BaseModel
from app.extensions import db


class Country(BaseModel):
    """Модель стран"""
    __tablename__ = 'countries'
    
    country_id = Column(Integer, primary_key=True)
    country_code = Column(String(3), unique=True, nullable=False)
    country_name = Column(String(100), nullable=False)
    phone_code = Column(String(10))
    
    def __repr__(self):
        return f'<Country {self.country_name}>'


class Region(BaseModel):
    """Модель регионов"""
    __tablename__ = 'regions'
    
    region_id = Column(Integer, primary_key=True)
    region_name = Column(String(100), nullable=False)
    country_id = Column(Integer, ForeignKey('countries.country_id'), nullable=False)
    region_code = Column(String(10))
    sort_order = Column(Integer, default=0)
    
    # Отношения
    country = db.relationship('Country', backref='regions')
    
    def __repr__(self):
        return f'<Region {self.region_name}>'


class City(BaseModel):
    """Модель городов"""
    __tablename__ = 'cities'
    
    city_id = Column(Integer, primary_key=True)
    city_name = Column(String(100), nullable=False)
    region_id = Column(Integer, ForeignKey('regions.region_id'), nullable=False)
    latitude = Column(DECIMAL(10, 8))
    longitude = Column(DECIMAL(11, 8))
    population = Column(Integer)
    sort_order = Column(Integer, default=0)
    
    # Отношения
    region = db.relationship('Region', backref='cities')
    
    @property
    def country(self):
        """Получение страны через регион"""
        return self.region.country if self.region else None
    
    @property
    def full_name(self):
        """Полное название с регионом"""
        return f"{self.city_name}, {self.region.region_name}" if self.region else self.city_name
    
    def get_distance_to(self, lat, lng):
        """Вычисление расстояния до точки в км (приблизительно)"""
        if not self.latitude or not self.longitude:
            return None
        
        from math import radians, cos, sin, asin, sqrt
        
        # Радиус Земли в километрах
        R = 6371
        
        # Преобразование в радианы
        lat1, lng1, lat2, lng2 = map(radians, [float(self.latitude), float(self.longitude), lat, lng])
        
        # Формула гаверсинуса
        dlat = lat2 - lat1
        dlng = lng2 - lng1
        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlng/2)**2
        c = 2 * asin(sqrt(a))
        
        return R * c
    
    @classmethod
    def search_by_name(cls, query, limit=10):
        """Поиск городов по названию"""
        return cls.query.filter(
            cls.city_name.ilike(f'%{query}%'),
            cls.is_active == True
        ).order_by(cls.sort_order, cls.city_name).limit(limit).all()
    
    @classmethod
    def get_by_region(cls, region_id):
        """Получение городов региона"""
        return cls.query.filter(
            cls.region_id == region_id,
            cls.is_active == True
        ).order_by(cls.sort_order, cls.city_name).all()
    
    @classmethod
    def get_popular_cities(cls, limit=20):
        """Получение популярных городов (по населению)"""
        return cls.query.filter(
            cls.is_active == True,
            cls.population.isnot(None)
        ).order_by(cls.population.desc()).limit(limit).all()
    
    def __repr__(self):
        return f'<City {self.city_name}>'