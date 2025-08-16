# app/utils/helpers.py
"""
Вспомогательные функции общего назначения
"""

import re
import secrets
import string
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from flask import request, url_for
import phonenumbers
from phonenumbers import NumberParseException
from email_validator import validate_email, EmailNotValidError


def generate_verification_code(length=6, digits_only=True):
    """Генерация кода верификации"""
    if digits_only:
        return ''.join(secrets.choice(string.digits) for _ in range(length))
    else:
        alphabet = string.ascii_uppercase + string.digits
        return ''.join(secrets.choice(alphabet) for _ in range(length))


def generate_secure_token(length=32):
    """Генерация безопасного токена"""
    return secrets.token_urlsafe(length)


def normalize_phone_number(phone_number: str, default_country='KZ') -> str:
    """
    Нормализация номера телефона
    
    Args:
        phone_number: Номер телефона
        default_country: Страна по умолчанию
        
    Returns:
        Нормализованный номер в международном формате
        
    Raises:
        ValueError: Если номер некорректный
    """
    try:
        # Убираем все нецифровые символы кроме +
        cleaned = re.sub(r'[^\d+]', '', phone_number)
        
        # Парсим номер
        parsed = phonenumbers.parse(cleaned, default_country)
        
        # Проверяем валидность
        if not phonenumbers.is_valid_number(parsed):
            raise ValueError("Invalid phone number")
        
        # Возвращаем в международном формате
        return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
        
    except NumberParseException:
        raise ValueError("Invalid phone number format")


def validate_email_address(email: str) -> str:
    """
    Валидация и нормализация email адреса
    
    Args:
        email: Email адрес
        
    Returns:
        Нормализованный email
        
    Raises:
        ValueError: Если email некорректный
    """
    try:
        # Валидируем email
        validation = validate_email(email)
        return validation.email
    except EmailNotValidError:
        raise ValueError("Invalid email address")


def clean_string(text: str, max_length: Optional[int] = None) -> str:
    """
    Очистка строки от лишних символов
    
    Args:
        text: Исходная строка
        max_length: Максимальная длина
        
    Returns:
        Очищенная строка
    """
    if not text:
        return ""
    
    # Убираем лишние пробелы
    cleaned = re.sub(r'\s+', ' ', text.strip())
    
    # Обрезаем до максимальной длины
    if max_length and len(cleaned) > max_length:
        cleaned = cleaned[:max_length].rstrip()
    
    return cleaned


def slugify(text: str, max_length: int = 100) -> str:
    """
    Создание URL-friendly строки (slug)
    
    Args:
        text: Исходный текст
        max_length: Максимальная длина
        
    Returns:
        Slug строка
    """
    # Приводим к нижнему регистру
    text = text.lower()
    
    # Заменяем кириллицу на латиницу (упрощенная транслитерация)
    cyrillic_map = {
        'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd', 'е': 'e', 'ё': 'yo',
        'ж': 'zh', 'з': 'z', 'и': 'i', 'й': 'y', 'к': 'k', 'л': 'l', 'м': 'm',
        'н': 'n', 'о': 'o', 'п': 'p', 'р': 'r', 'с': 's', 'т': 't', 'у': 'u',
        'ф': 'f', 'х': 'kh', 'ц': 'ts', 'ч': 'ch', 'ш': 'sh', 'щ': 'sch',
        'ы': 'y', 'э': 'e', 'ю': 'yu', 'я': 'ya', 'ь': '', 'ъ': ''
    }
    
    for cyrillic, latin in cyrillic_map.items():
        text = text.replace(cyrillic, latin)
    
    # Убираем все кроме букв, цифр и дефисов
    text = re.sub(r'[^a-z0-9\-]', '-', text)
    
    # Убираем множественные дефисы
    text = re.sub(r'-+', '-', text)
    
    # Убираем дефисы в начале и конце
    text = text.strip('-')
    
    # Обрезаем до максимальной длины
    if len(text) > max_length:
        text = text[:max_length].rstrip('-')
    
    return text or 'item'  # Возвращаем 'item' если строка пустая


def parse_date_filter(date_str: str) -> Optional[datetime]:
    """
    Парсинг даты из строки для фильтров
    
    Args:
        date_str: Строка с датой
        
    Returns:
        Объект datetime или None
    """
    if not date_str:
        return None
    
    formats = [
        '%Y-%m-%d',
        '%Y-%m-%d %H:%M:%S',
        '%Y-%m-%dT%H:%M:%S',
        '%Y-%m-%dT%H:%M:%SZ',
        '%d.%m.%Y',
        '%d/%m/%Y'
    ]
    
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    
    return None


def parse_price_range(price_str: str) -> tuple:
    """
    Парсинг диапазона цен из строки
    
    Args:
        price_str: Строка вида "100-500" или "100+" или "-500"
        
    Returns:
        Кортеж (min_price, max_price)
    """
    if not price_str:
        return None, None
    
    # Убираем пробелы и валютные символы
    cleaned = re.sub(r'[^\d\-+]', '', price_str)
    
    if '+' in cleaned:
        # Формат "100+"
        min_price = int(cleaned.replace('+', ''))
        return min_price, None
    elif cleaned.startswith('-'):
        # Формат "-500"
        max_price = int(cleaned[1:])
        return None, max_price
    elif '-' in cleaned and not cleaned.startswith('-'):
        # Формат "100-500"
        parts = cleaned.split('-')
        if len(parts) == 2:
            min_price = int(parts[0]) if parts[0] else None
            max_price = int(parts[1]) if parts[1] else None
            return min_price, max_price
    else:
        # Точная цена
        price = int(cleaned)
        return price, price
    
    return None, None


def format_price(price: float, currency: str = 'KZT') -> str:
    """
    Форматирование цены для отображения
    
    Args:
        price: Цена
        currency: Валюта
        
    Returns:
        Отформатированная строка цены
    """
    if not price:
        return "По договоренности"
    
    # Словарь символов валют
    currency_symbols = {
        'KZT': '₸',
        'USD': '$',
        'EUR': '€',
        'RUB': '₽'
    }
    
    symbol = currency_symbols.get(currency, currency)
    
    # Форматируем с разделителями тысяч
    if price >= 1000000:
        formatted = f"{price / 1000000:.1f}M"
    elif price >= 1000:
        formatted = f"{price / 1000:.0f}K"
    else:
        formatted = f"{price:.0f}"
    
    return f"{formatted} {symbol}"


def calculate_distance(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """
    Вычисление расстояния между двумя точками в километрах (формула гаверсинуса)
    
    Args:
        lat1, lng1: Координаты первой точки
        lat2, lng2: Координаты второй точки
        
    Returns:
        Расстояние в километрах
    """
    from math import radians, cos, sin, asin, sqrt
    
    # Радиус Земли в километрах
    R = 6371
    
    # Преобразование в радианы
    lat1, lng1, lat2, lng2 = map(radians, [lat1, lng1, lat2, lng2])
    
    # Формула гаверсинуса
    dlat = lat2 - lat1
    dlng = lng2 - lng1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlng/2)**2
    c = 2 * asin(sqrt(a))
    
    return R * c


def get_client_ip() -> str:
    """
    Получение IP адреса клиента с учетом прокси
    
    Returns:
        IP адрес клиента
    """
    # Проверяем заголовки прокси
    ip = request.headers.get('X-Forwarded-For')
    if ip:
        # Берем первый IP из списка
        ip = ip.split(',')[0].strip()
    else:
        ip = request.headers.get('X-Real-IP') or request.remote_addr
    
    return ip or '127.0.0.1'


def get_user_agent() -> str:
    """
    Получение User-Agent клиента
    
    Returns:
        User-Agent строка
    """
    return request.headers.get('User-Agent', 'Unknown')


def build_pagination_meta(query, page: int, per_page: int) -> Dict[str, Any]:
    """
    Создание метаданных пагинации
    
    Args:
        query: SQLAlchemy Query объект
        page: Номер страницы
        per_page: Элементов на странице
        
    Returns:
        Словарь с метаданными пагинации
    """
    total = query.count()
    items = query.offset((page - 1) * per_page).limit(per_page).all()
    
    total_pages = (total + per_page - 1) // per_page
    has_prev = page > 1
    has_next = page < total_pages
    
    return {
        'page': page,
        'per_page': per_page,
        'total': total,
        'total_pages': total_pages,
        'has_prev': has_prev,
        'has_next': has_next,
        'prev_page': page - 1 if has_prev else None,
        'next_page': page + 1 if has_next else None,
        'items': [item.to_dict() for item in items]
    }


def extract_filters_from_request() -> Dict[str, Any]:
    """
    Извлечение фильтров из параметров запроса
    
    Returns:
        Словарь с фильтрами
    """
    filters = {}
    
    # Стандартные фильтры
    for param in ['brand_id', 'model_id', 'city_id', 'body_type_id', 'engine_type_id', 
                  'transmission_id', 'drive_type_id', 'color_id', 'year_from', 'year_to',
                  'price_from', 'price_to', 'mileage_from', 'mileage_to']:
        value = request.args.get(param)
        if value:
            try:
                filters[param] = int(value)
            except ValueError:
                continue
    
    # Строковые фильтры
    for param in ['condition', 'currency', 'status', 'sort_by', 'order']:
        value = request.args.get(param)
        if value:
            filters[param] = value
    
    # Булевы фильтры
    for param in ['is_featured', 'is_urgent', 'customs_cleared', 'exchange_possible']:
        value = request.args.get(param)
        if value and value.lower() in ['true', '1', 'yes']:
            filters[param] = True
        elif value and value.lower() in ['false', '0', 'no']:
            filters[param] = False
    
    # Поисковый запрос
    query = request.args.get('q', '').strip()
    if query:
        filters['search_query'] = query
    
    # Геолокация
    lat = request.args.get('lat')
    lng = request.args.get('lng')
    radius = request.args.get('radius', '50')
    
    if lat and lng:
        try:
            filters['location'] = {
                'lat': float(lat),
                'lng': float(lng),
                'radius': int(radius)
            }
        except ValueError:
            pass
    
    return filters


def build_error_response(message: str, status_code: int = 400, 
                        errors: Dict = None) -> tuple:
    """
    Создание стандартизированного ответа об ошибке
    
    Args:
        message: Сообщение об ошибке
        status_code: HTTP статус код
        errors: Детали ошибок
        
    Returns:
        Кортеж (response_dict, status_code)
    """
    response = {
        'success': False,
        'message': message
    }
    
    if errors:
        response['errors'] = errors
    
    return response, status_code


def mask_sensitive_data(data: Dict, sensitive_fields: List[str] = None) -> Dict:
    """
    Маскирование чувствительных данных
    
    Args:
        data: Словарь с данными
        sensitive_fields: Список чувствительных полей
        
    Returns:
        Словарь с замаскированными данными
    """
    if not sensitive_fields:
        sensitive_fields = ['password', 'password_hash', 'token', 'secret', 'key']
    
    masked_data = data.copy()
    
    for field in sensitive_fields:
        if field in masked_data:
            masked_data[field] = '*' * 8
    
    return masked_data


def convert_to_kzt(amount: float, currency: str, exchange_rates: Dict = None) -> float:
    """
    Конвертация суммы в тенге
    
    Args:
        amount: Сумма
        currency: Валюта
        exchange_rates: Курсы валют
        
    Returns:
        Сумма в тенге
    """
    if currency == 'KZT':
        return amount
    
    if not exchange_rates:
        # Базовые курсы (в продакшене должны браться из базы данных)
        exchange_rates = {
            'USD': 480,
            'EUR': 520,
            'RUB': 5.2
        }
    
    rate = exchange_rates.get(currency, 1)
    return amount * rate


def generate_listing_number() -> str:
    """
    Генерация уникального номера объявления
    
    Returns:
        Номер объявления
    """
    import time
    timestamp = int(time.time())
    random_part = secrets.randbelow(1000)
    return f"KZ{timestamp}{random_part:03d}"


def validate_vin_number(vin: str) -> bool:
    """
    Базовая валидация VIN номера
    
    Args:
        vin: VIN номер
        
    Returns:
        True если VIN корректный
    """
    if not vin or len(vin) != 17:
        return False
    
    # VIN должен содержать только буквы и цифры (кроме I, O, Q)
    allowed_chars = set(string.ascii_uppercase + string.digits) - {'I', 'O', 'Q'}
    
    return all(c in allowed_chars for c in vin.upper())


def calculate_listing_score(listing_data: Dict) -> int:
    """
    Вычисление рейтинга объявления для сортировки
    
    Args:
        listing_data: Данные объявления
        
    Returns:
        Рейтинг объявления (0-100)
    """
    score = 50  # Базовый рейтинг
    
    # Бонусы за заполненность
    if listing_data.get('description'):
        score += 10
    
    if listing_data.get('images_count', 0) >= 3:
        score += 15
    elif listing_data.get('images_count', 0) >= 1:
        score += 5
    
    # Бонусы за верификацию
    if listing_data.get('user_verified'):
        score += 10
    
    # Бонусы за платные услуги
    if listing_data.get('is_featured'):
        score += 20
    
    if listing_data.get('is_urgent'):
        score += 10
    
    # Штрафы
    days_old = listing_data.get('days_since_published', 0)
    if days_old > 30:
        score -= 10
    elif days_old > 60:
        score -= 20
    
    return max(0, min(100, score))


def format_relative_time(dt: datetime) -> str:
    """
    Форматирование времени в относительном формате
    
    Args:
        dt: Дата и время
        
    Returns:
        Строка вида "2 дня назад"
    """
    if not dt:
        return ""
    
    now = datetime.utcnow()
    diff = now - dt
    
    if diff.days > 0:
        if diff.days == 1:
            return "вчера"
        elif diff.days < 7:
            return f"{diff.days} дня назад"
        elif diff.days < 30:
            weeks = diff.days // 7
            return f"{weeks} недель назад"
        else:
            months = diff.days // 30
            return f"{months} месяцев назад"
    
    elif diff.seconds > 3600:
        hours = diff.seconds // 3600
        return f"{hours} часов назад"
    
    elif diff.seconds > 60:
        minutes = diff.seconds // 60
        return f"{minutes} минут назад"
    
    else:
        return "только что"


def generate_sitemap_url(endpoint: str, **values) -> str:
    """
    Генерация URL для sitemap
    
    Args:
        endpoint: Имя endpoint'а
        **values: Параметры URL
        
    Returns:
        Полный URL
    """
    from flask import current_app
    
    with current_app.app_context():
        return url_for(endpoint, _external=True, **values)


def sanitize_html(text: str) -> str:
    """
    Очистка HTML от потенциально опасных тегов
    
    Args:
        text: Исходный HTML текст
        
    Returns:
        Очищенный текст
    """
    import re
    
    if not text:
        return ""
    
    # Убираем скрипты и стили
    text = re.sub(r'<script.*?</script>', '', text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<style.*?</style>', '', text, flags=re.DOTALL | re.IGNORECASE)
    
    # Убираем потенциально опасные атрибуты
    text = re.sub(r'on\w+="[^"]*"', '', text, flags=re.IGNORECASE)
    text = re.sub(r'javascript:', '', text, flags=re.IGNORECASE)
    
    return text


def create_thumbnail_filename(original_filename: str, size: str = 'thumb') -> str:
    """
    Создание имени файла для миниатюры
    
    Args:
        original_filename: Оригинальное имя файла
        size: Размер миниатюры
        
    Returns:
        Имя файла миниатюры
    """
    if not original_filename:
        return ""
    
    name, ext = os.path.splitext(original_filename)
    return f"{name}_{size}{ext}"


def is_mobile_user_agent(user_agent: str = None) -> bool:
    """
    Проверка мобильного User-Agent
    
    Args:
        user_agent: User-Agent строка
        
    Returns:
        True если мобильное устройство
    """
    if not user_agent:
        user_agent = get_user_agent()
    
    mobile_indicators = [
        'Mobile', 'Android', 'iPhone', 'iPad', 'Windows Phone',
        'BlackBerry', 'Opera Mini', 'IEMobile'
    ]
    
    return any(indicator in user_agent for indicator in mobile_indicators)