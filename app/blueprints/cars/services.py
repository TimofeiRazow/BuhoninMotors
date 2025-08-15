# app/blueprints/cars/services.py
from sqlalchemy import func
from app.models.car import (
    CarBrand, CarModel, CarGeneration, CarBodyType, CarEngineType,
    CarTransmissionType, CarDriveType, CarColor, CarFeature, CarAttributeGroup, CarAttribute,
    get_car_brands_with_models, get_car_hierarchy, get_car_attributes_grouped,
    get_car_reference_data, get_years_range
)
from app.utils.exceptions import NotFoundError
from app.utils.pagination import paginate_query
from app.extensions import cache
from app.database import db


class CarService:
    """Сервис для работы с автомобильными справочниками"""
    
    @staticmethod
    @cache.memoize(timeout=3600)  # Кэшируем на час
    def get_brands(search=None, limit=None):
        """
        Получение марок автомобилей
        
        Args:
            search: Поисковый запрос
            limit: Лимит результатов
            
        Returns:
            Список марок
        """
        query = CarBrand.query.filter(CarBrand.is_active == True)
        
        if search:
            query = query.filter(
                CarBrand.brand_name.ilike(f'%{search}%')
            )
        
        query = query.order_by(CarBrand.sort_order, CarBrand.brand_name)
        
        if limit:
            query = query.limit(limit)
        
        return query.all()
    
    @staticmethod
    def get_brand(brand_id):
        """
        Получение марки по ID
        
        Args:
            brand_id: ID марки
            
        Returns:
            Марка автомобиля
            
        Raises:
            NotFoundError: Если марка не найдена
        """
        brand = CarBrand.query.filter(
            CarBrand.brand_id == brand_id,
            CarBrand.is_active == True
        ).first()
        
        if not brand:
            raise NotFoundError(f"Brand {brand_id} not found", "brand")
        
        return brand
    
    @staticmethod
    @cache.memoize(timeout=3600)
    def get_models_by_brand(brand_id, search=None):
        """
        Получение моделей по марке
        
        Args:
            brand_id: ID марки
            search: Поисковый запрос
            
        Returns:
            Список моделей
        """
        # Проверяем существование марки
        CarService.get_brand(brand_id)
        
        query = CarModel.query.filter(
            CarModel.brand_id == brand_id,
            CarModel.is_active == True
        )
        
        if search:
            query = query.filter(
                CarModel.model_name.ilike(f'%{search}%')
            )
        
        return query.order_by(CarModel.model_name).all()
    
    @staticmethod
    def get_model(model_id):
        """
        Получение модели по ID
        
        Args:
            model_id: ID модели
            
        Returns:
            Модель автомобиля
            
        Raises:
            NotFoundError: Если модель не найдена
        """
        model = CarModel.query.filter(
            CarModel.model_id == model_id,
            CarModel.is_active == True
        ).first()
        
        if not model:
            raise NotFoundError(f"Model {model_id} not found", "model")
        
        return model
    
    @staticmethod
    @cache.memoize(timeout=3600)
    def get_generations_by_model(model_id):
        """
        Получение поколений по модели
        
        Args:
            model_id: ID модели
            
        Returns:
            Список поколений
        """
        # Проверяем существование модели
        CarService.get_model(model_id)
        
        return CarGeneration.get_by_model(model_id)
    
    @staticmethod
    @cache.memoize(timeout=3600)
    def get_body_types():
        """Получение всех типов кузова"""
        return CarBodyType.get_all_active()
    
    @staticmethod
    @cache.memoize(timeout=3600)
    def get_engine_types():
        """Получение всех типов двигателей"""
        return CarEngineType.get_all_active()
    
    @staticmethod
    @cache.memoize(timeout=3600)
    def get_transmission_types():
        """Получение всех типов трансмиссий"""
        return CarTransmissionType.get_all_active()
    
    @staticmethod
    @cache.memoize(timeout=3600)
    def get_drive_types():
        """Получение всех типов приводов"""
        return CarDriveType.get_all_active()
    
    @staticmethod
    @cache.memoize(timeout=3600)
    def get_colors():
        """Получение всех цветов"""
        return CarColor.get_all_active()
    
    @staticmethod
    @cache.memoize(timeout=3600)
    def get_features(category_id=None, search=None):
        """
        Получение особенностей автомобилей
        
        Args:
            category_id: ID категории
            search: Поисковый запрос
            
        Returns:
            Список особенностей
        """
        if category_id:
            return CarFeature.get_by_category(category_id)
        
        query = CarFeature.query.filter(CarFeature.is_active == True)
        
        if search:
            query = query.filter(
                CarFeature.feature_name.ilike(f'%{search}%')
            )
        
        return query.order_by(CarFeature.sort_order, CarFeature.feature_name).all()
    
    @staticmethod
    @cache.memoize(timeout=3600)
    def get_attributes_grouped():
        """Получение атрибутов автомобилей, сгруппированных по группам"""
        return get_car_attributes_grouped()
    
    @staticmethod
    @cache.memoize(timeout=3600)
    def get_searchable_attributes():
        """Получение атрибутов для поиска"""
        return CarAttribute.get_searchable_attributes()
    
    @staticmethod
    @cache.memoize(timeout=3600)
    def get_filterable_attributes():
        """Получение атрибутов для фильтрации"""
        return CarAttribute.get_filterable_attributes()
    
    @staticmethod
    @cache.memoize(timeout=3600)
    def get_brands_with_models():
        """Получение марок с моделями"""
        return get_car_brands_with_models()
    
    @staticmethod
    @cache.memoize(timeout=3600)
    def get_car_hierarchy(brand_id=None, model_id=None):
        """
        Получение иерархии марка -> модель -> поколение
        
        Args:
            brand_id: ID марки
            model_id: ID модели
            
        Returns:
            Иерархическая структура
        """
        return get_car_hierarchy(brand_id, model_id)
    
    @staticmethod
    @cache.memoize(timeout=3600)
    def get_reference_data():
        """Получение всех справочных данных"""
        return get_car_reference_data()
    
    @staticmethod
    @cache.memoize(timeout=3600)
    def get_years_range():
        """Получение диапазона доступных годов"""
        return get_years_range()
    
    @staticmethod
    def get_popular_brands(limit=20):
        """
        Получение популярных марок (по количеству объявлений)
        
        Args:
            limit: Количество марок
            
        Returns:
            Список популярных марок
        """
        from app.models.listing import ListingDetails
        
        # Запрос для получения марок с количеством объявлений
        subquery = db.session.query(
            func.cast(ListingDetails.searchable_fields['brand_id'], db.Integer).label('brand_id'),
            func.count().label('listings_count')
        ).group_by(
            func.cast(ListingDetails.searchable_fields['brand_id'], db.Integer)
        ).subquery()
        
        brands = db.session.query(CarBrand, subquery.c.listings_count).join(
            subquery,
            CarBrand.brand_id == subquery.c.brand_id
        ).filter(
            CarBrand.is_active == True
        ).order_by(
            subquery.c.listings_count.desc(),
            CarBrand.sort_order
        ).limit(limit).all()
        
        return [{'brand': brand, 'listings_count': count} for brand, count in brands]
    
    @staticmethod
    def get_popular_models_by_brand(brand_id, limit=20):
        """
        Получение популярных моделей марки
        
        Args:
            brand_id: ID марки
            limit: Количество моделей
            
        Returns:
            Список популярных моделей
        """
        from app.models.listing import ListingDetails
        
        # Проверяем существование марки
        CarService.get_brand(brand_id)
        
        subquery = db.session.query(
            func.cast(ListingDetails.searchable_fields['model_id'], db.Integer).label('model_id'),
            func.count().label('listings_count')
        ).filter(
            func.cast(ListingDetails.searchable_fields['brand_id'], db.Integer) == brand_id
        ).group_by(
            func.cast(ListingDetails.searchable_fields['model_id'], db.Integer)
        ).subquery()
        
        models = db.session.query(CarModel, subquery.c.listings_count).join(
            subquery,
            CarModel.model_id == subquery.c.model_id
        ).filter(
            CarModel.brand_id == brand_id,
            CarModel.is_active == True
        ).order_by(
            subquery.c.listings_count.desc(),
            CarModel.model_name
        ).limit(limit).all()
        
        return [{'model': model, 'listings_count': count} for model, count in models]
    
    @staticmethod
    def search_brands_and_models(query_text, limit=10):
        """
        Поиск по маркам и моделям
        
        Args:
            query_text: Поисковый запрос
            limit: Лимит результатов
            
        Returns:
            Результаты поиска
        """
        results = {
            'brands': [],
            'models': []
        }
        
        # Поиск марок
        brands = CarBrand.query.filter(
            CarBrand.brand_name.ilike(f'%{query_text}%'),
            CarBrand.is_active == True
        ).order_by(CarBrand.sort_order).limit(limit).all()
        
        results['brands'] = [brand.to_dict() for brand in brands]
        
        # Поиск моделей
        models = CarModel.query.join(CarBrand).filter(
            CarModel.model_name.ilike(f'%{query_text}%'),
            CarModel.is_active == True,
            CarBrand.is_active == True
        ).order_by(CarModel.model_name).limit(limit).all()
        
        results['models'] = [model.to_dict() for model in models]
        
        return results

