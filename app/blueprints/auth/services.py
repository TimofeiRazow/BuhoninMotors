# app/blueprints/auth/services.py
import secrets
from datetime import datetime, timedelta
from flask import current_app
from flask_jwt_extended import create_access_token, create_refresh_token, get_jwt_identity, get_jwt
from app.extensions import db
from app.models.user import (
    User, PhoneVerification, EmailVerification, LoginAttempt, RevokedToken
)
from app.utils.exceptions import (
    ValidationError, AuthenticationError, ConflictError, 
    PhoneAlreadyExistsError, EmailAlreadyExistsError, 
    InvalidCredentialsError, VerificationCodeError, UserNotFoundError
)
from app.utils.helpers import normalize_phone_number, validate_email_address, get_client_ip, get_user_agent


class AuthService:
    """Сервис аутентификации"""
    
    @staticmethod
    def register_user(phone_number, password, email=None, first_name=None, last_name=None):
        """
        Регистрация нового пользователя
        
        Args:
            phone_number: Номер телефона
            password: Пароль
            email: Email (опционально)
            first_name: Имя
            last_name: Фамилия
            
        Returns:
            Новый пользователь
            
        Raises:
            PhoneAlreadyExistsError: Если телефон уже зарегистрирован
            EmailAlreadyExistsError: Если email уже зарегистрирован
        """
        # Нормализуем номер телефона
        normalized_phone = normalize_phone_number(phone_number)
        
        # Проверяем существование пользователя с таким телефоном
        existing_user = User.find_by_phone(normalized_phone)
        if existing_user:
            raise PhoneAlreadyExistsError(normalized_phone)
        
        # Проверяем email если указан
        if email:
            normalized_email = validate_email_address(email)
            existing_email_user = User.find_by_email(normalized_email)
            if existing_email_user:
                raise EmailAlreadyExistsError(normalized_email)
        
        # Создаем пользователя
        user = User(
            phone_number=normalized_phone,
            email=email,
            first_name=first_name,
            last_name=last_name
        )
        user.set_password(password)
        user.save()
        
        # Отправляем код верификации телефона
        AuthService.send_phone_verification(normalized_phone)
        
        # Отправляем верификацию email если указан
        if email:
            AuthService.send_email_verification(user.user_id, email)
        
        return user
    
    @staticmethod
    def authenticate_user(identifier, password):
        """
        Аутентификация пользователя
        
        Args:
            identifier: Телефон или email
            password: Пароль
            
        Returns:
            Пользователь и токены
            
        Raises:
            InvalidCredentialsError: Если учетные данные неверны
        """
        ip_address = get_client_ip()
        user_agent = get_user_agent()
        
        # Проверяем лимит попыток входа
        if not LoginAttempt.check_rate_limit(ip_address):
            from app.utils.exceptions import RateLimitError
            raise RateLimitError("Too many login attempts. Try again later.")
        
        # Ищем пользователя по телефону или email
        user = None
        if '@' in identifier:
            user = User.find_by_email(identifier)
        else:
            try:
                normalized_phone = normalize_phone_number(identifier)
                user = User.find_by_phone(normalized_phone)
            except ValueError:
                pass
        
        # Проверяем пароль
        if not user or not user.check_password(password):
            # Логируем неудачную попытку
            LoginAttempt.log_attempt(
                identifier=identifier,
                ip_address=ip_address,
                success=False,
                user_agent=user_agent,
                failure_reason="Invalid credentials"
            )
            raise InvalidCredentialsError()
        
        # Логируем успешную попытку
        LoginAttempt.log_attempt(
            identifier=identifier,
            ip_address=ip_address,
            success=True,
            user_agent=user_agent
        )
        
        # Обновляем время последнего входа
        user.update_last_login()
        
        # Генерируем токены
        tokens = user.generate_tokens()
        
        return user, tokens
    
    @staticmethod
    def send_phone_verification(phone_number):
        """
        Отправка кода верификации на телефон
        
        Args:
            phone_number: Номер телефона
            
        Returns:
            Код верификации (только для тестирования)
        """
        normalized_phone = normalize_phone_number(phone_number)
        ip_address = get_client_ip()
        
        # Генерируем код
        verification_code = secrets.randbelow(900000) + 100000  # 6-значный код
        
        # Создаем запись верификации
        verification = PhoneVerification.create_verification(
            phone_number=normalized_phone,
            code=str(verification_code),
            ip_address=ip_address
        )
        
        # В продакшене здесь должна быть отправка SMS
        if current_app.config.get('TESTING'):
            return verification_code
        
        # TODO: Интеграция с SMS провайдером
        # sms_service.send_sms(normalized_phone, f"Ваш код: {verification_code}")
        
        return True
    
    @staticmethod
    def verify_phone_number(phone_number, verification_code):
        """
        Верификация номера телефона
        
        Args:
            phone_number: Номер телефона
            verification_code: Код верификации
            
        Returns:
            True если верификация успешна
            
        Raises:
            VerificationCodeError: Если код неверен
        """
        normalized_phone = normalize_phone_number(phone_number)
        
        # Проверяем код
        if not PhoneVerification.verify_code(normalized_phone, verification_code):
            raise VerificationCodeError("Invalid or expired verification code")
        
        # Обновляем статус пользователя
        user = User.find_by_phone(normalized_phone)
        if user:
            user.verify_phone()
        
        return True
    
    @staticmethod
    def send_email_verification(user_id, email):
        """
        Отправка верификации email
        
        Args:
            user_id: ID пользователя
            email: Email адрес
            
        Returns:
            True если отправлено
        """
        normalized_email = validate_email_address(email)
        
        # Генерируем токен
        token = secrets.token_urlsafe(32)
        
        # Создаем запись верификации
        verification = EmailVerification.create_verification(
            user_id=user_id,
            email=normalized_email,
            token=token
        )
        
        # В продакшене здесь должна быть отправка email
        if current_app.config.get('TESTING'):
            return token
        
        # TODO: Отправка email
        # email_service.send_verification_email(normalized_email, token)
        
        return True
    
    @staticmethod
    def verify_email(token):
        """
        Верификация email по токену
        
        Args:
            token: Токен верификации
            
        Returns:
            Пользователь если верификация успешна
            
        Raises:
            VerificationCodeError: Если токен неверен
        """
        user = EmailVerification.verify_token(token)
        if not user:
            raise VerificationCodeError("Invalid or expired verification token")
        
        # Обновляем статус пользователя
        user.verify_email()
        
        return user
    
    @staticmethod
    def refresh_access_token():
        """
        Обновление access токена
        
        Returns:
            Новый access токен
            
        Raises:
            AuthenticationError: Если refresh токен невалиден
        """
        try:
            user_id = get_jwt_identity()
            user = User.query.get(user_id)
            
            if not user or not user.is_active:
                raise AuthenticationError("User not found or inactive")
            
            # Генерируем новый access токен
            additional_claims = {
                'user_type': user.user_type,
                'is_verified': user.is_verified
            }
            
            access_token = create_access_token(
                identity=str(user_id),
                additional_claims=str(additional_claims)
            )
            
            return access_token
            
        except Exception:
            raise AuthenticationError("Invalid refresh token")
    
    @staticmethod
    def logout_user():
        """
        Выход пользователя (добавление токена в черный список)
        
        Returns:
            True если успешно
        """
        try:
            jti = get_jwt()['jti']
            user_id = get_jwt_identity()
            
            # Добавляем токен в черный список
            RevokedToken.revoke_token(jti, user_id)
            
            return True
            
        except Exception:
            return False
    
    @staticmethod
    def reset_password(identifier):
        """
        Запрос на сброс пароля
        
        Args:
            identifier: Телефон или email
            
        Returns:
            True если запрос отправлен
        """
        user = None
        
        # Ищем пользователя
        if '@' in identifier:
            user = User.find_by_email(identifier)
        else:
            try:
                normalized_phone = normalize_phone_number(identifier)
                user = User.find_by_phone(normalized_phone)
            except ValueError:
                pass
        
        if not user:
            # Не раскрываем информацию о существовании пользователя
            return True
        
        if '@' in identifier:
            # Отправляем ссылку на email
            token = secrets.token_urlsafe(32)
            AuthService.send_email_verification(user.user_id, user.email)
        else:
            # Отправляем SMS код
            AuthService.send_phone_verification(user.phone_number)
        
        return True
    
    @staticmethod
    def change_password(user_id, current_password, new_password):
        """
        Смена пароля пользователя
        
        Args:
            user_id: ID пользователя
            current_password: Текущий пароль
            new_password: Новый пароль
            
        Returns:
            True если пароль изменен
            
        Raises:
            UserNotFoundError: Если пользователь не найден
            InvalidCredentialsError: Если текущий пароль неверен
        """
        user = User.query.get(user_id)
        if not user:
            raise UserNotFoundError()
        
        # Проверяем текущий пароль
        if not user.check_password(current_password):
            raise InvalidCredentialsError()
        
        # Устанавливаем новый пароль
        user.set_password(new_password)
        user.save()
        
        return True


