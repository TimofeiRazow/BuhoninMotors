# app/models/media.py
import os
from datetime import datetime
from sqlalchemy import Column, Integer, String, BigInteger, Boolean, DateTime, ForeignKey, Index
from sqlalchemy.dialects.postgresql import JSONB
from app.models.base import BaseModel
from app.extensions import db


class MediaStorage(BaseModel):
    """Модель для хранения медиа файлов"""
    __tablename__ = 'media_storage'
    
    media_id = Column(Integer, primary_key=True)
    entity_id = Column(BigInteger, ForeignKey('global_entities.entity_id'), nullable=False)
    media_type = Column(String(20), nullable=False)
    file_url = Column(String(1000), nullable=False)
    thumbnail_url = Column(String(1000))
    file_name = Column(String(255))
    file_size = Column(BigInteger)
    mime_type = Column(String(100))
    file_order = Column(Integer, default=0)
    is_primary = Column(Boolean, default=False)
    alt_text = Column(String(255))
    uploaded_date = Column(DateTime, default=datetime.utcnow)
    storage_provider = Column(String(50), default='local')
    external_id = Column(String(255))
    metadata = Column(JSONB, default={})
    
    __table_args__ = (
        db.CheckConstraint(
            "media_type IN ('image', 'video', 'document')",
            name='check_media_type'
        ),
        # Индексы для оптимизации
        Index('idx_media_entity_primary', 'entity_id', 'file_order', 
              postgresql_where=db.text('is_primary = true')),
        Index('idx_media_entity_all', 'entity_id', 'media_type', 'file_order'),
    )
    
    # Отношения
    global_entity = db.relationship('GlobalEntity', backref='media_files')
    
    @classmethod
    def create_from_upload(cls, entity_id, file, file_order=0, is_primary=False, storage_provider='local'):
        """Создание записи медиа из загруженного файла"""
        media = cls(
            entity_id=entity_id,
            media_type=cls._get_media_type_from_mime(file.content_type),
            file_name=file.filename,
            file_size=cls._get_file_size(file),
            mime_type=file.content_type,
            file_order=file_order,
            is_primary=is_primary,
            storage_provider=storage_provider
        )
        
        return media
    
    @staticmethod
    def _get_media_type_from_mime(mime_type):
        """Определение типа медиа по MIME типу"""
        if mime_type.startswith('image/'):
            return 'image'
        elif mime_type.startswith('video/'):
            return 'video'
        else:
            return 'document'
    
    @staticmethod
    def _get_file_size(file):
        """Получение размера файла"""
        try:
            file.seek(0, 2)  # Перемещаемся в конец файла
            size = file.tell()
            file.seek(0)  # Возвращаемся в начало
            return size
        except:
            return None
    
    def set_as_primary(self):
        """Установка как основного файла"""
        # Сначала убираем флаг primary у других файлов этой сущности
        MediaStorage.query.filter(
            MediaStorage.entity_id == self.entity_id,
            MediaStorage.media_type == self.media_type,
            MediaStorage.media_id != self.media_id
        ).update({'is_primary': False})
        
        self.is_primary = True
        db.session.commit()
    
    def generate_thumbnail(self, size=(200, 200)):
        """Генерация миниатюры для изображения"""
        if self.media_type != 'image':
            return False
        
        try:
            from PIL import Image
            import io
            
            # Здесь должна быть логика генерации миниатюры
            # Это упрощенный пример
            
            # Сохраняем URL миниатюры
            base_name = os.path.splitext(self.file_url)[0]
            self.thumbnail_url = f"{base_name}_thumb.jpg"
            
            self.save()
            return True
            
        except ImportError:
            # Если Pillow не установлен
            return False
        except Exception as e:
            print(f"Error generating thumbnail: {e}")
            return False
    
    def delete_file(self):
        """Удаление файла с диска/облака"""
        try:
            if self.storage_provider == 'local':
                if os.path.exists(self.file_url):
                    os.remove(self.file_url)
                
                if self.thumbnail_url and os.path.exists(self.thumbnail_url):
                    os.remove(self.thumbnail_url)
            
            # Здесь можно добавить логику для других провайдеров (S3, etc.)
            
            return True
        except Exception as e:
            print(f"Error deleting file: {e}")
            return False
    
    def get_file_extension(self):
        """Получение расширения файла"""
        if self.file_name:
            return os.path.splitext(self.file_name)[1].lower()
        return ''
    
    def is_image(self):
        """Проверка, является ли файл изображением"""
        return self.media_type == 'image'
    
    def is_video(self):
        """Проверка, является ли файл видео"""
        return self.media_type == 'video'
    
    def is_document(self):
        """Проверка, является ли файл документом"""
        return self.media_type == 'document'
    
    def get_display_size(self):
        """Получение читаемого размера файла"""
        if not self.file_size:
            return "Unknown"
        
        for unit in ['B', 'KB', 'MB', 'GB']:
            if self.file_size < 1024.0:
                return f"{self.file_size:.1f} {unit}"
            self.file_size /= 1024.0
        
        return f"{self.file_size:.1f} TB"
    
    @classmethod
    def get_entity_media(cls, entity_id, media_type=None):
        """Получение медиа файлов сущности"""
        query = cls.query.filter(cls.entity_id == entity_id)
        
        if media_type:
            query = query.filter(cls.media_type == media_type)
        
        return query.order_by(cls.file_order, cls.uploaded_date).all()
    
    @classmethod
    def get_primary_image(cls, entity_id):
        """Получение основного изображения сущности"""
        return cls.query.filter(
            cls.entity_id == entity_id,
            cls.media_type == 'image',
            cls.is_primary == True
        ).first()
    
    @classmethod
    def count_entity_media(cls, entity_id, media_type=None):
        """Подсчет медиа файлов сущности"""
        query = cls.query.filter(cls.entity_id == entity_id)
        
        if media_type:
            query = query.filter(cls.media_type == media_type)
        
        return query.count()
    
    @classmethod
    def reorder_media(cls, entity_id, media_ids_order):
        """Изменение порядка медиа файлов"""
        for order, media_id in enumerate(media_ids_order):
            cls.query.filter(
                cls.media_id == media_id,
                cls.entity_id == entity_id
            ).update({'file_order': order})
        
        db.session.commit()
    
    def to_dict(self):
        """Преобразование в словарь"""
        return {
            'media_id': self.media_id,
            'entity_id': self.entity_id,
            'media_type': self.media_type,
            'file_url': self.file_url,
            'thumbnail_url': self.thumbnail_url,
            'file_name': self.file_name,
            'file_size': self.file_size,
            'file_size_display': self.get_display_size(),
            'mime_type': self.mime_type,
            'file_order': self.file_order,
            'is_primary': self.is_primary,
            'alt_text': self.alt_text,
            'uploaded_date': self.uploaded_date.isoformat() if self.uploaded_date else None,
            'storage_provider': self.storage_provider,
            'metadata': self.metadata
        }
    
    def __repr__(self):
        return f'<MediaStorage {self.file_name} ({self.media_type})>'


# Вспомогательные функции для работы с медиа
def get_allowed_extensions():
    """Получение разрешенных расширений файлов"""
    return {
        'image': ['.jpg', '.jpeg', '.png', '.gif', '.webp'],
        'video': ['.mp4', '.avi', '.mov', '.wmv', '.flv'],
        'document': ['.pdf', '.doc', '.docx', '.txt', '.rtf']
    }


def is_allowed_file(filename, media_type=None):
    """Проверка разрешенного расширения файла"""
    if not filename or '.' not in filename:
        return False
    
    ext = os.path.splitext(filename)[1].lower()
    allowed = get_allowed_extensions()
    
    if media_type:
        return ext in allowed.get(media_type, [])
    
    # Проверяем все типы
    for extensions in allowed.values():
        if ext in extensions:
            return True
    
    return False


def get_media_type_from_filename(filename):
    """Определение типа медиа по имени файла"""
    if not filename:
        return 'document'
    
    ext = os.path.splitext(filename)[1].lower()
    allowed = get_allowed_extensions()
    
    for media_type, extensions in allowed.items():
        if ext in extensions:
            return media_type
    
    return 'document'


def validate_file_size(file_size, media_type):
    """Валидация размера файла"""
    max_sizes = {
        'image': 5 * 1024 * 1024,    # 5MB
        'video': 100 * 1024 * 1024,  # 100MB
        'document': 10 * 1024 * 1024  # 10MB
    }
    
    max_size = max_sizes.get(media_type, 5 * 1024 * 1024)
    return file_size <= max_size


def clean_filename(filename):
    """Очистка имени файла от недопустимых символов"""
    import re
    
    if not filename:
        return None
    
    # Убираем путь, оставляем только имя файла
    filename = os.path.basename(filename)
    
    # Заменяем недопустимые символы
    filename = re.sub(r'[^\w\-_\.]', '_', filename)
    
    # Убираем множественные подчеркивания
    filename = re.sub(r'_+', '_', filename)
    
    return filename


def generate_unique_filename(original_filename, entity_id):
    """Генерация уникального имени файла"""
    import uuid
    
    if not original_filename:
        return f"{entity_id}_{uuid.uuid4().hex}"
    
    name, ext = os.path.splitext(clean_filename(original_filename))
    unique_id = uuid.uuid4().hex[:8]
    timestamp = int(datetime.utcnow().timestamp())
    
    return f"{entity_id}_{timestamp}_{unique_id}_{name}{ext}"


class MediaUploadHelper:
    """Помощник для загрузки медиа файлов"""
    
    def __init__(self, upload_folder, allowed_extensions=None):
        self.upload_folder = upload_folder
        self.allowed_extensions = allowed_extensions or get_allowed_extensions()
    
    def save_file(self, file, entity_id, subfolder=None):
        """Сохранение файла на диск"""
        if not file or not file.filename:
            return None
        
        # Проверяем расширение
        if not is_allowed_file(file.filename):
            raise ValueError("File type not allowed")
        
        # Генерируем уникальное имя файла
        filename = generate_unique_filename(file.filename, entity_id)
        
        # Создаем путь для сохранения
        if subfolder:
            save_folder = os.path.join(self.upload_folder, subfolder)
        else:
            save_folder = self.upload_folder
        
        os.makedirs(save_folder, exist_ok=True)
        
        file_path = os.path.join(save_folder, filename)
        
        try:
            file.save(file_path)
            return file_path
        except Exception as e:
            print(f"Error saving file: {e}")
            return None
    
    def create_media_record(self, file, entity_id, file_path, **kwargs):
        """Создание записи в базе данных"""
        media = MediaStorage.create_from_upload(
            entity_id=entity_id,
            file=file,
            **kwargs
        )
        
        media.file_url = file_path
        media.save()
        
        # Генерируем миниатюру для изображений
        if media.is_image():
            media.generate_thumbnail()
        
        return media
    
    def upload_file(self, file, entity_id, **kwargs):
        """Полный процесс загрузки файла"""
        file_path = self.save_file(file, entity_id)
        
        if not file_path:
            return None
        
        try:
            media = self.create_media_record(file, entity_id, file_path, **kwargs)
            return media
        except Exception as e:
            # Удаляем файл в случае ошибки
            if os.path.exists(file_path):
                os.remove(file_path)
            raise e