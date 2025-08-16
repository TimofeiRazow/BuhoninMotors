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
from app.utils.helpers import extract_filters_from_request
from app.utils.pagination import create_pagination_response


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
    user_id = g.current_user.user_id
    
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
        user_id=user_id,
        listing_data=listing_data,
        car_data=car_data if car_data else None
    )
    
    return jsonify({
        'data': listing.to_dict(include_details=True),
        'message': "Listing created successfully"
    }), 201


@bp.route('/<int:listing_id>', methods=['GET'])
@handle_errors
def get_listing(listing_id):
    """Получение объявления по ID"""
    user_id = None
    
    # Проверяем аутентификацию без требования
    if hasattr(g, 'current_user'):
        user_id = g.current_user.user_id
    
    listing = ListingService.get_listing(
        listing_id=listing_id,
        include_details=True
    )
    
    return jsonify({
        'data': listing.to_dict(include_details=True, user_id=user_id),
        'message': "Listing retrieved successfully"
    })


@bp.route('/<int:listing_id>', methods=['PUT'])
@handle_errors
@validate_json(UpdateListingSchema)
@auth_required
def update_listing(listing_id):
    """Обновление объявления"""
    data = g.validated_data
    user_id = g.current_user.user_id
    
    listing = ListingService.update_listing(
        listing_id=listing_id,
        user_id=user_id,
        update_data=data
    )
    
    return jsonify({
        'data': listing.to_dict(include_details=True),
        'message': "Listing updated successfully"
    })


@bp.route('/<int:listing_id>', methods=['DELETE'])
@handle_errors
@auth_required
def delete_listing(listing_id):
    """Удаление объявления"""
    user_id = g.current_user.user_id
    
    ListingService.delete_listing(
        listing_id=listing_id,
        user_id=user_id
    )
    
    return jsonify({
        'data': {'deleted': True},
        'message': "Listing deleted successfully"
    })


@bp.route('/<int:listing_id>/favorite', methods=['POST'])
@handle_errors
@auth_required
def toggle_favorite(listing_id):
    """Добавление/удаление из избранного"""
    user_id = g.current_user.user_id
    
    result = ListingService.toggle_favorite(
        listing_id=listing_id,
        user_id=user_id
    )
    
    return jsonify({
        'data': result,
        'message': f"Listing {result['action']} {'to' if result['action'] == 'added' else 'from'} favorites"
    })


@bp.route('/favorites', methods=['GET'])
@handle_errors
@auth_required
@paginate()
def get_favorites():
    """Получение избранных объявлений"""
    user_id = g.current_user.user_id
    
    # Получаем дополнительные параметры
    sort_by = request.args.get('sort', 'date_desc')
    include_expired = request.args.get('include_expired', 'false').lower() == 'true'
    folder_name = request.args.get('folder')
    
    pagination = ListingService.get_user_favorites(
        user_id=user_id,
        page=g.pagination['page'],
        per_page=g.pagination['per_page'],
        sort_by=sort_by,
        include_expired=include_expired,
        folder_name=folder_name
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
    user_id = g.current_user.user_id
    
    pagination = ListingService.get_user_listings(
        user_id=user_id,
        status=status_filter,
        page=g.pagination['page'],
        per_page=g.pagination['per_page']
    )
    
    response = create_pagination_response(pagination)
    
    return jsonify(response)


@bp.route('/<int:listing_id>/action', methods=['POST'])
@handle_errors
@validate_json(ListingActionSchema)
@auth_required
def perform_action(listing_id):
    """Выполнение действия с объявлением"""
    data = g.validated_data
    user_id = g.current_user.user_id
    
    result = ListingService.perform_listing_action(
        listing_id=listing_id,
        user_id=user_id,
        action=data['action']
    )
    
    return jsonify({
        'data': result,
        'message': result.get('message', 'Action performed successfully')
    })


@bp.route('/<int:listing_id>/view', methods=['POST'])
@handle_errors
def increment_view_count(listing_id):
    """Увеличение счетчика просмотров"""
    listing = ListingService.get_listing(listing_id, include_details=False)
    
    return jsonify({
        'data': {'view_count': listing.view_count},
        'message': "View count updated"
    })


# Дополнительные маршруты для избранного
@bp.route('/favorites/folders', methods=['GET'])
@handle_errors
@auth_required
def get_favorite_folders():
    """Получение папок избранного"""
    user_id = g.current_user.user_id
    
    from app.models.favorite import Favorite
    folders = Favorite.get_user_folders(user_id)
    
    return jsonify({
        'data': folders,
        'message': "Favorite folders retrieved successfully"
    })


@bp.route('/favorites/<int:listing_id>/move', methods=['POST'])
@handle_errors
@auth_required
def move_favorite_to_folder(listing_id):
    """Перемещение избранного в папку"""
    user_id = g.current_user.user_id
    folder_name = request.json.get('folder_name') if request.is_json else None
    
    from app.models.favorite import Favorite
    success = Favorite.move_to_folder(user_id, listing_id, folder_name)
    
    if success:
        return jsonify({
            'data': {'moved': True, 'folder_name': folder_name},
            'message': "Favorite moved to folder successfully"
        })
    else:
        return jsonify({
            'error': 'Not found',
            'message': "Favorite not found"
        }), 404


@bp.route('/popular', methods=['GET'])
@handle_errors
@cache_response(timeout=3600)  # Кэшируем на час
def get_popular_listings():
    """Получение популярных объявлений"""
    limit = min(int(request.args.get('limit', 20)), 50)
    days = min(int(request.args.get('days', 30)), 90)
    
    from app.models.listing import Listing
    popular_listings = Listing.get_popular_by_favorites(limit=limit, days=days)
    
    listings_data = [listing.to_dict() for listing in popular_listings]
    
    return jsonify({
        'data': listings_data,
        'message': "Popular listings retrieved successfully"
    })


@bp.route('/featured', methods=['GET'])
@handle_errors
@cache_response(timeout=1800)  # Кэшируем на 30 минут
@paginate()
def get_featured_listings():
    """Получение рекомендуемых объявлений"""
    from app.models.listing import Listing
    
    query = Listing.get_active_listings().filter(
        Listing.is_featured == True
    ).order_by(Listing.published_date.desc())
    
    from app.utils.pagination import paginate_query
    pagination = paginate_query(query, g.pagination['page'], g.pagination['per_page'])
    
    response = create_pagination_response(pagination)
    
    return jsonify(response)