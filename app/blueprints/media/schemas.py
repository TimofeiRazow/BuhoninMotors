
# app/blueprints/media/schemas.py
from marshmallow import Schema, fields, validate, validates, ValidationError


class FileUploadSchema(Schema):
    """Схема для загрузки файла"""
    entity_id = fields.Int(required=True)
    file_order = fields.Int(required=False, default=0, validate=validate.Range(min=0))
    is_primary = fields.Bool(required=False, default=False)
    alt_text = fields.Str(required=False, validate=validate.Length(max=255))


class MediaFileSchema(Schema):
    """Схема для медиа файла"""
    media_id = fields.Int(dump_only=True)
    entity_id = fields.Int(dump_only=True)
    media_type = fields.Str(dump_only=True)
    file_url = fields.Str(dump_only=True)
    thumbnail_url = fields.Str(dump_only=True)
    file_name = fields.Str(dump_only=True)
    file_size = fields.Int(dump_only=True)
    file_size_display = fields.Str(dump_only=True)
    mime_type = fields.Str(dump_only=True)
    file_order = fields.Int(dump_only=True)
    is_primary = fields.Bool(dump_only=True)
    alt_text = fields.Str(dump_only=True)
    uploaded_date = fields.DateTime(dump_only=True)
    storage_provider = fields.Str(dump_only=True)


class UpdateMediaSchema(Schema):
    """Схема для обновления медиа файла"""
    file_order = fields.Int(required=False, validate=validate.Range(min=0))
    is_primary = fields.Bool(required=False)
    alt_text = fields.Str(required=False, validate=validate.Length(max=255))


class MediaReorderSchema(Schema):
    """Схема для изменения порядка медиа файлов"""
    media_order = fields.List(fields.Int(), required=True, validate=validate.Length(min=1))