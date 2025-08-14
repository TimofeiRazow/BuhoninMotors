# app/blueprints/listings/schemas.py
from marshmallow import Schema, fields, validate, validates, ValidationError, post_load
from app.models.car import validate_car_year


class CreateListingSchema(Schema):
    """Схема для создания объявления"""
    title = fields.Str(required=True, validate=validate.Length(min=5, max=255))
    description = fields.Str(required=False, validate=validate.Length(max=5000))
    price = fields.Decimal(required=False, validate=validate.Range(min=0))
    currency_id = fields.Int(required=False)
    city_id = fields.Int(required=True)
    address = fields.Str(required=False, validate=validate.Length(max=500))
    latitude = fields.Decimal(required=False, validate=validate.Range(min=-90, max=90))
    longitude = fields.Decimal(required=False, validate=validate.Range(min=-180, max=180))
    contact_phone = fields.Str(required=False, validate=validate.Length(max=20))
    contact_name = fields.Str(required=False, validate=validate.Length(max=100))
    is_negotiable = fields.Bool(required=False, default=True)
    category_id = fields.Int(required=False)
    
    @validates('latitude')
    def validate_coordinates(self, value):
        if value is not None and 'longitude' not in self.context:
            raise ValidationError("Longitude is required when latitude is provided")
    
    @post_load
    def validate_coordinates_pair(self, data, **kwargs):
        lat = data.get('latitude')
        lng = data.get('longitude')
        
        if (lat is None) != (lng is None):
            raise ValidationError("Both latitude and longitude must be provided together")
        
        return data


class CreateCarListingSchema(CreateListingSchema):
    """Схема для создания объявления о продаже автомобиля"""
    # Обязательные поля для автомобиля
    brand_id = fields.Int(required=True)
    model_id = fields.Int(required=True)
    year = fields.Int(required=True)
    mileage = fields.Int(required=True, validate=validate.Range(min=0))
    condition = fields.Str(required=True, validate=validate.OneOf([
        'excellent', 'good', 'satisfactory', 'needs_repair', 'damaged'
    ]))
    body_type_id = fields.Int(required=True)
    
    # Опциональные поля
    generation_id = fields.Int(required=False)
    color_id = fields.Int(required=False)
    engine_volume = fields.Decimal(required=False, validate=validate.Range(min=0.1, max=20))
    engine_type_id = fields.Int(required=False)
    transmission_id = fields.Int(required=False)
    drive_type_id = fields.Int(required=False)
    power_hp = fields.Int(required=False, validate=validate.Range(min=1, max=2000))
    fuel_consumption = fields.Decimal(required=False, validate=validate.Range(min=0.1, max=50))
    
    # Дополнительные характеристики
    vin_number = fields.Str(required=False, validate=validate.Length(equal=17))
    customs_cleared = fields.Bool(required=False, default=False)
    exchange_possible = fields.Bool(required=False, default=False)
    credit_available = fields.Bool(required=False, default=False)
    
    # Особенности
    features = fields.List(fields.Int(), required=False)
    
    @validates('year')
    def validate_year(self, value):
        if not validate_car_year(value):
            raise ValidationError("Invalid car year")
    
    @validates('vin_number')
    def validate_vin(self, value):
        if value:
            from app.utils.helpers import validate_vin_number
            if not validate_vin_number(value):
                raise ValidationError("Invalid VIN number")


class UpdateListingSchema(Schema):
    """Схема для обновления объявления"""
    title = fields.Str(required=False, validate=validate.Length(min=5, max=255))
    description = fields.Str(required=False, validate=validate.Length(max=5000))
    price = fields.Decimal(required=False, validate=validate.Range(min=0))
    currency_id = fields.Int(required=False)
    city_id = fields.Int(required=False)
    address = fields.Str(required=False, validate=validate.Length(max=500))
    latitude = fields.Decimal(required=False, validate=validate.Range(min=-90, max=90))
    longitude = fields.Decimal(required=False, validate=validate.Range(min=-180, max=180))
    contact_phone = fields.Str(required=False, validate=validate.Length(max=20))
    contact_name = fields.Str(required=False, validate=validate.Length(max=100))
    is_negotiable = fields.Bool(required=False)


class ListingSearchSchema(Schema):
    """Схема для поиска объявлений"""
    # Текстовый поиск
    q = fields.Str(required=False, validate=validate.Length(min=2, max=200))
    
    # Фильтры по категории и типу
    category_id = fields.Int(required=False)
    listing_type = fields.Str(required=False, validate=validate.OneOf([
        'car_listing', 'parts_listing', 'service_listing', 'commercial_listing'
    ]))
    
    # Географические фильтры
    city_id = fields.Int(required=False)
    region_id = fields.Int(required=False)
    latitude = fields.Decimal(required=False, validate=validate.Range(min=-90, max=90))
    longitude = fields.Decimal(required=False, validate=validate.Range(min=-180, max=180))
    radius = fields.Int(required=False, validate=validate.Range(min=1, max=1000), default=50)
    
    # Фильтры по цене
    price_from = fields.Decimal(required=False, validate=validate.Range(min=0))
    price_to = fields.Decimal(required=False, validate=validate.Range(min=0))
    currency = fields.Str(required=False, validate=validate.OneOf(['KZT', 'USD', 'EUR', 'RUB']))
    
    # Автомобильные фильтры
    brand_id = fields.Int(required=False)
    model_id = fields.Int(required=False)
    year_from = fields.Int(required=False, validate=validate.Range(min=1950, max=2030))
    year_to = fields.Int(required=False, validate=validate.Range(min=1950, max=2030))
    mileage_from = fields.Int(required=False, validate=validate.Range(min=0))
    mileage_to = fields.Int(required=False, validate=validate.Range(min=0))
    body_type_id = fields.Int(required=False)
    engine_type_id = fields.Int(required=False)
    transmission_id = fields.Int(required=False)
    drive_type_id = fields.Int(required=False)
    color_id = fields.Int(required=False)
    condition = fields.Str(required=False, validate=validate.OneOf([
        'excellent', 'good', 'satisfactory', 'needs_repair', 'damaged'
    ]))
    
    # Булевы фильтры
    is_featured = fields.Bool(required=False)
    is_urgent = fields.Bool(required=False)
    customs_cleared = fields.Bool(required=False)
    exchange_possible = fields.Bool(required=False)
    
    # Сортировка
    sort_by = fields.Str(required=False, validate=validate.OneOf([
        'date_desc', 'date_asc', 'price_desc', 'price_asc', 'mileage_asc', 'mileage_desc',
        'year_desc', 'year_asc', 'relevance'
    ]), default='date_desc')
    
    # Пагинация
    page = fields.Int(required=False, validate=validate.Range(min=1), default=1)
    per_page = fields.Int(required=False, validate=validate.Range(min=1, max=100), default=20)


class ListingActionSchema(Schema):
    """Схема для действий с объявлением"""
    action = fields.Str(required=True, validate=validate.OneOf([
        'activate', 'deactivate', 'archive', 'mark_sold', 'renew'
    ]))


