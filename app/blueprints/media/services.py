# app/blueprints/media/services.py
import os
import uuid
from datetime import datetime
from flask import current_app
from werkzeug.utils import secure_filename
from app.models.media import MediaStorage, MediaUploadHelper, is_allowed_file, validate_file_size, get_media_type_from_filename
from app.models.base import GlobalEntity
from app.utils.exceptions import (
    ValidationError, NotFoundError, FileTooLargeError, 
    UnsupportedFileTypeError, AuthorizationError
)
from app.extensions import db


class MediaService:
    """Сервис для работы с медиа файлами"""
    
    @staticmethod
    def upload_file(file, entity_id, user_id, file_order=0, is_primary=False, alt_text=None):
        """
        Загрузка файла
        
        Args:
            file: Файл для загрузки
            entity_id: ID сущности
            user_id: ID пользователя
            file_order: Порядок файла
            is_primary: Является ли основным
            alt_text: Альтернативный текст
            
        Returns:
            Загруженный медиа файл
            
        Raises:
            ValidationError: Если файл некорректен
            AuthorizationError: Если нет прав на загрузку
        """
        # Проверяем права на загрузку файлов для данной сущности
        MediaService._check_upload_permissions(entity_id, user_id)
        
        # Валидация файла
        if not file or not file.filename:
            raise ValidationError("No file provided")
        
        # Проверяем тип файла
        if not is_allowed_file(file.filename):
            raise UnsupportedFileTypeError(file.filename)
        
        # Определяем тип медиа
        media_type = get_media_type_from_filename(file.filename)
        
        # Проверяем размер файла
        file.seek(0, 2)  # Перемещаемся в конец
        file_size = file.tell()
        file.seek(0)  # Возвращаемся в начало
        
        if not validate_file_size(file_size, media_type):
            raise FileTooLargeError()
        
        # Создаем помощник для загрузки
        upload_helper = MediaUploadHelper(current_app.config['UPLOAD_FOLDER'])
        
        try:
            # Загружаем файл
            media = upload_helper.upload_file(
                file=file,
                entity_id=entity_id,
                file_order=file_order,
                is_primary=is_primary
            )
            
            # Устанавливаем альтернативный текст
            if alt_text:
                media.alt_text = alt_text
                media.save()
            
            # Если это первый файл или помечен как основной, делаем его основным
            if is_primary or MediaService._is_first_media_for_entity(entity_id, media_type):
                media.set_as_primary()
            
            return media
            
        except Exception as e:
            raise ValidationError(f"File upload failed: {str(e)}")
    
    @staticmethod
    def _check_upload_permissions(entity_id, user_id):
        """Проверка прав на загрузку файлов"""
        from app.models.listing import Listing
        from app.models.user import User
        
        # Получаем сущность
        entity = GlobalEntity.query.get(entity_id)
        if not entity:
            raise NotFoundError("Entity not found")
        
        # Проверяем права в зависимости от типа сущности
        if entity.entity_type == 'listing':
            listing = Listing.query.filter_by(entity_id=entity_id).first()
            if not listing:
                raise NotFoundError("Listing not found")
            
            # Проверяем владельца объявления или админа
            user = User.query.get(user_id)
            if listing.user_id != user_id and (not user or user.user_type != 'admin'):
                raise AuthorizationError("You can only upload files to your own listings")
        
        elif entity.entity_type == 'user':
            # Пользователь может загружать файлы только для себя
            if entity_id != user_id:
                user = User.query.get(user_id)
                if not user or user.user_type != 'admin':
                    raise AuthorizationError("You can only upload files for yourself")
    
    @staticmethod
    def _is_first_media_for_entity(entity_id, media_type):
        """Проверка, является ли файл первым для сущности"""
        return MediaStorage.count_entity_media(entity_id, media_type) == 0
    
    @staticmethod
    def get_entity_media(entity_id, media_type=None, user_id=None):
        """
        Получение медиа файлов сущности
        
        Args:
            entity_id: ID сущности
            media_type: Тип медиа для фильтрации
            user_id: ID пользователя для проверки прав
            
        Returns:
            Список медиа файлов
            
        Raises:
            AuthorizationError: Если нет прав на просмотр
        """
        # Проверяем права доступа
        if user_id:
            MediaService._check_view_permissions(entity_id, user_id)
        
        return MediaStorage.get_entity_media(entity_id, media_type)
    
    @staticmethod
    def _check_view_permissions(entity_id, user_id):
        """Проверка прав на просмотр медиа файлов"""
        from app.models.listing import Listing
        from app.models.user import User
        
        entity = GlobalEntity.query.get(entity_id)
        if not entity:
            raise NotFoundError("Entity not found")
        
        # Для объявлений проверяем публичность или владельца
        if entity.entity_type == 'listing':
            listing = Listing.query.filter_by(entity_id=entity_id).first()
            if listing and not listing.is_active():
                # Неактивные объявления может смотреть только владелец или админ
                user = User.query.get(user_id)
                if listing.user_id != user_id and (not user or user.user_type != 'admin'):
                    raise AuthorizationError("Access denied")
    
    @staticmethod
    def get_media_file(media_id, user_id=None):
        """
        Получение медиа файла по ID
        
        Args:
            media_id: ID медиа файла
            user_id: ID пользователя для проверки прав
            
        Returns:
            Медиа файл
            
        Raises:
            NotFoundError: Если файл не найден
            AuthorizationError: Если нет прав доступа
        """
        media = MediaStorage.query.get(media_id)
        if not media:
            raise NotFoundError("Media file not found")
        
        # Проверяем права доступа
        if user_id:
            MediaService._check_view_permissions(media.entity_id, user_id)
        
        return media
    
    @staticmethod
    def update_media(media_id, user_id, update_data):
        """
        Обновление медиа файла
        
        Args:
            media_id: ID медиа файла
            user_id: ID пользователя
            update_data: Данные для обновления
            
        Returns:
            Обновленный медиа файл
            
        Raises:
            NotFoundError: Если файл не найден
            AuthorizationError: Если нет прав на редактирование
        """
        media = MediaStorage.query.get(media_id)
        if not media:
            raise NotFoundError("Media file not found")
        
        # Проверяем права на редактирование
        MediaService._check_upload_permissions(media.entity_id, user_id)
        
        # Обновляем поля
        for field, value in update_data.items():
            if hasattr(media, field):
                setattr(media, field, value)
        
        # Если устанавливается как основной
        if update_data.get('is_primary'):
            media.set_as_primary()
        
        media.save()
        return media
    
    @staticmethod
    def delete_media(media_id, user_id):
        """
        Удаление медиа файла
        
        Args:
            media_id: ID медиа файла
            user_id: ID пользователя
            
        Returns:
            True если успешно удален
            
        Raises:
            NotFoundError: Если файл не найден
            AuthorizationError: Если нет прав на удаление
        """
        media = MediaStorage.query.get(media_id)
        if not media:
            raise NotFoundError("Media file not found")
        
        # Проверяем права на удаление
        MediaService._check_upload_permissions(media.entity_id, user_id)
        
        # Удаляем файл с диска
        media.delete_file()
        
        # Удаляем запись из БД
        media.delete()
        
        return True
    
    @staticmethod
    def reorder_media(entity_id, user_id, media_order):
        """
        Изменение порядка медиа файлов
        
        Args:
            entity_id: ID сущности
            user_id: ID пользователя
            media_order: Список ID медиа в новом порядке
            
        Returns:
            True если успешно
            
        Raises:
            AuthorizationError: Если нет прав на редактирование
            ValidationError: Если порядок некорректен
        """
        # Проверяем права на редактирование
        MediaService._check_upload_permissions(entity_id, user_id)
        
        # Проверяем, что все медиа принадлежат данной сущности
        media_files = MediaStorage.query.filter(
            MediaStorage.media_id.in_(media_order),
            MediaStorage.entity_id == entity_id
        ).all()
        
        if len(media_files) != len(media_order):
            raise ValidationError("Invalid media order")
        
        # Изменяем порядок
        MediaStorage.reorder_media(entity_id, media_order)
        
        return True
    
    @staticmethod
    def get_upload_limits():
        """
        Получение лимитов загрузки
        
        Returns:
            Словарь с лимитами
        """
        return {
            'max_file_size': {
                'image': 5 * 1024 * 1024,    # 5MB
                'video': 100 * 1024 * 1024,  # 100MB
                'document': 10 * 1024 * 1024  # 10MB
            },
            'allowed_extensions': {
                'image': ['.jpg', '.jpeg', '.png', '.gif', '.webp'],
                'video': ['.mp4', '.avi', '.mov', '.wmv', '.flv'],
                'document': ['.pdf', '.doc', '.docx', '.txt', '.rtf']
            },
            'max_files_per_entity': {
                'listing': 20,
                'user': 5
            }
        }
    
    @staticmethod
    def generate_thumbnail(media_id):
        """
        Генерация миниатюры для изображения
        
        Args:
            media_id: ID медиа файла
            
        Returns:
            True если миниатюра создана
        """
        media = MediaStorage.query.get(media_id)
        if not media or not media.is_image():
            return False
        
        return media.generate_thumbnail()
    
    @staticmethod
    def get_media_stats(entity_id):
        """
        Получение статистики медиа файлов сущности
        
        Args:
            entity_id: ID сущности
            
        Returns:
            Статистика медиа файлов
        """
        stats = {
            'total_files': MediaStorage.count_entity_media(entity_id),
            'images_count': MediaStorage.count_entity_media(entity_id, 'image'),
            'videos_count': MediaStorage.count_entity_media(entity_id, 'video'),
            'documents_count': MediaStorage.count_entity_media(entity_id, 'document'),
            'total_size': 0
        }
        
        # Подсчитываем общий размер
        media_files = MediaStorage.get_entity_media(entity_id)
        stats['total_size'] = sum(media.file_size or 0 for media in media_files)
        
        return stats
