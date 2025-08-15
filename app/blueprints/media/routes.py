# app/blueprints/media/routes.py
from flask import request, jsonify, g, send_file
from werkzeug.exceptions import RequestEntityTooLarge
from app.blueprints.media import bp
from app.blueprints.media.services import MediaService
from app.blueprints.media.schemas import (
    FileUploadSchema, MediaFileSchema, UpdateMediaSchema, MediaReorderSchema
)
from app.utils.decorators import (
    handle_errors, auth_required, validate_json, rate_limit_by_user
)
from app.utils.helpers import build_response
from app.utils.exceptions import ValidationError


@bp.route('/upload', methods=['POST'])
@handle_errors
@auth_required
@rate_limit_by_user('media_upload', max_requests=50, window_minutes=60)
def upload_file():
    """Загрузка медиа файла"""
    try:
        # Проверяем наличие файла
        if 'file' not in request.files:
            raise ValidationError("No file provided")
        
        file = request.files['file']
        if file.filename == '':
            raise ValidationError("No file selected")
        
        # Получаем параметры из формы
        entity_id = request.form.get('entity_id', type=int)
        if not entity_id:
            raise ValidationError("Entity ID is required")
        
        file_order = request.form.get('file_order', 0, type=int)
        is_primary = request.form.get('is_primary', 'false').lower() == 'true'
        alt_text = request.form.get('alt_text', '').strip() or None
        
        # Загружаем файл
        media = MediaService.upload_file(
            file=file,
            entity_id=entity_id,
            user_id=g.current_user.user_id,
            file_order=file_order,
            is_primary=is_primary,
            alt_text=alt_text
        )
        
        schema = MediaFileSchema()
        
        return jsonify(build_response(
            data=schema.dump(media),
            message="File uploaded successfully",
            status_code=201
        ))
        
    except RequestEntityTooLarge:
        raise ValidationError("File too large")


@bp.route('/entity/<int:entity_id>', methods=['GET'])
@handle_errors
def get_entity_media(entity_id):
    """Получение медиа файлов сущности"""
    media_type = request.args.get('media_type')
    user_id = g.current_user.user_id if hasattr(g, 'current_user') else None
    
    media_files = MediaService.get_entity_media(entity_id, media_type, user_id)
    schema = MediaFileSchema(many=True)
    
    return jsonify(build_response(
        data=schema.dump(media_files),
        message="Media files retrieved successfully"
    ))


@bp.route('/<int:media_id>', methods=['GET'])
@handle_errors
def get_media_file(media_id):
    """Получение медиа файла по ID"""
    user_id = g.current_user.user_id if hasattr(g, 'current_user') else None
    
    media = MediaService.get_media_file(media_id, user_id)
    schema = MediaFileSchema()
    
    return jsonify(build_response(
        data=schema.dump(media),
        message="Media file retrieved successfully"
    ))


@bp.route('/<int:media_id>', methods=['PUT'])
@handle_errors
@validate_json(UpdateMediaSchema)
@auth_required
def update_media_file(media_id):
    """Обновление медиа файла"""
    data = g.validated_data
    
    media = MediaService.update_media(media_id, g.current_user.user_id, data)
    schema = MediaFileSchema()
    
    return jsonify(build_response(
        data=schema.dump(media),
        message="Media file updated successfully"
    ))


@bp.route('/<int:media_id>', methods=['DELETE'])
@handle_errors
@auth_required
def delete_media_file(media_id):
    """Удаление медиа файла"""
    success = MediaService.delete_media(media_id, g.current_user.user_id)
    
    return jsonify(build_response(
        data={'deleted': success},
        message="Media file deleted successfully"
    ))


@bp.route('/entity/<int:entity_id>/reorder', methods=['POST'])
@handle_errors
@validate_json(MediaReorderSchema)
@auth_required
def reorder_media_files(entity_id):
    """Изменение порядка медиа файлов"""
    data = g.validated_data
    
    success = MediaService.reorder_media(
        entity_id=entity_id,
        user_id=g.current_user.user_id,
        media_order=data['media_order']
    )
    
    return jsonify(build_response(
        data={'reordered': success},
        message="Media files reordered successfully"
    ))


@bp.route('/<int:media_id>/download', methods=['GET'])
@handle_errors
def download_file(media_id):
    """Скачивание медиа файла"""
    user_id = g.current_user.user_id if hasattr(g, 'current_user') else None
    
    media = MediaService.get_media_file(media_id, user_id)
    
    try:
        return send_file(
            media.file_url,
            as_attachment=True,
            download_name=media.file_name,
            mimetype=media.mime_type
        )
    except FileNotFoundError:
        raise ValidationError("File not found on disk")


@bp.route('/<int:media_id>/thumbnail', methods=['POST'])
@handle_errors
@auth_required
def generate_thumbnail(media_id):
    """Генерация миниатюры для изображения"""
    success = MediaService.generate_thumbnail(media_id)
    
    return jsonify(build_response(
        data={'thumbnail_generated': success},
        message="Thumbnail generated successfully" if success else "Cannot generate thumbnail"
    ))


@bp.route('/entity/<int:entity_id>/stats', methods=['GET'])
@handle_errors
def get_media_stats(entity_id):
    """Получение статистики медиа файлов"""
    stats = MediaService.get_media_stats(entity_id)
    
    return jsonify(build_response(
        data=stats,
        message="Media statistics retrieved successfully"
    ))


@bp.route('/limits', methods=['GET'])
@handle_errors
def get_upload_limits():
    """Получение лимитов загрузки"""
    limits = MediaService.get_upload_limits()
    
    return jsonify(build_response(
        data=limits,
        message="Upload limits retrieved successfully"
    ))


@bp.route('/multiple-upload', methods=['POST'])
@handle_errors
@auth_required
@rate_limit_by_user('bulk_upload', max_requests=10, window_minutes=60)
def upload_multiple_files():
    """Загрузка нескольких файлов"""
    try:
        # Проверяем наличие файлов
        files = request.files.getlist('files')
        if not files:
            raise ValidationError("No files provided")
        
        entity_id = request.form.get('entity_id', type=int)
        if not entity_id:
            raise ValidationError("Entity ID is required")
        
        uploaded_files = []
        
        for i, file in enumerate(files):
            if file.filename == '':
                continue
            
            try:
                media = MediaService.upload_file(
                    file=file,
                    entity_id=entity_id,
                    user_id=g.current_user.user_id,
                    file_order=i,
                    is_primary=(i == 0)  # Первый файл как основной
                )
                uploaded_files.append(media)
                
            except Exception as e:
                # Продолжаем загрузку остальных файлов
                continue
        
        schema = MediaFileSchema(many=True)
        
        return jsonify(build_response(
            data=schema.dump(uploaded_files),
            message=f"Uploaded {len(uploaded_files)} files successfully",
            status_code=201
        ))
        
    except RequestEntityTooLarge:
        raise ValidationError("Files too large")