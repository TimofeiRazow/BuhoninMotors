# app/blueprints/locations/routes.py
from flask import request, jsonify
from app.blueprints.locations import bp
from app.blueprints.locations.services import LocationService
from app.blueprints.locations.schemas import (
    CountrySchema, RegionSchema, CitySchema, LocationSearchSchema, NearbySearchSchema
)
from app.utils.decorators import handle_errors, cache_response, validate_json
from app.utils.helpers import build_response


@bp.route('/countries', methods=['GET'])
@handle_errors
@cache_response(timeout=3600)
def get_countries():
    """Получение всех стран"""
    countries = LocationService.get_countries()
    schema = CountrySchema(many=True)
    
    return jsonify(build_response(
        data=schema.dump(countries),
        message="Countries retrieved successfully"
    ))


@bp.route('/countries/<int:country_id>', methods=['GET'])
@handle_errors
@cache_response(timeout=3600)
def get_country(country_id):
    """Получение страны по ID"""
    country = LocationService.get_country(country_id)
    schema = CountrySchema()
    
    return jsonify(build_response(
        data=schema.dump(country),
        message="Country retrieved successfully"
    ))


@bp.route('/regions', methods=['GET'])
@handle_errors
@cache_response(timeout=3600)
def get_regions():
    """Получение регионов"""
    country_id = request.args.get('country_id', type=int)
    regions = LocationService.get_regions(country_id)
    schema = RegionSchema(many=True)
    
    return jsonify(build_response(
        data=schema.dump(regions),
        message="Regions retrieved successfully"
    ))


@bp.route('/regions/<int:region_id>', methods=['GET'])
@handle_errors
@cache_response(timeout=3600)
def get_region(region_id):
    """Получение региона по ID"""
    region = LocationService.get_region(region_id)
    schema = RegionSchema()
    
    return jsonify(build_response(
        data=schema.dump(region),
        message="Region retrieved successfully"
    ))


@bp.route('/cities', methods=['GET'])
@handle_errors
@cache_response(timeout=1800)
def get_cities():
    """Получение городов"""
    region_id = request.args.get('region_id', type=int)
    country_id = request.args.get('country_id', type=int)
    limit = request.args.get('limit', type=int)
    popular = request.args.get('popular', 'false').lower() == 'true'
    
    if popular:
        cities = LocationService.get_popular_cities(limit or 20)
    else:
        cities = LocationService.get_cities(region_id, country_id, limit)
    
    schema = CitySchema(many=True)
    
    return jsonify(build_response(
        data=schema.dump(cities),
        message="Cities retrieved successfully"
    ))


@bp.route('/cities/<int:city_id>', methods=['GET'])
@handle_errors
@cache_response(timeout=1800)
def get_city(city_id):
    """Получение города по ID"""
    city = LocationService.get_city(city_id)
    schema = CitySchema()
    
    return jsonify(build_response(
        data=schema.dump(city),
        message="City retrieved successfully"
    ))


@bp.route('/cities/search', methods=['GET'])
@handle_errors
@cache_response(timeout=600)  # 10 минут
def search_cities():
    """Поиск городов"""
    query = request.args.get('q', '').strip()
    country_id = request.args.get('country_id', type=int)
    region_id = request.args.get('region_id', type=int)
    limit = request.args.get('limit', 10, type=int)
    
    if not query or len(query) < 2:
        return jsonify(build_response(
            data=[],
            message="Search query too short"
        ))
    
    cities = LocationService.search_cities(query, country_id, region_id, limit)
    schema = CitySchema(many=True)
    
    return jsonify(build_response(
        data=schema.dump(cities),
        message="Cities search completed"
    ))


@bp.route('/search', methods=['GET'])
@handle_errors
@cache_response(timeout=600)
def search_locations():
    """Универсальный поиск локаций"""
    query = request.args.get('q', '').strip()
    country_id = request.args.get('country_id', type=int)
    region_id = request.args.get('region_id', type=int)
    limit = request.args.get('limit', 10, type=int)
    
    if not query or len(query) < 2:
        return jsonify(build_response(
            data={'countries': [], 'regions': [], 'cities': []},
            message="Search query too short"
        ))
    
    results = LocationService.search_locations(query, country_id, region_id, limit)
    
    return jsonify(build_response(
        data=results,
        message="Location search completed"
    ))


@bp.route('/nearby', methods=['GET'])
@handle_errors
@cache_response(timeout=600)
def find_nearby():
    """Поиск городов поблизости"""
    try:
        latitude = float(request.args.get('lat'))
        longitude = float(request.args.get('lng'))
        radius = int(request.args.get('radius', 50))
        limit = int(request.args.get('limit', 20))
    except (TypeError, ValueError):
        return jsonify(build_response(
            data=[],
            message="Invalid coordinates provided"
        )), 400
    
    cities = LocationService.find_nearby_cities(latitude, longitude, radius, limit)
    
    return jsonify(build_response(
        data=cities,
        message="Nearby cities found"
    ))


@bp.route('/regions/<int:region_id>/cities', methods=['GET'])
@handle_errors
@cache_response(timeout=1800)
def get_cities_by_region(region_id):
    """Получение городов региона"""
    cities = LocationService.get_cities_by_region(region_id)
    schema = CitySchema(many=True)
    
    return jsonify(build_response(
        data=schema.dump(cities),
        message="Cities retrieved successfully"
    ))


@bp.route('/hierarchy', methods=['GET'])
@handle_errors
@cache_response(timeout=3600)
def get_hierarchy():
    """Получение иерархии локаций"""
    hierarchy = LocationService.get_location_hierarchy()
    
    return jsonify(build_response(
        data=hierarchy,
        message="Location hierarchy retrieved successfully"
    ))


@bp.route('/stats', methods=['GET'])
@handle_errors
@cache_response(timeout=3600)
def get_stats():
    """Получение статистики локаций"""
    stats = LocationService.get_location_stats()
    
    return jsonify(build_response(
        data=stats,
        message="Location statistics retrieved successfully"
    ))