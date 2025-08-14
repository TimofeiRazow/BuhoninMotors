# app/utils/exceptions.py
"""
Кастомные исключения для приложения
"""

# app/utils/exceptions.py
"""
Пользовательские исключения для API
"""


class APIException(Exception):
    """Базовое исключение для API"""
    
    def __init__(self, message, status_code=400, payload=None):
        super().__init__()
        self.message = message
        self.status_code = status_code
        self.payload = payload
    
    def to_dict(self):
        rv = dict(self.payload or ())
        rv['error'] = self.message
        return rv


class ValidationError(APIException):
    """Ошибка валидации данных"""
    
    def __init__(self, message, payload=None):
        super().__init__(message, 400, payload)


class AuthenticationError(APIException):
    """Ошибка аутентификации"""
    
    def __init__(self, message="Authentication required"):
        super().__init__(message, 401)


class AuthorizationError(APIException):
    """Ошибка авторизации"""
    
    def __init__(self, message="Access denied"):
        super().__init__(message, 403)


class NotFoundError(APIException):
    """Ошибка "не найдено" """
    
    def __init__(self, message="Resource not found"):
        super().__init__(message, 404)


class ConflictError(APIException):
    """Ошибка конфликта (например, дублирование данных)"""
    
    def __init__(self, message="Resource already exists"):
        super().__init__(message, 409)


class RateLimitError(APIException):
    """Ошибка превышения лимита запросов"""
    
    def __init__(self, message="Rate limit exceeded"):
        super().__init__(message, 429)


class InternalServerError(APIException):
    """Внутренняя ошибка сервера"""
    
    def __init__(self, message="Internal server error"):
        super().__init__(message, 500)

class BaseAppException(Exception):
    """Базовое исключение приложения"""
    def __init__(self, message="Application error", code=500):
        self.message = message
        self.code = code
        super().__init__(self.message)


class ValidationError(BaseAppException):
    """Ошибка валидации данных"""
    def __init__(self, message="Validation error", field=None):
        self.field = field
        super().__init__(message, 400)


class AuthenticationError(BaseAppException):
    """Ошибка аутентификации"""
    def __init__(self, message="Authentication failed"):
        super().__init__(message, 401)


class AuthorizationError(BaseAppException):
    """Ошибка авторизации"""
    def __init__(self, message="Access denied"):
        super().__init__(message, 403)


class NotFoundError(BaseAppException):
    """Ресурс не найден"""
    def __init__(self, message="Resource not found", resource=None):
        self.resource = resource
        super().__init__(message, 404)


class ConflictError(BaseAppException):
    """Конфликт данных"""
    def __init__(self, message="Data conflict"):
        super().__init__(message, 409)


class RateLimitError(BaseAppException):
    """Превышен лимит запросов"""
    def __init__(self, message="Rate limit exceeded"):
        super().__init__(message, 429)


class InternalServerError(BaseAppException):
    """Внутренняя ошибка сервера"""
    def __init__(self, message="Internal server error"):
        super().__init__(message, 500)


class ServiceUnavailableError(BaseAppException):
    """Сервис недоступен"""
    def __init__(self, message="Service unavailable"):
        super().__init__(message, 503)


# Специфичные исключения для доменов

class UserNotFoundError(NotFoundError):
    """Пользователь не найден"""
    def __init__(self, user_id=None):
        message = f"User {user_id} not found" if user_id else "User not found"
        super().__init__(message, "user")


class ListingNotFoundError(NotFoundError):
    """Объявление не найдено"""
    def __init__(self, listing_id=None):
        message = f"Listing {listing_id} not found" if listing_id else "Listing not found"
        super().__init__(message, "listing")


class InvalidPhoneNumberError(ValidationError):
    """Некорректный номер телефона"""
    def __init__(self, phone_number=None):
        message = f"Invalid phone number: {phone_number}" if phone_number else "Invalid phone number"
        super().__init__(message, "phone_number")


class PhoneAlreadyExistsError(ConflictError):
    """Телефон уже зарегистрирован"""
    def __init__(self, phone_number=None):
        message = f"Phone number {phone_number} already exists" if phone_number else "Phone number already exists"
        super().__init__(message)


class EmailAlreadyExistsError(ConflictError):
    """Email уже зарегистрирован"""
    def __init__(self, email=None):
        message = f"Email {email} already exists" if email else "Email already exists"
        super().__init__(message)


class InvalidCredentialsError(AuthenticationError):
    """Неверные учетные данные"""
    def __init__(self):
        super().__init__("Invalid credentials")


class TokenExpiredError(AuthenticationError):
    """Токен истек"""
    def __init__(self):
        super().__init__("Token has expired")


class InvalidTokenError(AuthenticationError):
    """Невалидный токен"""
    def __init__(self):
        super().__init__("Invalid token")


class VerificationCodeError(ValidationError):
    """Ошибка кода верификации"""
    def __init__(self, message="Invalid verification code"):
        super().__init__(message, "verification_code")


class FileUploadError(ValidationError):
    """Ошибка загрузки файла"""
    def __init__(self, message="File upload error"):
        super().__init__(message, "file")


class FileTooLargeError(FileUploadError):
    """Файл слишком большой"""
    def __init__(self, max_size=None):
        message = f"File too large. Maximum size: {max_size}" if max_size else "File too large"
        super().__init__(message)


class UnsupportedFileTypeError(FileUploadError):
    """Неподдерживаемый тип файла"""
    def __init__(self, file_type=None):
        message = f"Unsupported file type: {file_type}" if file_type else "Unsupported file type"
        super().__init__(message)


class PaymentError(BaseAppException):
    """Ошибка платежа"""
    def __init__(self, message="Payment error"):
        super().__init__(message, 402)


class PaymentFailedError(PaymentError):
    """Платеж не прошел"""
    def __init__(self, reason=None):
        message = f"Payment failed: {reason}" if reason else "Payment failed"
        super().__init__(message)


class InsufficientFundsError(PaymentError):
    """Недостаточно средств"""
    def __init__(self):
        super().__init__("Insufficient funds")


class BusinessLogicError(BaseAppException):
    """Ошибка бизнес-логики"""
    def __init__(self, message="Business logic error"):
        super().__init__(message, 422)


class ListingExpiredError(BusinessLogicError):
    """Объявление истекло"""
    def __init__(self):
        super().__init__("Listing has expired")


class ListingNotActiveError(BusinessLogicError):
    """Объявление не активно"""
    def __init__(self):
        super().__init__("Listing is not active")


class UserNotVerifiedError(BusinessLogicError):
    """Пользователь не верифицирован"""
    def __init__(self):
        super().__init__("User is not verified")


class MaxListingsReachedError(BusinessLogicError):
    """Достигнут лимит объявлений"""
    def __init__(self, max_listings=None):
        message = f"Maximum listings reached: {max_listings}" if max_listings else "Maximum listings reached"
        super().__init__(message)


# Утилитарные функции для работы с исключениями
def handle_db_error(error):
    """Обработка ошибок базы данных"""
    from sqlalchemy.exc import IntegrityError, DataError
    
    if isinstance(error, IntegrityError):
        if 'unique' in str(error).lower():
            return ConflictError("Data already exists")
        else:
            return ConflictError("Data integrity error")
    elif isinstance(error, DataError):
        return ValidationError("Invalid data format")
    else:
        return InternalServerError("Database error")


def format_validation_error(errors):
    """Форматирование ошибок валидации Marshmallow"""
    formatted_errors = {}
    
    for field, messages in errors.items():
        if isinstance(messages, list):
            formatted_errors[field] = messages[0]  # Берем первую ошибку
        else:
            formatted_errors[field] = str(messages)
    
    return formatted_errors