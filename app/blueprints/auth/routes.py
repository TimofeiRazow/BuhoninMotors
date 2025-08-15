# app/blueprints/auth/routes.py
from flask import request, jsonify, g
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.blueprints.auth import bp
from app.blueprints.auth.shemas import (
    RegisterSchema, LoginSchema, VerifyPhoneSchema, SendVerificationCodeSchema,
    VerifyEmailSchema, ResetPasswordSchema, ChangePasswordSchema, RefreshTokenSchema
)
from app.blueprints.auth.services import AuthService
from app.utils.decorators import validate_json, handle_errors, auth_required, rate_limit_by_user, rate_limit_by_ip
from app.utils.helpers import build_response, build_error_response


@bp.route('/register', methods=['POST'])
@handle_errors
@validate_json(RegisterSchema)
#@rate_limit_by_ip('register', max_requests=5, window_minutes=60)
def register():
    """Регистрация нового пользователя"""
    data = g.validated_data
    
    user = AuthService.register_user(
        phone_number=data['phone_number'],
        password=data['password'],
        email=data.get('email'),
        first_name=data.get('first_name'),
        last_name=data.get('last_name')
    )
    
    return jsonify(build_response(
        data=user.to_dict(),
        message="User registered successfully. Please verify your phone number.",
        status_code=201
    ))


@bp.route('/login', methods=['POST'])
@handle_errors
@validate_json(LoginSchema)
@rate_limit_by_user('login', max_requests=10, window_minutes=15)
def login():
    """Вход пользователя"""
    data = g.validated_data
    
    user, tokens = AuthService.authenticate_user(
        identifier=data['identifier'],
        password=data['password']
    )
    
    response_data = {
        'user': user.to_dict(),
        'tokens': tokens
    }
    
    return jsonify(build_response(
        data=response_data,
        message="Login successful"
    ))


@bp.route('/logout', methods=['POST'])
@handle_errors
@jwt_required()
def logout():
    """Выход пользователя"""
    AuthService.logout_user()
    
    return jsonify(build_response(
        data=None,
        message="Logout successful"
    ))


@bp.route('/refresh', methods=['POST'])
@handle_errors
@jwt_required(refresh=True)
def refresh():
    """Обновление access токена"""
    access_token = AuthService.refresh_access_token()
    
    return jsonify(build_response(
        data={'access_token': access_token},
        message="Token refreshed successfully"
    ))


@bp.route('/send-verification-code', methods=['POST'])
@handle_errors
@validate_json(SendVerificationCodeSchema)
@rate_limit_by_user('send_verification', max_requests=3, window_minutes=60)
def send_verification_code():
    """Отправка кода верификации"""
    data = g.validated_data
    
    result = AuthService.send_phone_verification(data['phone_number'])
    
    return jsonify(build_response(
        data={'verification_sent': True},
        message="Verification code sent successfully"
    ))


@bp.route('/verify-phone', methods=['POST'])
@handle_errors
@validate_json(VerifyPhoneSchema)
def verify_phone():
    """Верификация номера телефона"""
    data = g.validated_data
    
    AuthService.verify_phone_number(
        phone_number=data['phone_number'],
        verification_code=data['verification_code']
    )
    
    return jsonify(build_response(
        data={'verified': True},
        message="Phone number verified successfully"
    ))


@bp.route('/verify-email', methods=['POST'])
@handle_errors
@validate_json(VerifyEmailSchema)
def verify_email():
    """Верификация email"""
    data = g.validated_data
    
    user = AuthService.verify_email(data['token'])
    
    return jsonify(build_response(
        data={'verified': True, 'user': user.to_dict()},
        message="Email verified successfully"
    ))


@bp.route('/reset-password', methods=['POST'])
@handle_errors
@validate_json(ResetPasswordSchema)
@rate_limit_by_user('reset_password', max_requests=3, window_minutes=60)
def reset_password():
    """Запрос на сброс пароля"""
    data = g.validated_data
    
    AuthService.reset_password(data['identifier'])
    
    return jsonify(build_response(
        data={'reset_sent': True},
        message="Password reset instructions sent"
    ))


@bp.route('/change-password', methods=['POST'])
@handle_errors
@validate_json(ChangePasswordSchema)
@auth_required
def change_password():
    """Смена пароля"""
    data = g.validated_data
    
    AuthService.change_password(
        user_id=g.current_user.user_id,
        current_password=data['current_password'],
        new_password=data['new_password']
    )
    
    return jsonify(build_response(
        data={'password_changed': True},
        message="Password changed successfully"
    ))


@bp.route('/me', methods=['GET'])
@handle_errors
@auth_required
def get_current_user():
    """Получение информации о текущем пользователе"""
    return jsonify(build_response(
        data=g.current_user.to_dict(),
        message="User information retrieved successfully"
    ))