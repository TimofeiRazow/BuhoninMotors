
# app/blueprints/locations/services.py
from sqlalchemy import func, and_
from app.models.location import Country, Region, City
from app.utils.exceptions import NotFoundError
from app.utils.pagination import paginate_query
from app.extensions import cache


class LocationService:
    """Сервис для работы с географическими данными"""
    
    @staticmethod
    @cache.memoize(timeout=3600)
    def get_countries():
        """Получение всех стран"""
        return Country.query.filter(Country.is_active == True).order_by(Country.country_name).all()
    
    @staticmethod
    def get_country(country_id):
        """
        Получение страны по ID
        
        Args:
            country_id: ID страны
            
        Returns:
            Страна
            
        Raises:
            NotFoundError: Если страна не найдена
        """
        country = Country.query.filter(
            Country.country_id == country_id,
            Country.is_active == True
        ).first()
        
        if not country:
            raise NotFoundError(f"Country {country_id} not found", "country")
        
        return country
    
    @staticmethod
    @cache.memoize(timeout=3600)
    def get_regions(country_id=None):
        """
        Получение регионов
        
        Args:
            country_id: ID страны (опционально)
            
        Returns:
            Список регионов
        """
        query = Region.query.filter(Region.is_active == True)
        
        if country_id:
            query = query.filter(Region.country_id == country_id)
        
        return query.order_by(Region.sort_order, Region.region_name).all()
    
    @staticmethod
    def get_region(region_id):
        """
        Получение региона по ID
        
        Args:
            region_id: ID региона
            
        Returns:
            Регион
            
        Raises:
            NotFoundError: Если регион не найден
        """
        region = Region.query.filter(
            Region.region_id == region_id,
            Region.is_active == True
        ).first()
        
        if not region:
            raise NotFoundError(f"Region {region_id} not found", "region")
        
        return region
    
    @staticmethod
    @cache.memoize(timeout=1800)  # 30 минут
    def get_cities(region_id=None, country_id=None, limit=None):
        """
        Получение городов
        
        Args:
            region_id: ID региона (опционально)
            country_id: ID страны (опционально)
            limit: Лимит результатов
            
        Returns:
            Список городов
        """
        query = City.query.filter(City.is_active == True)
        
        if region_id:
            query = query.filter(City.region_id == region_id)
        elif country_id:
            query = query.join(Region).filter(Region.country_id == country_id)
        
        query = query.order_by(City.sort_order, City.city_name)
        
        if limit:
            query = query.limit(limit)
        
        return query.all()
    
    @staticmethod
    def get_city(city_id):
        """
        Получение города по ID
        
        Args:
            city_id: ID города
            
        Returns:
            Город
            
        Raises:
            NotFoundError: Если город не найден
        """
        city = City.query.filter(
            City.city_id == city_id,
            City.is_active == True
        ).first()
        
        if not city:
            raise NotFoundError(f"City {city_id} not found", "city")
        
        return city
    
    @staticmethod
    @cache.memoize(timeout=1800)
    def get_popular_cities(limit=20):
        """
        Получение популярных городов (по населению)
        
        Args:
            limit: Количество городов
            
        Returns:
            Список популярных городов
        """
        return City.get_popular_cities(limit)
    
    @staticmethod
    def search_cities(query_text, country_id=None, region_id=None, limit=10):
        """
        Поиск городов по названию
        
        Args:
            query_text: Поисковый запрос
            country_id: ID страны для фильтрации
            region_id: ID региона для фильтрации
            limit: Лимит результатов
            
        Returns:
            Результаты поиска
        """
        if len(query_text) < 2:
            return []
        
        query = City.query.filter(
            City.city_name.ilike(f'%{query_text}%'),
            City.is_active == True
        )
        
        if region_id:
            query = query.filter(City.region_id == region_id)
        elif country_id:
            query = query.join(Region).filter(Region.country_id == country_id)
        
        return query.order_by(
            City.sort_order,
            City.population.desc().nullslast(),
            City.city_name
        ).limit(limit).all()
    
    @staticmethod
    def search_locations(query_text, country_id=None, region_id=None, limit=10):
        """
        Универсальный поиск по всем локациям
        
        Args:
            query_text: Поисковый запрос
            country_id: ID страны для фильтрации
            region_id: ID региона для фильтрации
            limit: Лимит результатов
            
        Returns:
            Результаты поиска по типам
        """
        results = {
            'countries': [],
            'regions': [],
            'cities': []
        }
        
        if len(query_text) < 2:
            return results
        
        # Поиск стран
        if not country_id and not region_id:
            countries = Country.query.filter(
                Country.country_name.ilike(f'%{query_text}%'),
                Country.is_active == True
            ).order_by(Country.country_name).limit(5).all()
            
            results['countries'] = [country.to_dict() for country in countries]
        
        # Поиск регионов
        if not region_id:
            regions_query = Region.query.filter(
                Region.region_name.ilike(f'%{query_text}%'),
                Region.is_active == True
            )
            
            if country_id:
                regions_query = regions_query.filter(Region.country_id == country_id)
            
            regions = regions_query.order_by(Region.sort_order, Region.region_name).limit(5).all()
            results['regions'] = [region.to_dict() for region in regions]
        
        # Поиск городов
        cities = LocationService.search_cities(query_text, country_id, region_id, limit)
        results['cities'] = [city.to_dict() for city in cities]
        
        return results
    
    @staticmethod
    def find_nearby_cities(latitude, longitude, radius_km=50, limit=20):
        """
        Поиск городов поблизости от координат
        
        Args:
            latitude: Широта
            longitude: Долгота
            radius_km: Радиус поиска в километрах
            limit: Лимит результатов
            
        Returns:
            Список городов с расстояниями
        """
        from sqlalchemy import text
        
        # Используем PostgreSQL функции для вычисления расстояния
        distance_query = text("""
            earth_distance(
                ll_to_earth(:search_lat, :search_lng),
                ll_to_earth(latitude, longitude)
            ) / 1000 as distance_km
        """)
        
        cities = City.query.add_column(distance_query).filter(
            City.latitude.isnot(None),
            City.longitude.isnot(None),
            City.is_active == True,
            text("""
                earth_box(ll_to_earth(:search_lat, :search_lng), :radius_m) @>
                ll_to_earth(latitude, longitude)
            """)
        ).params(
            search_lat=latitude,
            search_lng=longitude,
            radius_m=radius_km * 1000
        ).order_by(
            text("distance_km")
        ).limit(limit).all()
        
        # Форматируем результаты
        results = []
        for city, distance in cities:
            city_dict = city.to_dict()
            city_dict['distance_km'] = round(float(distance), 2)
            results.append(city_dict)
        
        return results
    
    @staticmethod
    def get_cities_by_region(region_id):
        """
        Получение городов региона
        
        Args:
            region_id: ID региона
            
        Returns:
            Список городов региона
        """
        # Проверяем существование региона
        LocationService.get_region(region_id)
        
        return City.get_by_region(region_id)
    
    @staticmethod
    def get_location_hierarchy():
        """
        Получение полной иерархии местоположений
        
        Returns:
            Иерархическая структура стран, регионов и городов
        """
        countries = Country.query.filter(Country.is_active == True).order_by(Country.country_name).all()
        
        result = []
        for country in countries:
            country_dict = country.to_dict()
            country_dict['regions'] = []
            
            regions = Region.query.filter(
                Region.country_id == country.country_id,
                Region.is_active == True
            ).order_by(Region.sort_order, Region.region_name).all()
            
            for region in regions:
                region_dict = region.to_dict()
                region_dict['cities'] = []
                
                # Получаем только крупные города для иерархии
                cities = City.query.filter(
                    City.region_id == region.region_id,
                    City.is_active == True
                ).order_by(
                    City.sort_order,
                    City.population.desc().nullslast()
                ).limit(10).all()
                
                region_dict['cities'] = [city.to_dict() for city in cities]
                country_dict['regions'].append(region_dict)
            
            result.append(country_dict)
        
        return result
    
    @staticmethod
    @cache.memoize(timeout=3600)
    def get_location_stats():
        """
        Получение статистики по локациям
        
        Returns:
            Статистика количества стран, регионов, городов
        """
        stats = {
            'countries_count': Country.query.filter(Country.is_active == True).count(),
            'regions_count': Region.query.filter(Region.is_active == True).count(),
            'cities_count': City.query.filter(City.is_active == True).count()
        }
        
        # Статистика по Казахстану
        kz_country = Country.query.filter_by(country_code='KZ').first()
        if kz_country:
            stats['kz_regions_count'] = Region.query.filter(
                Region.country_id == kz_country.country_id,
                Region.is_active == True
            ).count()
            
            stats['kz_cities_count'] = City.query.join(Region).filter(
                Region.country_id == kz_country.country_id,
                City.is_active == True
            ).count()
        
        return stats