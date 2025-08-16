# app/utils/decorators.py
"""
Декораторы для авторизации, валидации и других общих задач
"""

from functools import wraps
from flask import request, jsonify, g, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt, verify_jwt_in_request
from marshmallow import ValidationError as MarshmallowValidationError
from app.utils.exceptions import (
    ValidationError, AuthenticationError, AuthorizationError,
    UserNotFoundError, format_validation_error
)
from app.models.user import User


def validate_json(schema_class):
    """Декоратор для валидации JSON данных с помощью Marshmallow схемы"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not request.is_json:
                raise ValidationError("Request must be JSON")
            
            try:
                schema = schema_class()
                validated_data = schema.load(request.json or {})
                g.validated_data = validated_data
                return f(*args, **kwargs)
            except MarshmallowValidationError as err:
                formatted_errors = format_validation_error(err.messages)
                raise ValidationError(f"Validation failed: {formatted_errors}")
        
        return decorated_function
    return decorator


def auth_required(f):
    """Декоратор для проверки аутентификации пользователя"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            # Проверяем наличие заголовка Authorization
            auth_header = request.headers.get('Authorization', '')
            if not auth_header:
                return jsonify({
                    'error': 'Missing Authorization header',
                    'message': 'Authentication required'
                }), 401
            
            if not auth_header.startswith('Bearer '):
                return jsonify({
                    'error': 'Invalid Authorization header format',
                    'message': 'Authorization header must start with "Bearer "'
                }), 401
            
            # Извлекаем токен
            parts = auth_header.split(' ')
            if len(parts) != 2:
                return jsonify({
                    'error': 'Invalid Authorization header format',
                    'message': 'Authorization header must contain exactly one space'
                }), 401
            
            token = parts[1]
            
            # Проверяем формат JWT токена (должен содержать 3 части)
            token_parts = token.split('.')
            if len(token_parts) != 3:
                current_app.logger.error(f"Invalid JWT format: {len(token_parts)} parts instead of 3")
                return jsonify({
                    'error': 'Invalid token format',
                    'message': 'JWT token must contain exactly 3 parts separated by dots'
                }), 401
            
            # Проверяем, что каждая часть не пустая
            if not all(part.strip() for part in token_parts):
                current_app.logger.error("JWT token contains empty parts")
                return jsonify({
                    'error': 'Invalid token format',
                    'message': 'JWT token parts cannot be empty'
                }), 401
            
            try:
                # Проверяем JWT токен
                verify_jwt_in_request()
            except Exception as e:
                current_app.logger.error(f"JWT verification error: {str(e)}")
                if "Not enough segments" in str(e):
                    return jsonify({
                        'error': 'Malformed token',
                        'message': 'JWT token is malformed'
                    }), 401
                return jsonify({
                    'error': 'Token verification failed',
                    'message': str(e)
                }), 401
            
            # Получаем данные из токена
            try:
                user_id = get_jwt_identity()
                
                if not user_id:
                    return jsonify({
                        'error': 'Invalid token',
                        'message': 'Token does not contain user identity'
                    }), 401
                
                # Получаем пользователя
                user = User.query.filter(
                    User.user_id == int(user_id),
                    User.is_active == True
                ).first()
                
                if not user:
                    return jsonify({
                        'error': 'User not found',
                        'message': 'User not found or inactive'
                    }), 401
                
                # Сохраняем пользователя в g для использования в роуте
                g.current_user = user
                
                return f(*args, **kwargs)
                
            except ValueError:
                return jsonify({
                    'error': 'Invalid user ID',
                    'message': 'User ID in token is not valid'
                }), 401
            except Exception as e:
                current_app.logger.error(f"User verification error: {str(e)}")
                return jsonify({
                    'error': 'Authentication failed',
                    'message': 'Could not verify user'
                }), 401
            
        except Exception as e:
            current_app.logger.error(f"Auth decorator unexpected error: {str(e)}")
            return jsonify({
                'error': 'Authentication error',
                'message': 'An unexpected authentication error occurred'
            }), 500
    
    return decorated_function


def admin_required(f):
    """Декоратор для проверки прав администратора"""
    @wraps(f)
    @auth_required
    def decorated_function(*args, **kwargs):
        if g.current_user.user_type != 'admin':
            raise AuthorizationError("Admin access required")
        return f(*args, **kwargs)
    
    return decorated_function


def pro_user_required(f):
    """Декоратор для проверки PRO пользователя"""
    @wraps(f)
    @auth_required
    def decorated_function(*args, **kwargs):
        if not g.current_user.is_pro_user:
            raise AuthorizationError("PRO user access required")
        return f(*args, **kwargs)
    
    return decorated_function


def verified_user_required(f):
    """Декоратор для проверки верифицированного пользователя"""
    @wraps(f)
    @auth_required
    def decorated_function(*args, **kwargs):
        if not g.current_user.is_verified:
            raise AuthorizationError("Verified user access required")
        return f(*args, **kwargs)
    
    return decorated_function


def owner_or_admin_required(get_resource_owner_id):
    """
    Декоратор для проверки владельца ресурса или администратора
    get_resource_owner_id - функция для получения ID владельца ресурса
    """
    def decorator(f):
        @wraps(f)
        @auth_required
        def decorated_function(*args, **kwargs):
            resource_owner_id = get_resource_owner_id(*args, **kwargs)
            
            if (g.current_user.user_id != resource_owner_id and 
                g.current_user.user_type != 'admin'):
                raise AuthorizationError("Access denied")
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def listing_owner_required(f):
    """Декоратор для проверки владельца объявления"""
    @wraps(f)
    @auth_required
    def decorated_function(*args, **kwargs):
        from app.models.listing import Listing
        
        listing_id = kwargs.get('listing_id') or kwargs.get('id')
        if not listing_id:
            raise ValidationError("Listing ID is required")
        
        listing = Listing.query.get(listing_id)
        if not listing:
            from app.utils.exceptions import ListingNotFoundError
            raise ListingNotFoundError(listing_id)
        
        if (listing.user_id != g.current_user.user_id and 
            g.current_user.user_type != 'admin'):
            raise AuthorizationError("Access denied")
        
        g.current_listing = listing
        return f(*args, **kwargs)
    
    return decorated_function


def rate_limit_by_user(limit_key, max_requests=10, window_minutes=60):
    """Декоратор для ограничения запросов по пользователю"""
    def decorator(f):
        @wraps(f)
        @auth_required
        def decorated_function(*args, **kwargs):
            from app.extensions import cache
            from app.utils.exceptions import RateLimitError
            import time
            
            user_id = g.current_user.user_id
            cache_key = f"rate_limit:{limit_key}:{user_id}"
            
            # Получаем текущие запросы
            current_requests = cache.get(cache_key) or []
            current_time = time.time()
            window_start = current_time - (window_minutes * 60)
            
            # Фильтруем запросы в пределах окна
            recent_requests = [req_time for req_time in current_requests if req_time > window_start]
            
            if len(recent_requests) >= max_requests:
                raise RateLimitError(f"Rate limit exceeded: {max_requests} requests per {window_minutes} minutes")
            
            # Добавляем текущий запрос
            recent_requests.append(current_time)
            cache.set(cache_key, recent_requests, timeout=window_minutes * 60)
            
            return f(*args, **kwargs)
        
        return decorated_function
    return decorator


def rate_limit_by_ip(limit_key, max_requests=10, window_minutes=60):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            from app.extensions import cache
            from app.utils.exceptions import RateLimitError
            import time
            
            ip = request.remote_addr
            cache_key = f"rate_limit:{limit_key}:{ip}"
            
            current_requests = cache.get(cache_key) or []
            current_time = time.time()
            window_start = current_time - (window_minutes * 60)
            recent_requests = [t for t in current_requests if t > window_start]
            
            if len(recent_requests) >= max_requests:
                raise RateLimitError(f"Rate limit exceeded: {max_requests} requests per {window_minutes} minutes")
            
            recent_requests.append(current_time)
            cache.set(cache_key, recent_requests, timeout=window_minutes * 60)
            
            return f(*args, **kwargs)
        
        return decorated_function
    return decorator


def cache_response(timeout=300, key_prefix=None):
    """Декоратор для кэширования ответов"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            from app.extensions import cache
            import hashlib
            
            # Генерируем ключ кэша
            if key_prefix:
                cache_key = f"{key_prefix}:{request.endpoint}"
            else:
                cache_key = f"cache:{request.endpoint}"
            
            # Добавляем параметры запроса к ключу
            if request.args:
                args_str = str(sorted(request.args.items()))
                args_hash = hashlib.md5(args_str.encode()).hexdigest()
                cache_key += f":{args_hash}"
            
            # Добавляем ID пользователя если есть аутентификация
            if hasattr(g, 'current_user'):
                cache_key += f":user:{g.current_user.user_id}"
            
            # Проверяем кэш
            cached_response = cache.get(cache_key)
            if cached_response:
                return cached_response
            
            # Выполняем функцию и кэшируем результат
            response = f(*args, **kwargs)
            cache.set(cache_key, response, timeout=timeout)
            
            return response
        
        return decorated_function
    return decorator


def log_api_call(f):
    """Декоратор для логирования API вызовов"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        import logging
        import time
        
        start_time = time.time()
        
        # Логируем входящий запрос
        logger = logging.getLogger(__name__)
        user_id = getattr(g, 'current_user', {}).user_id if hasattr(g, 'current_user') else 'anonymous'
        
        logger.info(f"API Call: {request.method} {request.endpoint} - User: {user_id} - IP: {request.remote_addr}")
        
        try:
            response = f(*args, **kwargs)
            execution_time = time.time() - start_time
            logger.info(f"API Success: {request.endpoint} - Duration: {execution_time:.3f}s")
            return response
            
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"API Error: {request.endpoint} - Duration: {execution_time:.3f}s - Error: {str(e)}")
            raise
    
    return decorated_function


def handle_errors(f):
    """Декоратор для обработки ошибок и возврата JSON ответов"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except Exception as e:
            from app.utils.exceptions import BaseAppException, handle_db_error
            from sqlalchemy.exc import SQLAlchemyError
            import logging
            
            logger = logging.getLogger(__name__)
            
            if isinstance(e, BaseAppException):
                logger.warning(f"Application error: {e.message}")
                return jsonify({
                    'error': e.__class__.__name__,
                    'message': e.message
                }), e.code
            
            elif isinstance(e, SQLAlchemyError):
                logger.error(f"Database error: {str(e)}")
                handled_error = handle_db_error(e)
                return jsonify({
                    'error': handled_error.__class__.__name__,
                    'message': handled_error.message
                }), handled_error.code
            
            else:
                logger.error(f"Unexpected error: {str(e)}")
                return jsonify({
                    'error': 'InternalServerError',
                    'message': 'An unexpected error occurred'
                }), 500
    
    return decorated_function


def paginate(default_per_page=20, max_per_page=100):
    """Декоратор для пагинации результатов"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            try:
                page = int(request.args.get('page', 1))
                per_page = int(request.args.get('per_page', default_per_page))
                
                if page < 1:
                    page = 1
                
                if per_page > max_per_page:
                    per_page = max_per_page
                elif per_page < 1:
                    per_page = default_per_page
                
                g.pagination = {
                    'page': page,
                    'per_page': per_page,
                    'offset': (page - 1) * per_page
                }
                
                return f(*args, **kwargs)
                
            except ValueError:
                raise ValidationError("Invalid pagination parameters")
        
        return decorated_function
    return decorator


def require_fields(*required_fields):
    """Декоратор для проверки обязательных полей в JSON"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not request.is_json:
                raise ValidationError("Request must be JSON")
            
            data = request.json or {}
            missing_fields = []
            
            for field in required_fields:
                if field not in data or data[field] is None or data[field] == '':
                    missing_fields.append(field)
            
            if missing_fields:
                raise ValidationError(f"Missing required fields: {', '.join(missing_fields)}")
            
            return f(*args, **kwargs)
        
        return decorated_function
    return decorator