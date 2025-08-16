# app/blueprints/listings/services.py
from datetime import datetime, timedelta
from sqlalchemy import and_, or_, desc, asc, func
from sqlalchemy.orm import joinedload
from app.extensions import db
from app.models.listing import Listing, ListingDetails, ListingFeature
from app.models.car import CarBrand, CarModel
from app.models.location import City, Region
from app.models.base import get_status_by_code, EntityType
from app.utils.exceptions import (
    ListingNotFoundError, AuthorizationError, ValidationError,
    BusinessLogicError, MaxListingsReachedError
)
from app.utils.pagination import paginate_query


class ListingService:
    """Сервис для работы с объявлениями"""
    
    MAX_LISTINGS_PER_USER = {
        'regular': 5,
        'pro': 50,
        'dealer': 200,
        'admin': 999999
    }
    
    @staticmethod
    def create_listing(user_id, listing_data, car_data=None):
        """
        Создание нового объявления
        
        Args:
            user_id: ID пользователя
            listing_data: Данные объявления
            car_data: Данные автомобиля (для автомобильных объявлений)
            
        Returns:
            Созданное объявление
            
        Raises:
            MaxListingsReachedError: Если превышен лимит объявлений
            ValidationError: Если данные некорректны
        """
        from app.models.user import User
        
        # Получаем пользователя
        user = User.query.get(user_id)
        if not user:
            from app.utils.exceptions import UserNotFoundError
            raise UserNotFoundError()
        
        
        # Получаем тип объявления
        listing_type_code = 'car_listing' if car_data else 'service_listing'
        listing_type = EntityType.query.filter_by(type_code=listing_type_code).first()
        
        if not listing_type:
            raise ValidationError("Invalid listing type")
        
        # Получаем статус "на модерации"
        moderation_status = get_status_by_code('listing_status', 'moderation')
        
        # Создаем объявление
        listing = Listing(
            user_id=user_id,
            listing_type_id=listing_type.type_id,
            status_id=moderation_status.status_id,
            **listing_data
        )
        listing.save()
        
        # Создаем детали для автомобильного объявления
        if car_data:
            details = ListingDetails(
                listing_id=listing.listing_id,
                listing_type_id=listing_type.type_id
            )
            details.set_car_details(**car_data)
            
            # Добавляем особенности
            features = car_data.get('features', [])
            if features:
                ListingService._add_listing_features(listing.listing_id, features)
        
        # Отправляем на модерацию
        ListingService._submit_for_moderation(listing)
        
        return listing
    
    @staticmethod
    def _check_listings_limit(user):
        """Проверка лимита объявлений пользователя"""
        max_listings = ListingService.MAX_LISTINGS_PER_USER.get(user.user_type, 5)
        
        active_statuses = ['draft', 'moderation', 'active']
        current_count = Listing.query.join(Status).filter(
            Listing.user_id == user.user_id,
            Status.status_code.in_(active_statuses)
        ).count()
        
        if current_count >= max_listings:
            raise MaxListingsReachedError(max_listings)
    
    @staticmethod
    def _add_listing_features(listing_id, feature_ids):
        """Добавление особенностей к объявлению"""
        for feature_id in feature_ids:
            feature = ListingFeature(
                listing_id=listing_id,
                feature_id=feature_id
            )
            feature.save()
    
    @staticmethod
    def _submit_for_moderation(listing):
        """Отправка объявления на модерацию"""
        from app.models.moderation import ModerationQueue
        from app.models.base import get_status_by_code
        
        moderation_status = get_status_by_code('moderation_status', 'pending')
        
        moderation = ModerationQueue(
            entity_id=listing.entity_id,
            user_id=listing.user_id,
            status_id=moderation_status.status_id
        )
        moderation.save()
    
    @staticmethod
    def get_listing(listing_id, user_id=None, include_details=True):
        """
        Получение объявления по ID
        
        Args:
            listing_id: ID объявления
            user_id: ID пользователя (для проверки избранного)
            include_details: Включать ли детальную информацию
            
        Returns:
            Объявление
            
        Raises:
            ListingNotFoundError: Если объявление не найдено
        """
        query = Listing.query.options(
            joinedload(Listing.user),
            joinedload(Listing.city),
            joinedload(Listing.status)
        )
        
        listing = query.get(listing_id)
        
        if not listing:
            raise ListingNotFoundError(listing_id)
        
        # Увеличиваем счетчик просмотров
        listing.increment_view_count()
        
        return listing
    
    @staticmethod
    def update_listing(listing_id, user_id, update_data):
        """
        Обновление объявления
        
        Args:
            listing_id: ID объявления
            user_id: ID пользователя
            update_data: Данные для обновления
            
        Returns:
            Обновленное объявление
            
        Raises:
            ListingNotFoundError: Если объявление не найдено
            AuthorizationError: Если пользователь не владелец
        """
        listing = Listing.query.get(listing_id)
        
        if not listing:
            raise ListingNotFoundError(listing_id)
        
        # Проверяем права доступа
        if listing.user_id != user_id:
            from app.models.user import User
            user = User.query.get(user_id)
            if not user or user.user_type != 'admin':
                raise AuthorizationError("You can only edit your own listings")
        
        # Обновляем поля
        for field, value in update_data.items():
            if hasattr(listing, field):
                setattr(listing, field, value)
        
        listing.save()
        
        return listing
    
    @staticmethod
    def delete_listing(listing_id, user_id):
        """
        Удаление объявления
        
        Args:
            listing_id: ID объявления
            user_id: ID пользователя
            
        Returns:
            True если успешно удалено
            
        Raises:
            ListingNotFoundError: Если объявление не найдено
            AuthorizationError: Если пользователь не владелец
        """
        listing = Listing.query.get(listing_id)
        
        if not listing:
            raise ListingNotFoundError(listing_id)
        
        # Проверяем права доступа
        if listing.user_id != user_id:
            from app.models.user import User
            user = User.query.get(user_id)
            if not user or user.user_type != 'admin':
                raise AuthorizationError("You can only delete your own listings")
        
        # Мягкое удаление
        listing.soft_delete()
        
        return True
    
    @staticmethod
    def search_listings(search_params):
        """
        Поиск объявлений с фильтрацией
        
        Args:
            search_params: Параметры поиска
            
        Returns:
            Результаты поиска с пагинацией
        """
        # Базовый запрос только для активных объявлений
        query = Listing.get_active_listings().options(
            joinedload(Listing.city).joinedload(City.region),
            joinedload(Listing.currency),
            joinedload(Listing.status)
        )
        
        # Применяем фильтры
        query = ListingService._apply_filters(query, search_params)
        
        # Применяем сортировку
        query = ListingService._apply_sorting(query, search_params.get('sort_by', 'date_desc'))
        
        # Пагинация
        page = search_params.get('page', 1)
        per_page = search_params.get('per_page', 20)
        
        return paginate_query(query, page, per_page)
    
    @staticmethod
    def _apply_filters(query, params):
        """Применение фильтров к запросу"""
        
        # Текстовый поиск
        search_query = params.get('q')
        if search_query:
            query = Listing.search_by_text(search_query)
        
        # Фильтр по типу объявления
        listing_type = params.get('listing_type')
        if listing_type:
            query = query.join(EntityType).filter(
                EntityType.type_code == listing_type
            )
        
        # Географические фильтры
        city_id = params.get('city_id')
        if city_id:
            query = query.filter(Listing.city_id == city_id)
        
        region_id = params.get('region_id')
        if region_id:
            query = query.join(City).filter(City.region_id == region_id)
        
        # Геолокационный поиск
        latitude = params.get('latitude')
        longitude = params.get('longitude')
        radius = params.get('radius', 50)
        
        if latitude and longitude:
            query = Listing.search_by_location(latitude, longitude, radius)
        
        # Фильтры по цене
        price_from = params.get('price_from')
        price_to = params.get('price_to')
        
        if price_from is not None:
            query = query.filter(Listing.price >= price_from)
        
        if price_to is not None:
            query = query.filter(Listing.price <= price_to)
        
        # Булевы фильтры
        if params.get('is_featured'):
            query = query.filter(Listing.is_featured == True)
        
        if params.get('is_urgent'):
            query = query.filter(Listing.is_urgent == True)
        
        # Автомобильные фильтры (через JSONB)
        car_filters = ['brand_id', 'model_id', 'body_type_id', 'engine_type_id', 
                      'transmission_id', 'drive_type_id', 'color_id']
        
        for filter_name in car_filters:
            value = params.get(filter_name)
            if value:
                query = query.join(ListingDetails).filter(
                    ListingDetails.searchable_fields[filter_name].astext.cast(db.Integer) == value
                )
        
        # Фильтры по году
        year_from = params.get('year_from')
        year_to = params.get('year_to')
        
        if year_from:
            query = query.join(ListingDetails).filter(
                ListingDetails.searchable_fields['year'].astext.cast(db.Integer) >= year_from
            )
        
        if year_to:
            query = query.join(ListingDetails).filter(
                ListingDetails.searchable_fields['year'].astext.cast(db.Integer) <= year_to
            )
        
        # Фильтры по пробегу
        mileage_from = params.get('mileage_from')
        mileage_to = params.get('mileage_to')
        
        if mileage_from:
            query = query.join(ListingDetails).filter(
                ListingDetails.details['mileage'].astext.cast(db.Integer) >= mileage_from
            )
        
        if mileage_to:
            query = query.join(ListingDetails).filter(
                ListingDetails.details['mileage'].astext.cast(db.Integer) <= mileage_to
            )
        
        # Фильтр по состоянию
        condition = params.get('condition')
        if condition:
            query = query.join(ListingDetails).filter(
                ListingDetails.details['condition'].astext == condition
            )
        
        return query
    
    @staticmethod
    def _apply_sorting(query, sort_by):
        """Применение сортировки к запросу"""
        
        if sort_by == 'date_desc':
            return query.order_by(desc(Listing.published_date))
        
        elif sort_by == 'date_asc':
            return query.order_by(asc(Listing.published_date))
        
        elif sort_by == 'price_desc':
            return query.order_by(desc(Listing.price))
        
        elif sort_by == 'price_asc':
            return query.order_by(asc(Listing.price))
        
        elif sort_by == 'mileage_asc':
            return query.join(ListingDetails).order_by(
                asc(ListingDetails.details['mileage'].astext.cast(db.Integer))
            )
        
        elif sort_by == 'mileage_desc':
            return query.join(ListingDetails).order_by(
                desc(ListingDetails.details['mileage'].astext.cast(db.Integer))
            )
        
        elif sort_by == 'year_desc':
            return query.join(ListingDetails).order_by(
                desc(ListingDetails.searchable_fields['year'].astext.cast(db.Integer))
            )
        
        elif sort_by == 'year_asc':
            return query.join(ListingDetails).order_by(
                asc(ListingDetails.searchable_fields['year'].astext.cast(db.Integer))
            )
        
        else:  # relevance or default
            return query.order_by(
                desc(Listing.is_featured),
                desc(Listing.is_urgent),
                desc(Listing.published_date)
            )
    
    @staticmethod
    def toggle_favorite(listing_id, user_id):
        """
        Добавление/удаление объявления из избранного
        
        Args:
            listing_id: ID объявления
            user_id: ID пользователя
            
        Returns:
            Словарь с результатом операции
            
        Raises:
            ListingNotFoundError: Если объявление не найдено
        """
        listing = Listing.query.get(listing_id)
        
        if not listing:
            raise ListingNotFoundError(listing_id)
        
        is_favorited = listing.is_favorited_by(user_id)
        
        if is_favorited:
            listing.remove_from_favorites(user_id)
            action = 'removed'
        else:
            listing.add_to_favorites(user_id)
            action = 'added'
        
        return {
            'action': action,
            'is_favorited': not is_favorited,
            'favorite_count': listing.favorite_count
        }
    
    @staticmethod
    def get_user_favorites(user_id, page=1, per_page=20, sort_by='date_desc', 
                        include_expired=False, folder_name=None):
        """
        Получение избранных объявлений пользователя
        
        Args:
            user_id: ID пользователя
            page: Номер страницы
            per_page: Объявлений на странице
            sort_by: Сортировка
            include_expired: Включать ли истекшие объявления
            folder_name: Фильтр по папке
            
        Returns:
            Избранные объявления с пагинацией
        """
        from app.models.favorite import Favorite
        from app.models.base import get_status_by_code
        
        # Базовый запрос
        query = Listing.query.join(
            Favorite, Listing.entity_id == Favorite.entity_id
        ).filter(
            Favorite.user_id == user_id
        ).options(
            joinedload(Listing.city).joinedload(City.region),
            joinedload(Listing.currency),
            joinedload(Listing.status)
        )
        
        # Фильтр по папке
        if folder_name is not None:
            if folder_name == '':
                # Общая папка (без названия)
                query = query.filter(Favorite.folder_name.is_(None))
            else:
                query = query.filter(Favorite.folder_name == folder_name)
        
        # Фильтр по статусу объявлений
        if not include_expired:
            # Только активные объявления
            active_status = get_status_by_code('listing_status', 'active')
            if active_status:
                query = query.filter(
                    Listing.status_id == active_status.status_id,
                    or_(
                        Listing.expires_date.is_(None),
                        Listing.expires_date > datetime.utcnow()
                    )
                )
        
        # Применяем сортировку
        if sort_by == 'date_desc':
            query = query.order_by(desc(Favorite.added_date))
        elif sort_by == 'date_asc':
            query = query.order_by(asc(Favorite.added_date))
        elif sort_by == 'price_desc':
            query = query.order_by(desc(Listing.price))
        elif sort_by == 'price_asc':
            query = query.order_by(asc(Listing.price))
        elif sort_by == 'title_asc':
            query = query.order_by(asc(Listing.title))
        else:
            # По умолчанию сортируем по дате добавления в избранное (новые сначала)
            query = query.order_by(desc(Favorite.added_date))
        
        return paginate_query(query, page, per_page)

    @staticmethod
    def get_user_listings(user_id, status=None, page=1, per_page=20):
        """
        Получение объявлений пользователя
        
        Args:
            user_id: ID пользователя
            status: Фильтр по статусу
            page: Номер страницы
            per_page: Объявлений на странице
            
        Returns:
            Объявления пользователя с пагинацией
        """
        query = Listing.query.filter(
            Listing.user_id == user_id,
            Listing.is_active == True
        ).options(
            joinedload(Listing.status),
            joinedload(Listing.city)
        )
        
        if status:
            query = query.join(Status).filter(Status.status_code == status)
        
        query = query.order_by(desc(Listing.updated_date))
        
        return paginate_query(query, page, per_page)
    
    @staticmethod
    def perform_listing_action(listing_id, user_id, action):
        """
        Выполнение действия с объявлением
        
        Args:
            listing_id: ID объявления
            user_id: ID пользователя
            action: Действие
            
        Returns:
            Результат операции
            
        Raises:
            ListingNotFoundError: Если объявление не найдено
            AuthorizationError: Если пользователь не владелец
            BusinessLogicError: Если действие недопустимо
        """
        listing = Listing.query.get(listing_id)
        
        if not listing:
            raise ListingNotFoundError(listing_id)
        
        # Проверяем права доступа
        if listing.user_id != user_id:
            raise AuthorizationError("You can only manage your own listings")
        
        if action == 'activate':
            return ListingService._activate_listing(listing)
        
        elif action == 'deactivate':
            return ListingService._deactivate_listing(listing)
        
        elif action == 'archive':
            listing.archive()
            return {'status': 'archived', 'message': 'Listing archived successfully'}
        
        elif action == 'mark_sold':
            listing.mark_as_sold()
            return {'status': 'sold', 'message': 'Listing marked as sold'}
        
        elif action == 'renew':
            return ListingService._renew_listing(listing)
        
        else:
            raise ValidationError(f"Unknown action: {action}")
    
    @staticmethod
    def _activate_listing(listing):
        """Активация объявления"""
        if listing.status.status_code == 'active':
            raise BusinessLogicError("Listing is already active")
        
        listing.publish()
        return {'status': 'active', 'message': 'Listing activated successfully'}
    
    @staticmethod
    def _deactivate_listing(listing):
        """Деактивация объявления"""
        draft_status = get_status_by_code('listing_status', 'draft')
        listing.status_id = draft_status.status_id
        listing.save()
        
        return {'status': 'draft', 'message': 'Listing deactivated successfully'}
    
    @staticmethod
    def _renew_listing(listing):
        """Продление объявления"""
        if listing.is_expired():
            listing.publish(duration_days=30)
            return {'status': 'renewed', 'message': 'Listing renewed successfully'}
        else:
            raise BusinessLogicError("Listing is not expired")


