# app/utils/pagination.py
"""
Утилиты для пагинации результатов
"""

from typing import Dict, List, Any, Optional
from flask import request, url_for
from sqlalchemy.orm import Query


class Pagination:
    """Класс для работы с пагинацией"""
    
    def __init__(self, query: Query, page: int, per_page: int, 
                 error_out: bool = True, max_per_page: int = 100):
        """
        Инициализация пагинации
        
        Args:
            query: SQLAlchemy Query объект
            page: Номер страницы (начиная с 1)
            per_page: Количество элементов на странице
            error_out: Выбрасывать ошибку при некорректных параметрах
            max_per_page: Максимальное количество элементов на странице
        """
        self.query = query
        self.page = max(1, page) if page > 0 else 1
        self.per_page = min(max(1, per_page), max_per_page)
        self.error_out = error_out
        self.max_per_page = max_per_page
        
        # Вычисляем общее количество элементов
        self.total = self.query.count()
        
        # Вычисляем общее количество страниц
        self.total_pages = (self.total + self.per_page - 1) // self.per_page
        
        # Проверяем корректность номера страницы
        if self.error_out and self.page > self.total_pages and self.total_pages > 0:
            from app.utils.exceptions import NotFoundError
            raise NotFoundError("Page not found")
        
        # Вычисляем offset
        self.offset = (self.page - 1) * self.per_page
        
        # Получаем элементы для текущей страницы
        self._items = None
    
    @property
    def items(self) -> List:
        """Получение элементов текущей страницы"""
        if self._items is None:
            self._items = self.query.offset(self.offset).limit(self.per_page).all()
        return self._items
    
    @property
    def has_prev(self) -> bool:
        """Есть ли предыдущая страница"""
        return self.page > 1
    
    @property
    def has_next(self) -> bool:
        """Есть ли следующая страница"""
        return self.page < self.total_pages
    
    @property
    def prev_num(self) -> Optional[int]:
        """Номер предыдущей страницы"""
        return self.page - 1 if self.has_prev else None
    
    @property
    def next_num(self) -> Optional[int]:
        """Номер следующей страницы"""
        return self.page + 1 if self.has_next else None
    
    def iter_pages(self, left_edge: int = 2, left_current: int = 2,
                   right_current: int = 3, right_edge: int = 2) -> List[Optional[int]]:
        """
        Итератор номеров страниц для создания навигации
        
        Args:
            left_edge: Количество страниц слева от начала
            left_current: Количество страниц слева от текущей
            right_current: Количество страниц справа от текущей
            right_edge: Количество страниц справа от конца
            
        Returns:
            Список номеров страниц (None означает разрыв)
        """
        last = self.total_pages
        
        for num in range(1, last + 1):
            if (num <= left_edge or 
                (self.page - left_current - 1 < num < self.page + right_current) or 
                num > last - right_edge):
                yield num
    
    def get_page_args(self, page: int = None, per_page: int = None) -> Dict[str, Any]:
        """
        Получение аргументов для генерации URL страницы
        
        Args:
            page: Номер страницы
            per_page: Элементов на странице
            
        Returns:
            Словарь аргументов
        """
        args = dict(request.args)
        
        if page is not None:
            args['page'] = page
        
        if per_page is not None:
            args['per_page'] = per_page
        
        return args
    
    def get_page_url(self, page: int, per_page: int = None, endpoint: str = None) -> str:
        """
        Получение URL для конкретной страницы
        
        Args:
            page: Номер страницы
            per_page: Элементов на странице
            endpoint: Endpoint для URL
            
        Returns:
            URL страницы
        """
        if endpoint is None:
            endpoint = request.endpoint
        
        args = self.get_page_args(page, per_page)
        return url_for(endpoint, **args)
    
    def to_dict(self, serialize_items: bool = True) -> Dict[str, Any]:
        """
        Преобразование в словарь для JSON ответа
        
        Args:
            serialize_items: Сериализовать ли элементы
            
        Returns:
            Словарь с данными пагинации
        """
        data = {
            'page': self.page,
            'per_page': self.per_page,
            'total': self.total,
            'total_pages': self.total_pages,
            'has_prev': self.has_prev,
            'has_next': self.has_next,
            'prev_page': self.prev_num,
            'next_page': self.next_num
        }
        
        if serialize_items:
            # Пытаемся сериализовать элементы
            items = []
            for item in self.items:
                if hasattr(item, 'to_dict'):
                    items.append(item.to_dict())
                elif hasattr(item, '__dict__'):
                    items.append(item.__dict__)
                else:
                    items.append(str(item))
            
            data['items'] = items
        
        return data


class CursorPagination:
    """Пагинация по курсору (для больших объемов данных)"""
    
    def __init__(self, query: Query, cursor_field: str = 'id', 
                 cursor: str = None, per_page: int = 20, 
                 order: str = 'desc', max_per_page: int = 100):
        """
        Инициализация курсорной пагинации
        
        Args:
            query: SQLAlchemy Query объект
            cursor_field: Поле для курсора (обычно ID или дата)
            cursor: Значение курсора
            per_page: Количество элементов на странице
            order: Порядок сортировки ('asc' или 'desc')
            max_per_page: Максимальное количество элементов на странице
        """
        self.query = query
        self.cursor_field = cursor_field
        self.cursor = cursor
        self.per_page = min(max(1, per_page), max_per_page)
        self.order = order.lower()
        
        # Получаем поле модели для курсора
        self.model = query.column_descriptions[0]['type']
        self.cursor_column = getattr(self.model, cursor_field)
        
        # Применяем фильтр курсора
        if self.cursor:
            if self.order == 'desc':
                self.query = self.query.filter(self.cursor_column < self.cursor)
            else:
                self.query = self.query.filter(self.cursor_column > self.cursor)
        
        # Применяем сортировку
        if self.order == 'desc':
            self.query = self.query.order_by(self.cursor_column.desc())
        else:
            self.query = self.query.order_by(self.cursor_column.asc())
        
        # Получаем элементы (+1 для проверки наличия следующей страницы)
        self._items = self.query.limit(self.per_page + 1).all()
    
    @property
    def items(self) -> List:
        """Получение элементов текущей страницы"""
        return self._items[:self.per_page]
    
    @property
    def has_next(self) -> bool:
        """Есть ли следующая страница"""
        return len(self._items) > self.per_page
    
    @property
    def next_cursor(self) -> Optional[str]:
        """Курсор для следующей страницы"""
        if self.has_next and self.items:
            last_item = self.items[-1]
            return str(getattr(last_item, self.cursor_field))
        return None
    
    def to_dict(self, serialize_items: bool = True) -> Dict[str, Any]:
        """
        Преобразование в словарь для JSON ответа
        
        Args:
            serialize_items: Сериализовать ли элементы
            
        Returns:
            Словарь с данными пагинации
        """
        data = {
            'cursor': self.cursor,
            'per_page': self.per_page,
            'has_next': self.has_next,
            'next_cursor': self.next_cursor
        }
        
        if serialize_items:
            items = []
            for item in self.items:
                if hasattr(item, 'to_dict'):
                    items.append(item.to_dict())
                elif hasattr(item, '__dict__'):
                    items.append(item.__dict__)
                else:
                    items.append(str(item))
            
            data['items'] = items
        
        return data


def paginate_query(query: Query, page: int = None, per_page: int = None,
                   error_out: bool = True, max_per_page: int = 100) -> Pagination:
    """
    Вспомогательная функция для пагинации запроса
    
    Args:
        query: SQLAlchemy Query объект
        page: Номер страницы (из request.args если не указан)
        per_page: Элементов на странице (из request.args если не указан)
        error_out: Выбрасывать ошибку при некорректных параметрах
        max_per_page: Максимальное количество элементов на странице
        
    Returns:
        Объект Pagination
    """
    if page is None:
        page = request.args.get('page', 1, type=int)
    
    if per_page is None:
        per_page = request.args.get('per_page', 20, type=int)
    
    return Pagination(query, page, per_page, error_out, max_per_page)


def paginate_cursor(query: Query, cursor_field: str = 'id', 
                   cursor: str = None, per_page: int = None,
                   order: str = 'desc', max_per_page: int = 100) -> CursorPagination:
    """
    Вспомогательная функция для курсорной пагинации
    
    Args:
        query: SQLAlchemy Query объект
        cursor_field: Поле для курсора
        cursor: Значение курсора (из request.args если не указан)
        per_page: Элементов на странице (из request.args если не указан)
        order: Порядок сортировки
        max_per_page: Максимальное количество элементов на странице
        
    Returns:
        Объект CursorPagination
    """
    if cursor is None:
        cursor = request.args.get('cursor')
    
    if per_page is None:
        per_page = request.args.get('per_page', 20, type=int)
    
    return CursorPagination(query, cursor_field, cursor, per_page, order, max_per_page)


def build_pagination_links(pagination: Pagination, endpoint: str = None) -> Dict[str, Optional[str]]:
    """
    Создание ссылок для навигации по страницам
    
    Args:
        pagination: Объект пагинации
        endpoint: Endpoint для ссылок
        
    Returns:
        Словарь со ссылками
    """
    if endpoint is None:
        endpoint = request.endpoint
    
    links = {
        'first': pagination.get_page_url(1, endpoint=endpoint),
        'last': pagination.get_page_url(pagination.total_pages, endpoint=endpoint),
        'prev': None,
        'next': None
    }
    
    if pagination.has_prev:
        links['prev'] = pagination.get_page_url(pagination.prev_num, endpoint=endpoint)
    
    if pagination.has_next:
        links['next'] = pagination.get_page_url(pagination.next_num, endpoint=endpoint)
    
    return links


def create_pagination_response(pagination: Pagination, endpoint: str = None) -> Dict[str, Any]:
    """
    Создание полного ответа с пагинацией
    
    Args:
        pagination: Объект пагинации
        endpoint: Endpoint для ссылок
        
    Returns:
        Словарь с данными и метаинформацией
    """
    data = pagination.to_dict()
    links = build_pagination_links(pagination, endpoint)
    
    return {
        'data': data['items'],
        'meta': {
            'pagination': {
                'page': data['page'],
                'per_page': data['per_page'],
                'total': data['total'],
                'total_pages': data['total_pages']
            },
            'links': links
        }
    }