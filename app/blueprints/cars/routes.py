# app/blueprints/cars/routes.py
from flask import request, jsonify
from app.blueprints.cars import bp
from app.blueprints.cars.services import CarService
from app.blueprints.cars.schemas import (
    BrandSchema, ModelSchema, GenerationSchema, BodyTypeSchema,
    EngineTypeSchema, TransmissionTypeSchema, DriveTypeSchema,
    ColorSchema, FeatureSchema, AttributeGroupSchema
)
from app.utils.decorators import handle_errors, cache_response
from app.utils.helpers import build_response


@bp.route('/brands', methods=['GET'])
@handle_errors
@cache_response(timeout=3600)
def get_brands():
    """Получение марок автомобилей"""
    search = request.args.get('search')
    limit = request.args.get('limit', type=int)
    include_models = request.args.get('include_models', 'false').lower() == 'true'
    popular = request.args.get('popular', 'false').lower() == 'true'
    
    if popular:
        # Получаем популярные марки
        brands_data = CarService.get_popular_brands(limit or 20)
        schema = BrandSchema(many=True)
        brands = [item['brand'] for item in brands_data]
        result = schema.dump(brands)
        
        # Добавляем количество объявлений
        for i, item in enumerate(brands_data):
            result[i]['listings_count'] = item['listings_count']
    
    elif include_models:
        # Получаем марки с моделями
        brands_data = CarService.get_brands_with_models()
        result = brands_data
    
    else:
        # Обычный запрос марок
        brands = CarService.get_brands(search, limit)
        schema = BrandSchema(many=True)
        result = schema.dump(brands)
    
    return jsonify(build_response(
        data=result,
        message="Brands retrieved successfully"
    ))


@bp.route('/brands/<int:brand_id>', methods=['GET'])
@handle_errors
@cache_response(timeout=3600)
def get_brand(brand_id):
    """Получение марки по ID"""
    brand = CarService.get_brand(brand_id)
    schema = BrandSchema()
    
    return jsonify(build_response(
        data=schema.dump(brand),
        message="Brand retrieved successfully"
    ))


@bp.route('/brands/<int:brand_id>/models', methods=['GET'])
@handle_errors
@cache_response(timeout=3600)
def get_models_by_brand(brand_id):
    """Получение моделей по марке"""
    search = request.args.get('search')
    popular = request.args.get('popular', 'false').lower() == 'true'
    
    if popular:
        # Получаем популярные модели
        models_data = CarService.get_popular_models_by_brand(brand_id, 20)
        schema = ModelSchema(many=True)
        models = [item['model'] for item in models_data]
        result = schema.dump(models)
        
        # Добавляем количество объявлений
        for i, item in enumerate(models_data):
            result[i]['listings_count'] = item['listings_count']
    
    else:
        # Обычный запрос моделей
        models = CarService.get_models_by_brand(brand_id, search)
        schema = ModelSchema(many=True)
        result = schema.dump(models)
    
    return jsonify(build_response(
        data=result,
        message="Models retrieved successfully"
    ))


@bp.route('/models/<int:model_id>', methods=['GET'])
@handle_errors
@cache_response(timeout=3600)
def get_model(model_id):
    """Получение модели по ID"""
    model = CarService.get_model(model_id)
    schema = ModelSchema()
    
    return jsonify(build_response(
        data=schema.dump(model),
        message="Model retrieved successfully"
    ))


@bp.route('/models/<int:model_id>/generations', methods=['GET'])
@handle_errors
@cache_response(timeout=3600)
def get_generations_by_model(model_id):
    """Получение поколений по модели"""
    generations = CarService.get_generations_by_model(model_id)
    schema = GenerationSchema(many=True)
    
    return jsonify(build_response(
        data=schema.dump(generations),
        message="Generations retrieved successfully"
    ))


@bp.route('/body-types', methods=['GET'])
@handle_errors
@cache_response(timeout=3600)
def get_body_types():
    """Получение типов кузова"""
    body_types = CarService.get_body_types()
    schema = BodyTypeSchema(many=True)
    
    return jsonify(build_response(
        data=schema.dump(body_types),
        message="Body types retrieved successfully"
    ))


@bp.route('/engine-types', methods=['GET'])
@handle_errors
@cache_response(timeout=3600)
def get_engine_types():
    """Получение типов двигателей"""
    engine_types = CarService.get_engine_types()
    schema = EngineTypeSchema(many=True)
    
    return jsonify(build_response(
        data=schema.dump(engine_types),
        message="Engine types retrieved successfully"
    ))


@bp.route('/transmission-types', methods=['GET'])
@handle_errors
@cache_response(timeout=3600)
def get_transmission_types():
    """Получение типов трансмиссий"""
    transmission_types = CarService.get_transmission_types()
    schema = TransmissionTypeSchema(many=True)
    
    return jsonify(build_response(
        data=schema.dump(transmission_types),
        message="Transmission types retrieved successfully"
    ))


@bp.route('/drive-types', methods=['GET'])
@handle_errors
@cache_response(timeout=3600)
def get_drive_types():
    """Получение типов приводов"""
    drive_types = CarService.get_drive_types()
    schema = DriveTypeSchema(many=True)
    
    return jsonify(build_response(
        data=schema.dump(drive_types),
        message="Drive types retrieved successfully"
    ))


@bp.route('/colors', methods=['GET'])
@handle_errors
@cache_response(timeout=3600)
def get_colors():
    """Получение цветов"""
    colors = CarService.get_colors()
    schema = ColorSchema(many=True)
    
    return jsonify(build_response(
        data=schema.dump(colors),
        message="Colors retrieved successfully"
    ))


@bp.route('/features', methods=['GET'])
@handle_errors
@cache_response(timeout=3600)
def get_features():
    """Получение особенностей автомобилей"""
    category_id = request.args.get('category_id', type=int)
    search = request.args.get('search')
    
    features = CarService.get_features(category_id, search)
    schema = FeatureSchema(many=True)
    
    return jsonify(build_response(
        data=schema.dump(features),
        message="Features retrieved successfully"
    ))


@bp.route('/attributes', methods=['GET'])
@handle_errors
@cache_response(timeout=3600)
def get_attributes():
    """Получение атрибутов автомобилей"""
    grouped = request.args.get('grouped', 'false').lower() == 'true'
    searchable_only = request.args.get('searchable_only', 'false').lower() == 'true'
    filterable_only = request.args.get('filterable_only', 'false').lower() == 'true'
    
    if searchable_only:
        attributes = CarService.get_searchable_attributes()
        result = [attr.to_dict() for attr in attributes]
    
    elif filterable_only:
        attributes = CarService.get_filterable_attributes()
        result = [attr.to_dict() for attr in attributes]
    
    elif grouped:
        result = CarService.get_attributes_grouped()
    
    else:
        result = CarService.get_attributes_grouped()
    
    return jsonify(build_response(
        data=result,
        message="Attributes retrieved successfully"
    ))


@bp.route('/hierarchy', methods=['GET'])
@handle_errors
@cache_response(timeout=3600)
def get_hierarchy():
    """Получение иерархии марка -> модель -> поколение"""
    brand_id = request.args.get('brand_id', type=int)
    model_id = request.args.get('model_id', type=int)
    
    hierarchy = CarService.get_car_hierarchy(brand_id, model_id)
    
    return jsonify(build_response(
        data=hierarchy,
        message="Car hierarchy retrieved successfully"
    ))


@bp.route('/reference-data', methods=['GET'])
@handle_errors
@cache_response(timeout=3600)
def get_reference_data():
    """Получение всех справочных данных"""
    data = CarService.get_reference_data()
    
    return jsonify(build_response(
        data=data,
        message="Reference data retrieved successfully"
    ))


@bp.route('/years', methods=['GET'])
@handle_errors
@cache_response(timeout=3600)
def get_years():
    """Получение диапазона доступных годов"""
    years_data = CarService.get_years_range()
    
    return jsonify(build_response(
        data=years_data,
        message="Years range retrieved successfully"
    ))


@bp.route('/search', methods=['GET'])
@handle_errors
@cache_response(timeout=300)
def search_cars():
    """Поиск по маркам и моделям"""
    query = request.args.get('q', '').strip()
    limit = request.args.get('limit', 10, type=int)
    
    if not query or len(query) < 2:
        return jsonify(build_response(
            data={'brands': [], 'models': []},
            message="Search query too short"
        ))
    
    results = CarService.search_brands_and_models(query, limit)
    
    return jsonify(build_response(
        data=results,
        message="Search completed successfully"
    ))