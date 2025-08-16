# app/models/favorite.py
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Index, UniqueConstraint, Boolean
from sqlalchemy.sql import func
from app.models.base import BaseModel
from app.extensions import db


class Favorite(BaseModel):
    """Модель избранных объявлений"""
    __tablename__ = 'favorites'
    
    favorite_id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.user_id'), nullable=False)
    entity_id = Column(Integer, ForeignKey('global_entities.entity_id'), nullable=False)
    folder_name = Column(String(100))  # Папка для группировки избранного
    added_date = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Ограничения
    __table_args__ = (
        # Один пользователь не может добавить одну сущность в избранное дважды
        UniqueConstraint('user_id', 'entity_id', name='uq_user_entity_favorite'),
        # Индексы для оптимизации
        Index('idx_favorites_user_date', 'user_id', 'added_date'),
        Index('idx_favorites_entity', 'entity_id'),
        Index('idx_favorites_user_folder', 'user_id', 'folder_name'),
    )
    
    # Отношения
    user = db.relationship('User', backref='favorites')
    entity = db.relationship('GlobalEntity', backref='favorites')
    
    @classmethod
    def add_to_favorites(cls, user_id, entity_id, folder_name=None):
        """
        Добавление в избранное
        
        Args:
            user_id: ID пользователя
            entity_id: ID сущности (объявления)
            folder_name: Название папки (опционально)
            
        Returns:
            Favorite объект или None если уже существует
            
        Raises:
            ValidationError: Если данные невалидны
        """
        # Проверяем, не добавлено ли уже в избранное
        existing = cls.query.filter(
            cls.user_id == user_id,
            cls.entity_id == entity_id
        ).first()
        
        if existing:
            return None  # Уже в избранном
        
        # Создаем новую запись
        favorite = cls(
            user_id=user_id,
            entity_id=entity_id,
            folder_name=folder_name
        )
        favorite.save()
        
        # Обновляем счетчик избранного у объявления
        cls._update_listing_favorite_count(entity_id, increment=True)
        
        return favorite
    
    @classmethod
    def remove_from_favorites(cls, user_id, entity_id):
        """
        Удаление из избранного
        
        Args:
            user_id: ID пользователя
            entity_id: ID сущности
            
        Returns:
            bool: True если удалено, False если не было в избранном
        """
        favorite = cls.query.filter(
            cls.user_id == user_id,
            cls.entity_id == entity_id
        ).first()
        
        if favorite:
            favorite.delete()
            
            # Обновляем счетчик избранного у объявления
            cls._update_listing_favorite_count(entity_id, increment=False)
            
            return True
        
        return False
    
    @classmethod
    def toggle_favorite(cls, user_id, entity_id, folder_name=None):
        """
        Переключение статуса избранного
        
        Args:
            user_id: ID пользователя
            entity_id: ID сущности
            folder_name: Название папки (для добавления)
            
        Returns:
            tuple: (Favorite объект или None, bool добавлено ли)
        """
        existing = cls.query.filter(
            cls.user_id == user_id,
            cls.entity_id == entity_id
        ).first()
        
        if existing:
            # Удаляем из избранного
            existing.delete()
            cls._update_listing_favorite_count(entity_id, increment=False)
            return None, False
        else:
            # Добавляем в избранное
            favorite = cls(
                user_id=user_id,
                entity_id=entity_id,
                folder_name=folder_name
            )
            favorite.save()
            cls._update_listing_favorite_count(entity_id, increment=True)
            return favorite, True
    
    @classmethod
    def is_favorited(cls, user_id, entity_id):
        """
        Проверка нахождения в избранном
        
        Args:
            user_id: ID пользователя
            entity_id: ID сущности
            
        Returns:
            bool: True если в избранном
        """
        return cls.query.filter(
            cls.user_id == user_id,
            cls.entity_id == entity_id
        ).first() is not None
    
    @classmethod
    def get_user_favorites(cls, user_id, folder_name=None, page=1, per_page=20):
        """
        Получение избранных объявлений пользователя
        
        Args:
            user_id: ID пользователя
            folder_name: Фильтр по папке (опционально)
            page: Номер страницы
            per_page: Элементов на странице
            
        Returns:
            Pagination объект с избранными
        """
        from app.models.listing import Listing
        from app.utils.pagination import paginate_query
        
        query = cls.query.filter(cls.user_id == user_id)
        
        if folder_name:
            query = query.filter(cls.folder_name == folder_name)
        
        # Джойним с объявлениями для получения актуальной информации
        query = query.join(Listing, Listing.entity_id == cls.entity_id).filter(
            Listing.is_active == True  # Только активные объявления
        ).order_by(cls.added_date.desc())
        
        return paginate_query(query, page, per_page)
    
    @classmethod
    def get_user_folders(cls, user_id):
        """
        Получение папок пользователя с количеством объявлений
        
        Args:
            user_id: ID пользователя
            
        Returns:
            list: Список словарей с информацией о папках
        """
        folders = db.session.query(
            cls.folder_name,
            func.count(cls.favorite_id).label('count')
        ).filter(
            cls.user_id == user_id,
            cls.folder_name.isnot(None)
        ).group_by(cls.folder_name).all()
        
        # Добавляем общую папку (без названия)
        general_count = cls.query.filter(
            cls.user_id == user_id,
            cls.folder_name.is_(None)
        ).count()
        
        result = [{'folder_name': None, 'count': general_count}]
        result.extend([
            {'folder_name': folder.folder_name, 'count': folder.count}
            for folder in folders
        ])
        
        return result
    
    @classmethod
    def move_to_folder(cls, user_id, entity_id, new_folder_name):
        """
        Перемещение избранного в другую папку
        
        Args:
            user_id: ID пользователя
            entity_id: ID сущности
            new_folder_name: Новое название папки
            
        Returns:
            bool: True если успешно перемещено
        """
        favorite = cls.query.filter(
            cls.user_id == user_id,
            cls.entity_id == entity_id
        ).first()
        
        if favorite:
            favorite.folder_name = new_folder_name
            favorite.save()
            return True
        
        return False
    
    @classmethod
    def get_favorites_count(cls, user_id, folder_name=None):
        """
        Получение количества избранных объявлений
        
        Args:
            user_id: ID пользователя
            folder_name: Название папки (опционально)
            
        Returns:
            int: Количество избранных
        """
        query = cls.query.filter(cls.user_id == user_id)
        
        if folder_name:
            query = query.filter(cls.folder_name == folder_name)
        
        return query.count()
    
    @classmethod
    def cleanup_invalid_favorites(cls):
        """
        Очистка избранного с недействительными объявлениями
        
        Returns:
            int: Количество удаленных записей
        """
        from app.models.listing import Listing
        
        # Находим избранные с несуществующими объявлениями
        invalid_favorites = cls.query.outerjoin(
            Listing, Listing.entity_id == cls.entity_id
        ).filter(Listing.listing_id.is_(None)).all()
        
        count = len(invalid_favorites)
        
        for favorite in invalid_favorites:
            favorite.delete()
        
        return count
    
    @classmethod
    def get_popular_listings(cls, limit=10, days=30):
        """
        Получение популярных объявлений по количеству добавлений в избранное
        
        Args:
            limit: Количество объявлений
            days: За последние N дней
            
        Returns:
            list: Список entity_id популярных объявлений
        """
        from_date = datetime.utcnow() - timedelta(days=days)
        
        popular = db.session.query(
            cls.entity_id,
            func.count(cls.favorite_id).label('favorites_count')
        ).filter(
            cls.added_date >= from_date
        ).group_by(cls.entity_id).order_by(
            func.count(cls.favorite_id).desc()
        ).limit(limit).all()
        
        return [item.entity_id for item in popular]
    
    @staticmethod
    def _update_listing_favorite_count(entity_id, increment=True):
        """
        Обновление счетчика избранного у объявления
        
        Args:
            entity_id: ID сущности объявления
            increment: True для увеличения, False для уменьшения
        """
        from app.models.listing import Listing
        
        listing = Listing.query.filter(Listing.entity_id == entity_id).first()
        if listing:
            if increment:
                listing.favorite_count = Listing.favorite_count + 1
            else:
                listing.favorite_count = func.greatest(Listing.favorite_count - 1, 0)
            
            db.session.commit()
    
    def get_listing(self):
        """
        Получение объявления для этого избранного
        
        Returns:
            Listing объект или None
        """
        from app.models.listing import Listing
        
        return Listing.query.filter(Listing.entity_id == self.entity_id).first()
    
    def to_dict(self, include_listing=True):
        """
        Преобразование в словарь
        
        Args:
            include_listing: Включить ли информацию об объявлении
            
        Returns:
            dict: Словарь с данными избранного
        """
        data = {
            'favorite_id': self.favorite_id,
            'user_id': self.user_id,
            'entity_id': self.entity_id,
            'folder_name': self.folder_name,
            'added_date': self.added_date.isoformat(),
        }
        
        if include_listing:
            listing = self.get_listing()
            if listing:
                data['listing'] = listing.to_dict(user_id=self.user_id)
            else:
                data['listing'] = None  # Объявление удалено или недоступно
        
        return data
    
    def __repr__(self):
        return f'<Favorite user_id={self.user_id} entity_id={self.entity_id}>'


class FavoriteFolder(BaseModel):
    """Модель папок для избранного (опциональная, для расширенной функциональности)"""
    __tablename__ = 'favorite_folders'
    
    folder_id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.user_id'), nullable=False)
    folder_name = Column(String(100), nullable=False)
    description = Column(String(255))
    color = Column(String(7))  # HEX цвет для папки
    sort_order = Column(Integer, default=0)
    created_date = Column(DateTime, default=datetime.utcnow)
    is_default = Column(Boolean, default=False)
    
    # Ограничения
    __table_args__ = (
        UniqueConstraint('user_id', 'folder_name', name='uq_user_folder_name'),
        Index('idx_favorite_folders_user', 'user_id', 'sort_order'),
    )
    
    # Отношения
    user = db.relationship('User', backref='favorite_folders')
    
    @classmethod
    def create_folder(cls, user_id, folder_name, description=None, color=None):
        """
        Создание новой папки для избранного
        
        Args:
            user_id: ID пользователя
            folder_name: Название папки
            description: Описание папки
            color: Цвет папки
            
        Returns:
            FavoriteFolder объект
            
        Raises:
            ValidationError: Если папка уже существует
        """
        # Проверяем уникальность названия
        existing = cls.query.filter(
            cls.user_id == user_id,
            cls.folder_name == folder_name
        ).first()
        
        if existing:
            from app.utils.exceptions import ValidationError
            raise ValidationError(f"Folder '{folder_name}' already exists")
        
        # Определяем порядок сортировки
        max_order = db.session.query(func.max(cls.sort_order)).filter(
            cls.user_id == user_id
        ).scalar() or 0
        
        folder = cls(
            user_id=user_id,
            folder_name=folder_name,
            description=description,
            color=color,
            sort_order=max_order + 1
        )
        folder.save()
        
        return folder
    
    @classmethod
    def get_user_folders(cls, user_id):
        """
        Получение папок пользователя с количеством избранных
        
        Args:
            user_id: ID пользователя
            
        Returns:
            list: Список папок с количеством объявлений
        """
        folders = cls.query.filter(cls.user_id == user_id).order_by(
            cls.is_default.desc(), cls.sort_order
        ).all()
        
        result = []
        for folder in folders:
            favorites_count = Favorite.query.filter(
                Favorite.user_id == user_id,
                Favorite.folder_name == folder.folder_name
            ).count()
            
            folder_dict = folder.to_dict()
            folder_dict['favorites_count'] = favorites_count
            result.append(folder_dict)
        
        return result
    
    def rename(self, new_name):
        """
        Переименование папки
        
        Args:
            new_name: Новое название
            
        Returns:
            bool: True если успешно переименовано
        """
        # Проверяем уникальность нового названия
        existing = self.__class__.query.filter(
            self.__class__.user_id == self.user_id,
            self.__class__.folder_name == new_name,
            self.__class__.folder_id != self.folder_id
        ).first()
        
        if existing:
            return False
        
        old_name = self.folder_name
        self.folder_name = new_name
        self.save()
        
        # Обновляем все избранные с этой папкой
        Favorite.query.filter(
            Favorite.user_id == self.user_id,
            Favorite.folder_name == old_name
        ).update({'folder_name': new_name})
        
        db.session.commit()
        return True
    
    def delete_folder(self, move_to_folder=None):
        """
        Удаление папки
        
        Args:
            move_to_folder: Название папки, куда переместить избранные (None для общей папки)
            
        Returns:
            int: Количество перемещенных избранных
        """
        # Перемещаем все избранные из этой папки
        favorites = Favorite.query.filter(
            Favorite.user_id == self.user_id,
            Favorite.folder_name == self.folder_name
        ).all()
        
        for favorite in favorites:
            favorite.folder_name = move_to_folder
            favorite.save()
        
        moved_count = len(favorites)
        
        # Удаляем папку
        self.delete()
        
        return moved_count
    
    def to_dict(self):
        """Преобразование в словарь"""
        return {
            'folder_id': self.folder_id,
            'user_id': self.user_id,
            'folder_name': self.folder_name,
            'description': self.description,
            'color': self.color,
            'sort_order': self.sort_order,
            'created_date': self.created_date.isoformat(),
            'is_default': self.is_default
        }
    
    def __repr__(self):
        return f'<FavoriteFolder {self.folder_name}>'