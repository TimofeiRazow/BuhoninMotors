# scripts/seed_data.py
"""
Скрипт для заполнения базы данных базовыми справочными данными
"""

from app.extensions import db
from app.models import *


def seed_countries():
    """Заполнение стран"""
    countries_data = [
        ('KZ', 'Казахстан', '+7'),
        ('RU', 'Россия', '+7'),
        ('BY', 'Беларусь', '+375'),
        ('UZ', 'Узбекистан', '+998'),
        ('KG', 'Кыргызстан', '+996'),
        ('TJ', 'Таджикистан', '+992'),
        ('TM', 'Туркменистан', '+993'),
        ('AM', 'Армения', '+374'),
        ('AZ', 'Азербайджан', '+994'),
        ('GE', 'Грузия', '+995')
    ]
    
    for code, name, phone in countries_data:
        country, created = get_or_create(
            Country,
            country_code=code,
            defaults={
                'country_name': name,
                'phone_code': phone
            }
        )
        if created:
            print(f"Создана страна: {name}")


def seed_currencies():
    """Заполнение валют"""
    currencies_data = [
        ('KZT', 'Казахстанский тенге', '₸', True, 1),
        ('USD', 'Доллар США', '$', False, 480),
        ('EUR', 'Евро', '€', False, 520),
        ('RUB', 'Российский рубль', '₽', False, 5.2),
        ('CNY', 'Китайский юань', '¥', False, 65)
    ]
    
    for code, name, symbol, is_base, rate in currencies_data:
        currency, created = get_or_create(
            Currency,
            currency_code=code,
            defaults={
                'currency_name': name,
                'symbol': symbol,
                'is_base_currency': is_base,
                'exchange_rate_to_kzt': rate
            }
        )
        if created:
            print(f"Создана валюта: {name}")


def seed_entity_types():
    """Заполнение типов сущностей"""
    types_data = [
        ('car_listing', 'Объявление о продаже автомобиля'),
        ('parts_listing', 'Объявление о продаже запчастей'),
        ('service_listing', 'Объявление об услугах'),
        ('commercial_listing', 'Коммерческий транспорт'),
        ('moto_listing', 'Мотоциклы и мототехника'),
        ('user', 'Пользователь'),
        ('conversation', 'Диалог'),
        ('message', 'Сообщение'),
        ('ticket', 'Тикет поддержки'),
        ('review', 'Отзыв')
    ]
    
    for code, name in types_data:
        entity_type, created = get_or_create(
            EntityType,
            type_code=code,
            defaults={'type_name': name}
        )
        if created:
            print(f"Создан тип сущности: {name}")


def seed_status_groups():
    """Заполнение групп статусов"""
    groups_data = [
        ('listing_status', 'Статусы объявлений', 'Статусы для объявлений'),
        ('user_status', 'Статусы пользователей', 'Статусы для пользователей'),
        ('payment_status', 'Статусы платежей', 'Статусы для платежных операций'),
        ('ticket_status', 'Статусы тикетов', 'Статусы для тикетов поддержки'),
        ('moderation_status', 'Статусы модерации', 'Статусы модерации контента'),
        ('notification_status', 'Статусы уведомлений', 'Статусы уведомлений'),
        ('conversation_status', 'Статусы диалогов', 'Статусы диалогов')
    ]
    
    for code, name, desc in groups_data:
        group, created = get_or_create(
            StatusGroup,
            group_code=code,
            defaults={
                'group_name': name,
                'description': desc
            }
        )
        if created:
            print(f"Создана группа статусов: {name}")


def seed_statuses():
    """Заполнение статусов"""
    statuses_data = [
        # Статусы объявлений
        ('listing_status', 'draft', 'Черновик', '#6b7280', False, 1),
        ('listing_status', 'moderation', 'На модерации', '#f59e0b', False, 2),
        ('listing_status', 'active', 'Активно', '#10b981', False, 3),
        ('listing_status', 'sold', 'Продано', '#3b82f6', True, 4),
        ('listing_status', 'archived', 'В архиве', '#6b7280', True, 5),
        ('listing_status', 'rejected', 'Отклонено', '#ef4444', True, 6),
        ('listing_status', 'expired', 'Истек срок', '#f59e0b', False, 7),
        
        # Статусы пользователей
        ('user_status', 'active', 'Активный', '#10b981', False, 1),
        ('user_status', 'blocked', 'Заблокирован', '#ef4444', True, 2),
        ('user_status', 'suspended', 'Приостановлен', '#f59e0b', False, 3),
        ('user_status', 'pending_verification', 'Ожидает верификации', '#f59e0b', False, 4),
        
        # Статусы платежей
        ('payment_status', 'pending', 'Ожидает оплаты', '#f59e0b', False, 1),
        ('payment_status', 'processing', 'Обрабатывается', '#3b82f6', False, 2),
        ('payment_status', 'completed', 'Завершен', '#10b981', True, 3),
        ('payment_status', 'failed', 'Ошибка', '#ef4444', True, 4),
        ('payment_status', 'cancelled', 'Отменен', '#6b7280', True, 5),
        ('payment_status', 'refunded', 'Возврат', '#8b5cf6', True, 6),
    ]
    
    for group_code, status_code, name, color, is_final, sort_order in statuses_data:
        group = StatusGroup.query.filter_by(group_code=group_code).first()
        if group:
            status, created = get_or_create(
                Status,
                group_id=group.group_id,
                status_code=status_code,
                defaults={
                    'status_name': name,
                    'status_color': color,
                    'is_final': is_final,
                    'sort_order': sort_order
                }
            )
            if created:
                print(f"Создан статус: {name}")


def seed_category_trees():
    """Заполнение деревьев категорий"""
    trees_data = [
        ('auto_categories', 'Категории автомобилей', 'Категории для легковых автомобилей'),
        ('parts_categories', 'Категории запчастей', 'Категории для автозапчастей'),
        ('service_categories', 'Категории услуг', 'Категории автомобильных услуг'),
        ('commercial_categories', 'Коммерческий транспорт', 'Категории коммерческого транспорта'),
        ('moto_categories', 'Мотоциклы и мототехника', 'Категории мототехники'),
        ('support_categories', 'Категории поддержки', 'Категории для службы поддержки')
    ]
    
    for code, name, desc in trees_data:
        tree, created = get_or_create(
            CategoryTree,
            tree_code=code,
            defaults={
                'tree_name': name,
                'description': desc
            }
        )
        if created:
            print(f"Создано дерево категорий: {name}")


def seed_car_body_types():
    """Заполнение типов кузова"""
    body_types = [
        ('Седан', 1), ('Хэтчбек', 2), ('Универсал', 3), ('Лифтбек', 4),
        ('Купе', 5), ('Кабриолет', 6), ('Родстер', 7), ('Тарга', 8),
        ('Лимузин', 9), ('Внедорожник', 10), ('Кроссовер', 11), 
        ('Пикап', 12), ('Фургон', 13), ('Минивэн', 14), ('Компактвэн', 15)
    ]
    
    for name, order in body_types:
        body_type, created = get_or_create(
            CarBodyType,
            body_type_name=name,
            defaults={'sort_order': order}
        )
        if created:
            print(f"Создан тип кузова: {name}")


def seed_car_engine_types():
    """Заполнение типов двигателей"""
    engine_types = [
        ('Бензин', 1), ('Дизель', 2), ('Гибрид', 3), 
        ('Электро', 4), ('Газ', 5), ('Газ/Бензин', 6)
    ]
    
    for name, order in engine_types:
        engine_type, created = get_or_create(
            CarEngineType,
            engine_type_name=name,
            defaults={'sort_order': order}
        )
        if created:
            print(f"Создан тип двигателя: {name}")


def seed_car_transmission_types():
    """Заполнение типов трансмиссии"""
    transmission_types = [
        ('Механика', 1), ('Автомат', 2), ('Робот', 3), ('Вариатор', 4)
    ]
    
    for name, order in transmission_types:
        transmission, created = get_or_create(
            CarTransmissionType,
            transmission_name=name,
            defaults={'sort_order': order}
        )
        if created:
            print(f"Создан тип трансмиссии: {name}")


def seed_car_drive_types():
    """Заполнение типов привода"""
    drive_types = [
        ('Передний', 1), ('Задний', 2), ('Полный', 3)
    ]
    
    for name, order in drive_types:
        drive_type, created = get_or_create(
            CarDriveType,
            drive_type_name=name,
            defaults={'sort_order': order}
        )
        if created:
            print(f"Создан тип привода: {name}")


def seed_car_colors():
    """Заполнение цветов автомобилей"""
    colors_data = [
        ('Белый', '#FFFFFF', 1), ('Черный', '#000000', 2), 
        ('Серый', '#808080', 3), ('Серебристый', '#C0C0C0', 4),
        ('Красный', '#FF0000', 5), ('Синий', '#0000FF', 6), 
        ('Зеленый', '#008000', 7), ('Желтый', '#FFFF00', 8),
        ('Оранжевый', '#FFA500', 9), ('Коричневый', '#8B4513', 10), 
        ('Бежевый', '#F5F5DC', 11), ('Золотистый', '#FFD700', 12)
    ]
    
    for name, hex_color, order in colors_data:
        color, created = get_or_create(
            CarColor,
            color_name=name,
            defaults={
                'color_hex': hex_color,
                'sort_order': order
            }
        )
        if created:
            print(f"Создан цвет: {name}")


def seed_car_brands():
    """Заполнение популярных марок автомобилей"""
    brands_data = [
        ('Toyota', 'toyota', 'Япония', 1),
        ('Volkswagen', 'volkswagen', 'Германия', 2),
        ('Hyundai', 'hyundai', 'Южная Корея', 3),
        ('Kia', 'kia', 'Южная Корея', 4),
        ('Nissan', 'nissan', 'Япония', 5),
        ('Honda', 'honda', 'Япония', 6),
        ('Chevrolet', 'chevrolet', 'США', 7),
        ('Mitsubishi', 'mitsubishi', 'Япония', 8),
        ('Mazda', 'mazda', 'Япония', 9),
        ('Ford', 'ford', 'США', 10),
        ('Daewoo', 'daewoo', 'Южная Корея', 11),
        ('Opel', 'opel', 'Германия', 12),
        ('Audi', 'audi', 'Германия', 13),
        ('BMW', 'bmw', 'Германия', 14),
        ('Mercedes-Benz', 'mercedes-benz', 'Германия', 15),
        ('Lexus', 'lexus', 'Япония', 16),
        ('Subaru', 'subaru', 'Япония', 17),
        ('Suzuki', 'suzuki', 'Япония', 18),
        ('Renault', 'renault', 'Франция', 19),
        ('Peugeot', 'peugeot', 'Франция', 20)
    ]
    
    for name, slug, country, order in brands_data:
        brand, created = get_or_create(
            CarBrand,
            brand_name=name,
            defaults={
                'brand_slug': slug,
                'country_origin': country,
                'sort_order': order
            }
        )
        if created:
            print(f"Создана марка: {name}")


def seed_kazakhstan_regions():
    """Заполнение регионов Казахстана"""
    kz = Country.query.filter_by(country_code='KZ').first()
    if not kz:
        print("Сначала создайте страну Казахстан")
        return
    
    regions_data = [
        ('Алматинская область', 'ALM', 1),
        ('Акмолинская область', 'AKM', 2),
        ('Актюбинская область', 'AKT', 3),
        ('Атырауская область', 'ATY', 4),
        ('Восточно-Казахстанская область', 'VKO', 5),
        ('Жамбылская область', 'ZHA', 6),
        ('Западно-Казахстанская область', 'ZKO', 7),
        ('Карагандинская область', 'KAR', 8),
        ('Костанайская область', 'KOS', 9),
        ('Кызылординская область', 'KYZ', 10),
        ('Мангистауская область', 'MAN', 11),
        ('Павлодарская область', 'PAV', 12),
        ('Северо-Казахстанская область', 'SKO', 13),
        ('Туркестанская область', 'TUR', 14),
        ('город Алматы', 'ALA', 15),
        ('город Астана', 'AST', 16),
        ('город Шымкент', 'SHY', 17)
    ]
    
    for name, code, order in regions_data:
        region, created = get_or_create(
            Region,
            region_name=name,
            country_id=kz.country_id,
            defaults={
                'region_code': code,
                'sort_order': order
            }
        )
        if created:
            print(f"Создан регион: {name}")


def seed_major_cities():
    """Заполнение крупных городов Казахстана"""
    cities_data = [
        # Алматы
        ('Алматы', 'ALA', 43.2220, 76.8512, 1900000, 1),
        
        # Астана (Нур-Султан)
        ('Астана', 'AST', 51.1694, 71.4491, 1200000, 2),
        ('Нур-Султан', 'AST', 51.1694, 71.4491, 1200000, 3),
        
        # Шымкент
        ('Шымкент', 'SHY', 42.3417, 69.5901, 1000000, 4),
        
        # Другие крупные города
        ('Караганда', 'KAR', 49.8047, 73.1094, 500000, 5),
        ('Актобе', 'AKT', 50.2839, 57.1670, 400000, 6),
        ('Тараз', 'ZHA', 42.9000, 71.3667, 350000, 7),
        ('Павлодар', 'PAV', 52.2873, 76.9674, 350000, 8),
        ('Усть-Каменогорск', 'VKO', 49.9825, 82.6094, 300000, 9),
        ('Семей', 'VKO', 50.4111, 80.2275, 300000, 10),
        ('Атырау', 'ATY', 47.1164, 51.8815, 250000, 11),
        ('Костанай', 'KOS', 53.2075, 63.6367, 250000, 12),
        ('Кызылорда', 'KYZ', 44.8479, 65.5093, 200000, 13),
        ('Уральск', 'ZKO', 51.2333, 51.3833, 200000, 14),
        ('Актау', 'MAN', 43.6481, 51.1560, 180000, 15)
    ]
    
    for city_name, region_code, lat, lng, population, order in cities_data:
        region = Region.query.filter_by(region_code=region_code).first()
        if region:
            city, created = get_or_create(
                City,
                city_name=city_name,
                region_id=region.region_id,
                defaults={
                    'latitude': lat,
                    'longitude': lng,
                    'population': population,
                    'sort_order': order
                }
            )
            if created:
                print(f"Создан город: {city_name}")


def seed_car_attribute_groups():
    """Заполнение групп атрибутов автомобилей"""
    groups_data = [
        ('basic', 'Основные характеристики', 1),
        ('engine', 'Двигатель', 2),
        ('transmission', 'Трансмиссия', 3),
        ('exterior', 'Экстерьер', 4),
        ('interior', 'Интерьер', 5),
        ('safety', 'Безопасность', 6),
        ('comfort', 'Комфорт', 7),
        ('multimedia', 'Мультимедиа', 8)
    ]
    
    for code, name, order in groups_data:
        group, created = get_or_create(
            CarAttributeGroup,
            group_code=code,
            defaults={
                'group_name': name,
                'sort_order': order
            }
        )
        if created:
            print(f"Создана группа атрибутов: {name}")


def seed_car_attributes():
    """Заполнение основных атрибутов автомобилей"""
    # Получаем группы
    basic_group = CarAttributeGroup.query.filter_by(group_code='basic').first()
    engine_group = CarAttributeGroup.query.filter_by(group_code='engine').first()
    transmission_group = CarAttributeGroup.query.filter_by(group_code='transmission').first()
    
    if not all([basic_group, engine_group, transmission_group]):
        print("Сначала создайте группы атрибутов")
        return
    
    attributes_data = [
        # Основные характеристики
        (basic_group.group_id, 'year', 'Год выпуска', 'number', True, True, True, 1),
        (basic_group.group_id, 'mileage', 'Пробег (км)', 'number', True, True, True, 2),
        (basic_group.group_id, 'condition', 'Состояние', 'string', True, True, True, 3),
        (basic_group.group_id, 'brand_id', 'Марка', 'reference', True, True, True, 4),
        (basic_group.group_id, 'model_id', 'Модель', 'reference', True, True, True, 5),
        (basic_group.group_id, 'generation_id', 'Поколение', 'reference', False, True, True, 6),
        (basic_group.group_id, 'body_type_id', 'Тип кузова', 'reference', True, True, True, 7),
        (basic_group.group_id, 'color_id', 'Цвет', 'reference', False, True, True, 8),
        (basic_group.group_id, 'vin_number', 'VIN номер', 'string', False, False, False, 9),
        (basic_group.group_id, 'customs_cleared', 'Растаможен', 'boolean', False, True, True, 10),
        
        # Двигатель
        (engine_group.group_id, 'engine_volume', 'Объем двигателя (л)', 'number', False, True, True, 1),
        (engine_group.group_id, 'engine_type_id', 'Тип двигателя', 'reference', False, True, True, 2),
        (engine_group.group_id, 'fuel_consumption', 'Расход топлива', 'number', False, False, False, 3),
        (engine_group.group_id, 'power_hp', 'Мощность (л.с.)', 'number', False, True, True, 4),
        
        # Трансмиссия
        (transmission_group.group_id, 'transmission_id', 'Коробка передач', 'reference', False, True, True, 1),
        (transmission_group.group_id, 'drive_type_id', 'Привод', 'reference', False, True, True, 2),
    ]
    
    for group_id, code, name, attr_type, required, searchable, filterable, order in attributes_data:
        attribute, created = get_or_create(
            CarAttribute,
            attribute_code=code,
            defaults={
                'group_id': group_id,
                'attribute_name': name,
                'attribute_type': attr_type,
                'is_required': required,
                'is_searchable': searchable,
                'is_filterable': filterable,
                'sort_order': order
            }
        )
        if created:
            print(f"Создан атрибут: {name}")


def seed_initial_data():
    """Заполнение всех базовых данных"""
    print("Начинаем заполнение базовых данных...")
    
    # Порядок важен из-за внешних ключей
    seed_countries()
    seed_currencies()
    seed_entity_types()
    seed_status_groups()
    seed_statuses()
    seed_category_trees()
    
    # Автомобильные справочники
    seed_car_body_types()
    seed_car_engine_types()
    seed_car_transmission_types()
    seed_car_drive_types()
    seed_car_colors()
    seed_car_brands()
    
    # География
    seed_kazakhstan_regions()
    seed_major_cities()
    
    # Атрибуты автомобилей
    seed_car_attribute_groups()
    seed_car_attributes()
    
    # Сохраняем все изменения
    try:
        db.session.commit()
        print("\nВсе базовые данные успешно загружены!")
    except Exception as e:
        db.session.rollback()
        print(f"\nОшибка при сохранении данных: {e}")
        raise


if __name__ == '__main__':
    from app import create_app
    
    app = create_app()
    with app.app_context():
        seed_initial_data()