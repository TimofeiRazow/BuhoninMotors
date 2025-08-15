# app/blueprints/auth/schemas.py
from marshmallow import Schema, fields, validate, validates, ValidationError, validates_schema
from app.utils.helpers import normalize_phone_number, validate_email_address


class RegisterSchema(Schema):
    """Схема для регистрации пользователя"""
    phone_number = fields.Str(required=True, validate=validate.Length(min=10, max=20))
    email = fields.Email(required=False, allow_none=True)
    password = fields.Str(required=True, validate=validate.Length(min=6, max=100))
    first_name = fields.Str(required=False, validate=validate.Length(max=100))
    last_name = fields.Str(required=False, validate=validate.Length(max=100))
    
    @validates('phone_number')
    def validate_phone_number(self, value):
        try:
            normalize_phone_number(value)
        except ValueError as e:
            raise ValidationError(str(e))
    
    @validates('email')
    def validate_email(self, value):
        if value:
            try:
                validate_email_address(value)
            except ValueError as e:
                raise ValidationError(str(e))

class LoginSchema(Schema):
    """Схема для входа пользователя"""
    identifier = fields.Str(required=False, validate=validate.Length(min=3, max=255))
    password = fields.Str(required=True, validate=validate.Length(min=1, max=100))
    phone_number = fields.Str(required=False)
    remember_me = fields.Bool(required=False, default=False)
    @validates('phone_number')
    def validate_phone_number(self, value):
        try:
            normalize_phone_number(value)
        except ValueError as e:
            raise ValidationError(str(e))

class VerifyPhoneSchema(Schema):
    """Схема для верификации телефона"""
    phone_number = fields.Str(required=True, validate=validate.Length(min=10, max=20))
    verification_code = fields.Str(required=True, validate=validate.Length(min=4, max=10))
    
    @validates('phone_number')
    def validate_phone_number(self, value):
        try:
            normalize_phone_number(value)
        except ValueError as e:
            raise ValidationError(str(e))


class SendVerificationCodeSchema(Schema):
    """Схема для отправки кода верификации"""
    phone_number = fields.Str(required=True, validate=validate.Length(min=10, max=20))
    
    @validates('phone_number')
    def validate_phone_number(self, value):
        try:
            normalize_phone_number(value)
        except ValueError as e:
            raise ValidationError(str(e))


class VerifyEmailSchema(Schema):
    """Схема для верификации email"""
    token = fields.Str(required=True, validate=validate.Length(min=10, max=500))


class ResetPasswordSchema(Schema):
    """Схема для сброса пароля"""
    identifier = fields.Str(required=True, validate=validate.Length(min=3, max=255))


class ChangePasswordSchema(Schema):
    """Схема для смены пароля"""
    current_password = fields.Str(required=True, validate=validate.Length(min=1, max=100))
    new_password = fields.Str(required=True, validate=validate.Length(min=6, max=100))
    confirm_password = fields.Str(required=True, validate=validate.Length(min=6, max=100))
    
    @validates('confirm_password')
    def validate_passwords_match(self, value):
        if 'new_password' in self.context and value != self.context['new_password']:
            raise ValidationError("Passwords do not match")


class RefreshTokenSchema(Schema):
    """Схема для обновления токена"""
    refresh_token = fields.Str(required=True)

