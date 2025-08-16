# app/blueprints/users/routes.py
"""
Роуты для управления пользователями
"""

from flask import request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from marshmallow import ValidationError

from app.blueprints.users import bp
from app.blueprints.users.services import UserService
from app.blueprints.users.schemas import (
    UserProfileSchema, UserProfileUpdateSchema, UserSettingsSchema,
    ChangePasswordSchema, UserStatsSchema, UserListSchema
)
from app.utils.decorators import admin_required, validate_json
from app.utils.pagination import paginate_query
from app.utils.exceptions import APIException
from app.database import get_db


@bp.route('/profile', methods=['GET'])
@jwt_required()
def get_profile():
    """Получение профиля текущего пользователя"""
    try:
        user_id = get_jwt_identity()
        db = get_db()
        
        user_data = UserService.get_user_profile(db, user_id)
        if not user_data:
            return jsonify({'error': 'User not found'}), 404
        
        schema = UserProfileSchema()
        return jsonify({
            'success': True,
            'data': schema.dump(user_data)
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting user profile: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@bp.route('/profile', methods=['PUT'])
@jwt_required()
@validate_json(UserProfileUpdateSchema)  # Fixed: Added schema parameter
def update_profile():
    """Обновление профиля пользователя"""
    try:
        user_id = get_jwt_identity()
        db = get_db()
        
        # Get validated data from g.validated_data (set by the decorator)
        from flask import g
        data = g.validated_data
        
        updated_user = UserService.update_user_profile(db, user_id, data)
        if not updated_user:
            return jsonify({'error': 'User not found'}), 404
        
        response_schema = UserProfileSchema()
        return jsonify({
            'success': True,
            'message': 'Profile updated successfully',
            'data': response_schema.dump(updated_user)
        })
        
    except APIException as e:
        return jsonify({'error': str(e)}), e.status_code
    except Exception as e:
        current_app.logger.error(f"Error updating user profile: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@bp.route('/settings', methods=['GET'])
@jwt_required()
def get_settings():
    """Получение настроек пользователя"""
    try:
        user_id = get_jwt_identity()
        db = get_db()
        
        settings = UserService.get_user_settings(db, user_id)
        schema = UserSettingsSchema()
        
        return jsonify({
            'success': True,
            'data': schema.dump(settings)
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting user settings: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@bp.route('/settings', methods=['PUT'])
@jwt_required()
@validate_json(UserSettingsSchema)  # Fixed: Added schema parameter
def update_settings():
    """Обновление настроек пользователя"""
    try:
        user_id = get_jwt_identity()
        db = get_db()
        
        # Get validated data from g.validated_data (set by the decorator)
        from flask import g
        data = g.validated_data
        
        updated_settings = UserService.update_user_settings(db, user_id, data)
        
        schema = UserSettingsSchema()
        return jsonify({
            'success': True,
            'message': 'Settings updated successfully',
            'data': schema.dump(updated_settings)
        })
        
    except Exception as e:
        current_app.logger.error(f"Error updating user settings: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@bp.route('/change-password', methods=['POST'])
@jwt_required()
@validate_json(ChangePasswordSchema)  # Fixed: Added schema parameter
def change_password():
    """Смена пароля пользователя"""
    try:
        user_id = get_jwt_identity()
        db = get_db()
        
        # Get validated data from g.validated_data (set by the decorator)
        from flask import g
        data = g.validated_data
        
        success = UserService.change_password(
            db, user_id, data['current_password'], data['new_password']
        )
        
        if not success:
            return jsonify({'error': 'Current password is incorrect'}), 400
        
        return jsonify({
            'success': True,
            'message': 'Password changed successfully'
        })
        
    except Exception as e:
        current_app.logger.error(f"Error changing password: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@bp.route('/stats', methods=['GET'])
@jwt_required()
def get_user_stats():
    """Получение статистики пользователя"""
    try:
        user_id = get_jwt_identity()
        print('TRALALELOTRALALA')
        db = get_db()
        print(db)
        
        stats = UserService.get_user_statistics(db, user_id)
        schema = UserStatsSchema()
        
        return jsonify({
            'success': True,
            'data': schema.dump(stats)
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting user stats: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@bp.route('/<int:user_id>/reviews', methods=['GET'])
def get_user_reviews(user_id):
    """Получение отзывов о пользователе"""
    try:
        db = get_db()
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        
        reviews = UserService.get_user_reviews(db, user_id, page, per_page)
        
        return jsonify({
            'success': True,
            'data': reviews
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting user reviews: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@bp.route('/<int:user_id>/public-profile', methods=['GET'])
def get_public_profile(user_id):
    """Получение публичного профиля пользователя"""
    try:
        db = get_db()
        
        user_data = UserService.get_public_profile(db, user_id)
        if not user_data:
            return jsonify({'error': 'User not found'}), 404
        
        return jsonify({
            'success': True,
            'data': user_data
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting public profile: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@bp.route('/search', methods=['GET'])
@jwt_required()
def search_users():
    """Поиск пользователей (только для админов)"""
    try:
        db = get_db()
        current_user_id = get_jwt_identity()
        
        # Проверяем права администратора
        if not UserService.is_admin(db, current_user_id):
            return jsonify({'error': 'Access denied'}), 403
        
        query = request.args.get('q', '')
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        
        users = UserService.search_users(db, query, page, per_page)
        
        return jsonify({
            'success': True,
            'data': users
        })
        
    except Exception as e:
        current_app.logger.error(f"Error searching users: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@bp.route('/<int:user_id>/block', methods=['POST'])
@jwt_required()
def block_user(user_id):
    """Блокировка пользователя (только для админов)"""
    try:
        db = get_db()
        current_user_id = get_jwt_identity()
        
        # Проверяем права администратора
        if not UserService.is_admin(db, current_user_id):
            return jsonify({'error': 'Access denied'}), 403
        
        reason = request.json.get('reason', '') if request.json else ''
        
        success = UserService.block_user(db, user_id, current_user_id, reason)
        if not success:
            return jsonify({'error': 'User not found or already blocked'}), 400
        
        return jsonify({
            'success': True,
            'message': 'User blocked successfully'
        })
        
    except Exception as e:
        current_app.logger.error(f"Error blocking user: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@bp.route('/<int:user_id>/unblock', methods=['POST'])
@jwt_required()
def unblock_user(user_id):
    """Разблокировка пользователя (только для админов)"""
    try:
        db = get_db()
        current_user_id = get_jwt_identity()
        
        # Проверяем права администратора
        if not UserService.is_admin(db, current_user_id):
            return jsonify({'error': 'Access denied'}), 403
        
        success = UserService.unblock_user(db, user_id, current_user_id)
        if not success:
            return jsonify({'error': 'User not found or not blocked'}), 400
        
        return jsonify({
            'success': True,
            'message': 'User unblocked successfully'
        })
        
    except Exception as e:
        current_app.logger.error(f"Error unblocking user: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@bp.route('/devices', methods=['GET'])
@jwt_required()
def get_user_devices():
    """Получение устройств пользователя"""
    try:
        user_id = get_jwt_identity()
        db = get_db()
        
        devices = UserService.get_user_devices(db, user_id)
        
        return jsonify({
            'success': True,
            'data': devices
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting user devices: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@bp.route('/devices/<device_id>', methods=['DELETE'])
@jwt_required()
def remove_device(device_id):
    """Удаление устройства пользователя"""
    try:
        user_id = get_jwt_identity()
        db = get_db()
        
        success = UserService.remove_user_device(db, user_id, device_id)
        if not success:
            return jsonify({'error': 'Device not found'}), 404
        
        return jsonify({
            'success': True,
            'message': 'Device removed successfully'
        })
        
    except Exception as e:
        current_app.logger.error(f"Error removing device: {e}")
        return jsonify({'error': 'Internal server error'}), 500