# app/blueprints/listings/routes.py
from flask import request, jsonify, g
from app.blueprints.listings import bp
from app.blueprints.listings.schemas import (
    CreateCarListingSchema, UpdateListingSchema, ListingSearchSchema, ListingActionSchema
)
from app.blueprints.listings.services import ListingService
from app.utils.decorators import (
    validate_json, handle_errors, auth_required, listing_owner_required, 
    paginate, cache_response
)
from app.utils.helpers import build_response, extract_filters_from_request
from app.utils.pagination import create_pagination_response
from app.database import db

@bp.route('/', methods=['GET'])
@handle_errors
@cache_response(timeout=300)
@paginate()
def search_listings():
    """Поиск объявлений"""
    # Извлекаем фильтры из параметров запроса
    filters = extract_filters_from_request()
    
    # Добавляем параметры пагинации
    filters.update(g.pagination)
    
    # Выполняем поиск
    pagination = ListingService.search_listings(filters)
    
    # Формируем ответ
    response = create_pagination_response(pagination)
    
    return jsonify(response)


@bp.route('/', methods=['POST'])
@handle_errors
@validate_json(CreateCarListingSchema)
@auth_required
def create_listing():
    """Создание нового объявления"""
    data = g.validated_data
    
    # Разделяем данные на основные и автомобильные
    car_fields = [
        'brand_id', 'model_id', 'generation_id', 'year', 'mileage', 'condition',
        'body_type_id', 'color_id', 'engine_volume', 'engine_type_id',
        'transmission_id', 'drive_type_id', 'power_hp', 'fuel_consumption',
        'vin_number', 'customs_cleared', 'exchange_possible', 'credit_available',
        'features'
    ]
    
    listing_data = {k: v for k, v in data.items() if k not in car_fields}
    car_data = {k: v for k, v in data.items() if k in car_fields}
    
    # Создаем объявление
    listing = ListingService.create_listing(
        user_id=g.current_user.user_id,
        listing_data=listing_data,
        car_data=car_data if car_data else None
    )
    
    return jsonify(build_response(
        data=listing.to_dict(include_details=True),
        message="Listing created successfully",
        status_code=201
    ))


@bp.route('/<int:listing_id>', methods=['GET'])
@handle_errors
def get_listing(listing_id):
    """Получение объявления по ID"""
    user_id = None
    if hasattr(g, 'current_user'):
        user_id = g.current_user.user_id
    
    listing = ListingService.get_listing(
        listing_id=listing_id,
        user_id=user_id,
        include_details=True
    )
    
    return jsonify(build_response(
        data=listing.to_dict(include_details=True, user_id=user_id),
        message="Listing retrieved successfully"
    ))


@bp.route('/<int:listing_id>', methods=['PUT'])
@handle_errors
@validate_json(UpdateListingSchema)
@listing_owner_required
def update_listing(listing_id):
    """Обновление объявления"""
    data = g.validated_data
    
    listing = ListingService.update_listing(
        listing_id=listing_id,
        user_id=g.current_user.user_id,
        update_data=data
    )
    
    return jsonify(build_response(
        data=listing.to_dict(include_details=True),
        message="Listing updated successfully"
    ))


@bp.route('/<int:listing_id>', methods=['DELETE'])
@handle_errors
@listing_owner_required
def delete_listing(listing_id):
    """Удаление объявления"""
    ListingService.delete_listing(
        listing_id=listing_id,
        user_id=g.current_user.user_id
    )
    
    return jsonify(build_response(
        data={'deleted': True},
        message="Listing deleted successfully"
    ))


@bp.route('/<int:listing_id>/favorite', methods=['POST'])
@handle_errors
@auth_required
def toggle_favorite(listing_id):
    """Добавление/удаление из избранного"""
    result = ListingService.toggle_favorite(
        listing_id=listing_id,
        user_id=g.current_user.user_id
    )
    
    return jsonify(build_response(
        data=result,
        message=f"Listing {result['action']} {'to' if result['action'] == 'added' else 'from'} favorites"
    ))


@bp.route('/favorites', methods=['GET'])
@handle_errors
@auth_required
@paginate()
def get_favorites():
    """Получение избранных объявлений"""
    pagination = ListingService.get_user_favorites(
        user_id=g.current_user.user_id,
        page=g.pagination['page'],
        per_page=g.pagination['per_page']
    )
    
    response = create_pagination_response(pagination)
    
    return jsonify(response)


@bp.route('/my', methods=['GET'])
@handle_errors
@auth_required
@paginate()
def get_my_listings():
    """Получение объявлений текущего пользователя"""
    status_filter = request.args.get('status')
    
    pagination = ListingService.get_user_listings(
        user_id=g.current_user.user_id,
        status=status_filter,
        page=g.pagination['page'],
        per_page=g.pagination['per_page']
    )
    
    response = create_pagination_response(pagination)
    
    return jsonify(response)


@bp.route('/<int:listing_id>/action', methods=['POST'])
@handle_errors
@validate_json(ListingActionSchema)
@listing_owner_required
def perform_action(listing_id):
    """Выполнение действия с объявлением"""
    data = g.validated_data
    
    result = ListingService.perform_listing_action(
        listing_id=listing_id,
        user_id=g.current_user.user_id,
        action=data['action']
    )
    
    return jsonify(build_response(
        data=result,
        message=result.get('message', 'Action performed successfully')
    ))


@bp.route('/<int:listing_id>/view', methods=['POST'])
@handle_errors
def increment_view_count(listing_id):
    """Увеличение счетчика просмотров"""
    listing = ListingService.get_listing(listing_id, include_details=False)
    
    return jsonify(build_response(
        data={'view_count': listing.view_count},
        message="View count updated"
    ))