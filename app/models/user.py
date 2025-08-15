# app/models/user.py
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, DECIMAL, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, INET
from flask_jwt_extended import create_access_token, create_refresh_token
from app.models.base import BaseModel, EntityBasedModel
from app.extensions import db


class User(EntityBasedModel):
    """Модель пользователя"""
    __tablename__ = 'users'
    
    user_id = Column(Integer, primary_key=True)
    phone_number = Column(String(20), unique=True, nullable=False)
    email = Column(String(255), unique=True, nullable=True)
    password_hash = Column(String(255), nullable=False)
    first_name = Column(String(100))
    last_name = Column(String(100))
    registration_date = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime)
    verification_status = Column(String(20), default='pending')
    user_type = Column(String(20), default='regular')

    support_tickets = db.relationship("SupportTicket", foreign_keys="SupportTicket.user_id", back_populates="user")
    assigned_tickets = db.relationship("SupportTicket", foreign_keys="SupportTicket.assigned_to", back_populates="assigned_user")
    # Add this to your User model
    notification_settings = db.relationship("UserNotificationSettings", back_populates="user")
    
    __table_args__ = (
        db.CheckConstraint(
            "verification_status IN ('pending', 'phone_verified', 'email_verified', 'fully_verified')",
            name='check_verification_status'
        ),
        db.CheckConstraint(
            "user_type IN ('regular', 'pro', 'dealer', 'admin')",
            name='check_user_type'
        ),
        # Уникальные индексы только для активных пользователей
        db.Index('idx_users_phone_active', 'phone_number', postgresql_where=db.text('is_active = true')),
        db.Index('idx_users_email_active', 'email', postgresql_where=db.text('is_active = true AND email IS NOT NULL')),
    )
    
    def set_password(self, password):
        """Установка пароля с хешированием"""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Проверка пароля"""
        return check_password_hash(self.password_hash, password)
    
    def generate_tokens(self):
        """Генерация JWT токенов"""
        additional_claims = {
            'user_type': self.user_type,
            'is_verified': self.verification_status == 'fully_verified'
        }
        
        access_token = create_access_token(
            identity=self.user_id,
            additional_claims=additional_claims
        )
        refresh_token = create_refresh_token(identity=self.user_id)
        
        return {
            'access_token': access_token,
            'refresh_token': refresh_token
        }
    
    def update_last_login(self):
        """Обновление времени последнего входа"""
        self.last_login = datetime.utcnow()
        db.session.commit()
    
    def verify_phone(self):
        """Верификация телефона"""
        if self.verification_status == 'pending':
            self.verification_status = 'phone_verified'
        elif self.verification_status == 'email_verified':
            self.verification_status = 'fully_verified'
        db.session.commit()
    
    def verify_email(self):
        """Верификация email"""
        if self.verification_status == 'pending':
            self.verification_status = 'email_verified'
        elif self.verification_status == 'phone_verified':
            self.verification_status = 'fully_verified'
        db.session.commit()
    
    @property
    def full_name(self):
        """Полное имя пользователя"""
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.first_name or self.last_name or ""
    
    @property
    def is_verified(self):
        """Проверка верификации пользователя"""
        return self.verification_status == 'fully_verified'
    
    @property
    def is_pro_user(self):
        """Проверка PRO статуса"""
        return self.user_type in ['pro', 'dealer']
    
    @classmethod
    def find_by_phone(cls, phone_number):
        """Поиск пользователя по телефону"""
        return cls.query.filter(
            cls.phone_number == phone_number,
            cls.is_active == True
        ).first()
    
    @classmethod
    def find_by_email(cls, email):
        """Поиск пользователя по email"""
        return cls.query.filter(
            cls.email == email,
            cls.is_active == True
        ).first()
    
    def to_dict(self, include_sensitive=False):
        """Преобразование в словарь с возможностью исключения чувствительных данных"""
        data = {
            'user_id': self.user_id,
            'phone_number': self.phone_number,
            'email': self.email,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'full_name': self.full_name,
            'user_type': self.user_type,
            'verification_status': self.verification_status,
            'is_verified': self.is_verified,
            'registration_date': self.registration_date.isoformat() if self.registration_date else None,
            'last_login': self.last_login.isoformat() if self.last_login else None
        }
        
        if include_sensitive:
            data.update({
                'entity_id': self.entity_id,
                'is_active': self.is_active
            })
        
        return data
    
    def __repr__(self):
        return f'<User {self.phone_number}>'


class UserProfile(BaseModel):
    """Профиль пользователя"""
    __tablename__ = 'user_profiles'
    
    profile_id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.user_id'), unique=True, nullable=False)
    company_name = Column(String(255))
    address = Column(Text)
    city_id = Column(Integer, ForeignKey('cities.city_id'))
    avatar_url = Column(String(500))
    description = Column(Text)
    website = Column(String(255))
    business_hours = Column(JSONB)
    verification_documents = Column(JSONB)
    rating_average = Column(DECIMAL(3, 2), default=0)
    reviews_count = Column(Integer, default=0)
    
    # Отношения
    user = db.relationship('User', backref=db.backref('profile', uselist=False))
    city = db.relationship('City', backref='user_profiles')
    
    @property
    def rating_stars(self):
        """Рейтинг в звездах (округленный)"""
        return round(float(self.rating_average)) if self.rating_average else 0
    
    def update_rating(self):
        """Обновление рейтинга на основе отзывов"""
        from app.models.review import UserReview
        
        reviews = UserReview.query.filter(
            UserReview.reviewed_user_id == self.user_id,
            UserReview.is_public == True
        ).all()
        
        if reviews:
            self.rating_average = sum(review.rating for review in reviews) / len(reviews)
            self.reviews_count = len(reviews)
        else:
            self.rating_average = 0
            self.reviews_count = 0
        
        db.session.commit()
    
    def to_dict(self):
        """Преобразование в словарь"""
        return {
            'profile_id': self.profile_id,
            'user_id': self.user_id,
            'company_name': self.company_name,
            'address': self.address,
            'city_id': self.city_id,
            'city_name': self.city.city_name if self.city else None,
            'avatar_url': self.avatar_url,
            'description': self.description,
            'website': self.website,
            'business_hours': self.business_hours,
            'rating_average': float(self.rating_average) if self.rating_average else 0,
            'rating_stars': self.rating_stars,
            'reviews_count': self.reviews_count
        }


class UserSettings(BaseModel):
    """Настройки пользователя"""
    __tablename__ = 'user_settings'
    
    user_id = Column(Integer, ForeignKey('users.user_id'), primary_key=True)
    notifications_enabled = Column(Boolean, default=True)
    email_notifications = Column(Boolean, default=True)
    sms_notifications = Column(Boolean, default=False)
    push_notifications = Column(Boolean, default=True)
    auto_renewal_enabled = Column(Boolean, default=False)
    privacy_settings = Column(JSONB, default={})
    preferred_language = Column(String(10), default='ru')
    timezone = Column(String(50), default='Asia/Almaty')
    
    # Отношения
    user = db.relationship('User', backref=db.backref('settings', uselist=False))
    
    def to_dict(self):
        """Преобразование в словарь"""
        return {
            'user_id': self.user_id,
            'notifications_enabled': self.notifications_enabled,
            'email_notifications': self.email_notifications,
            'sms_notifications': self.sms_notifications,
            'push_notifications': self.push_notifications,
            'auto_renewal_enabled': self.auto_renewal_enabled,
            'privacy_settings': self.privacy_settings,
            'preferred_language': self.preferred_language,
            'timezone': self.timezone
        }


class DeviceRegistration(BaseModel):
    """Регистрация устройств для push-уведомлений"""
    __tablename__ = 'device_registration'
    
    device_id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.user_id'), nullable=False)
    device_token = Column(String(500), nullable=False)
    device_type = Column(String(20), nullable=False)
    device_model = Column(String(100))
    os_version = Column(String(50))
    app_version = Column(String(50))
    registration_date = Column(DateTime, default=datetime.utcnow)
    last_active_date = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        db.CheckConstraint(
            "device_type IN ('ios', 'android', 'web')",
            name='check_device_type'
        ),
    )
    
    # Отношения
    user = db.relationship('User', backref='devices')
    
    def update_activity(self):
        """Обновление времени последней активности"""
        self.last_active_date = datetime.utcnow()
        db.session.commit()
    
    @classmethod
    def get_user_devices(cls, user_id, device_type=None):
        """Получение активных устройств пользователя"""
        query = cls.query.filter(
            cls.user_id == user_id,
            cls.is_active == True
        )
        
        if device_type:
            query = query.filter(cls.device_type == device_type)
        
        return query.all()


class PhoneVerification(BaseModel):
    """Верификация телефонов"""
    __tablename__ = 'phone_verification'
    
    verification_id = Column(Integer, primary_key=True)
    phone_number = Column(String(20), nullable=False)
    verification_code = Column(String(10), nullable=False)
    expires_at = Column(DateTime, nullable=False)
    verified_at = Column(DateTime)
    attempts_count = Column(Integer, default=0)
    ip_address = Column(INET)
    
    @classmethod
    def create_verification(cls, phone_number, code, ip_address=None):
        """Создание новой верификации"""
        # Деактивируем старые коды для этого номера
        cls.query.filter(
            cls.phone_number == phone_number,
            cls.verified_at.is_(None)
        ).update({'is_active': False})
        
        verification = cls(
            phone_number=phone_number,
            verification_code=code,
            expires_at=datetime.utcnow() + timedelta(minutes=5),
            ip_address=ip_address
        )
        verification.save()
        return verification
    
    @classmethod
    def verify_code(cls, phone_number, code):
        """Проверка кода верификации"""
        verification = cls.query.filter(
            cls.phone_number == phone_number,
            cls.verification_code == code,
            cls.expires_at > datetime.utcnow(),
            cls.verified_at.is_(None),
            cls.is_active == True
        ).first()
        
        if verification:
            verification.verified_at = datetime.utcnow()
            verification.save()
            return True
        
        return False
    
    def increment_attempts(self):
        """Увеличение счетчика попыток"""
        self.attempts_count += 1
        if self.attempts_count >= 3:
            self.is_active = False
        self.save()


class EmailVerification(BaseModel):
    """Верификация email"""
    __tablename__ = 'email_verification'
    
    verification_id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.user_id'), nullable=False)
    email_address = Column(String(255), nullable=False)
    verification_token = Column(String(255), nullable=False)
    expires_at = Column(DateTime, nullable=False)
    verified_at = Column(DateTime)
    
    # Отношения
    user = db.relationship('User', backref='email_verifications')
    
    @classmethod
    def create_verification(cls, user_id, email, token):
        """Создание новой верификации email"""
        verification = cls(
            user_id=user_id,
            email_address=email,
            verification_token=token,
            expires_at=datetime.utcnow() + timedelta(hours=24)
        )
        verification.save()
        return verification
    
    @classmethod
    def verify_token(cls, token):
        """Проверка токена верификации"""
        verification = cls.query.filter(
            cls.verification_token == token,
            cls.expires_at > datetime.utcnow(),
            cls.verified_at.is_(None),
            cls.is_active == True
        ).first()
        
        if verification:
            verification.verified_at = datetime.utcnow()
            verification.save()
            return verification.user
        
        return None


class UserSession(BaseModel):
    """Сессии пользователей"""
    __tablename__ = 'user_sessions'
    
    session_id = Column(String(255), primary_key=True)
    user_id = Column(Integer, ForeignKey('users.user_id'), nullable=False)
    ip_address = Column(INET)
    user_agent = Column(Text)
    last_activity = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)
    
    # Отношения
    user = db.relationship('User', backref='sessions')
    
    @classmethod
    def create_session(cls, session_id, user_id, ip_address=None, user_agent=None):
        """Создание новой сессии"""
        session = cls(
            session_id=session_id,
            user_id=user_id,
            ip_address=ip_address,
            user_agent=user_agent,
            expires_at=datetime.utcnow() + timedelta(days=30)
        )
        session.save()
        return session
    
    def update_activity(self):
        """Обновление активности сессии"""
        self.last_activity = datetime.utcnow()
        self.save()
    
    def is_expired(self):
        """Проверка истечения сессии"""
        return datetime.utcnow() > self.expires_at


class LoginAttempt(BaseModel):
    """Попытки входа"""
    __tablename__ = 'login_attempts'
    
    attempt_id = Column(Integer, primary_key=True)
    phone_number = Column(String(20))
    email = Column(String(255))
    ip_address = Column(INET, nullable=False)
    success = Column(Boolean, nullable=False)
    attempted_at = Column(DateTime, default=datetime.utcnow)
    user_agent = Column(Text)
    failure_reason = Column(String(100))
    
    @classmethod
    def log_attempt(cls, identifier, ip_address, success, user_agent=None, failure_reason=None):
        """Логирование попытки входа"""
        # Определяем тип идентификатора (телефон или email)
        if '@' in identifier:
            email = identifier
            phone_number = None
        else:
            phone_number = identifier
            email = None
        
        attempt = cls(
            phone_number=phone_number,
            email=email,
            ip_address=ip_address,
            success=success,
            user_agent=user_agent,
            failure_reason=failure_reason
        )
        attempt.save()
        return attempt
    
    @classmethod
    def check_rate_limit(cls, ip_address, minutes=15, max_attempts=5):
        """Проверка лимита попыток с IP"""
        since = datetime.utcnow() - timedelta(minutes=minutes)
        attempts = cls.query.filter(
            cls.ip_address == ip_address,
            cls.attempted_at >= since,
            cls.success == False
        ).count()
        
        return attempts < max_attempts


class RevokedToken(BaseModel):
    """Отозванные JWT токены"""
    __tablename__ = 'revoked_tokens'
    
    id = Column(Integer, primary_key=True)
    jti = Column(String(120), unique=True, nullable=False)
    user_id = Column(Integer, ForeignKey('users.user_id'), nullable=False)
    revoked_at = Column(DateTime, default=datetime.utcnow)
    
    # Отношения
    user = db.relationship('User', backref='revoked_tokens')
    
    @classmethod
    def is_jti_blacklisted(cls, jti):
        """Проверка токена в черном списке"""
        return cls.query.filter(cls.jti == jti).first() is not None
    
    @classmethod
    def revoke_token(cls, jti, user_id):
        """Отзыв токена"""
        revoked_token = cls(jti=jti, user_id=user_id)
        revoked_token.save()
        return revoked_token