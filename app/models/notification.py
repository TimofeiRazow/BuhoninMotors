# app/models/notification.py
"""
Модели для системы уведомлений
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship, backref
from sqlalchemy.dialects.postgresql import JSONB

from app.models.base import BaseModel
from app.database import Base, TimestampMixin, db


class NotificationChannel(BaseModel):
    """Каналы уведомлений (push, email, sms, in_app)"""
    __tablename__ = 'notification_channels'
    
    channel_id = Column(Integer, primary_key=True)
    channel_code = Column(String(20), unique=True, nullable=False)
    channel_name = Column(String(50), nullable=False)
    is_active = Column(Boolean, default=True)
    settings = Column(JSONB, default={})
    
    # Relationships - использование строк для отложенной инициализации
    templates = relationship('NotificationTemplate', back_populates='channel')
    notifications = relationship('Notification', back_populates='channel')
    user_settings = relationship('UserNotificationSettings', back_populates='channel')
    
    def __repr__(self):
        return f'<NotificationChannel {self.channel_code}>'


class NotificationTemplate(BaseModel):
    """Шаблоны уведомлений"""
    __tablename__ = 'notification_templates'
    
    template_id = Column(Integer, primary_key=True)
    template_code = Column(String(100), unique=True, nullable=False)
    template_name = Column(String(255), nullable=False)
    channel_id = Column(Integer, ForeignKey('notification_channels.channel_id'), nullable=False)
    subject_template = Column(Text)
    body_template = Column(Text, nullable=False)
    variables = Column(JSONB, default={})
    is_active = Column(Boolean, default=True)
    
    # Relationships
    channel = relationship('NotificationChannel', back_populates='templates')
    notifications = relationship('Notification', back_populates='template')
    
    def render_subject(self, variables):
        """Рендеринг заголовка с переменными"""
        if not self.subject_template:
            return None
        
        try:
            return self.subject_template.format(**variables)
        except (KeyError, ValueError):
            return self.subject_template
    
    def render_body(self, variables):
        """Рендеринг тела сообщения с переменными"""
        try:
            return self.body_template.format(**variables)
        except (KeyError, ValueError):
            return self.body_template
    
    def __repr__(self):
        return f'<NotificationTemplate {self.template_code}>'


class UserNotificationSettings(BaseModel, TimestampMixin):
    """Настройки уведомлений пользователей"""
    __tablename__ = 'user_notification_settings'
    
    user_id = Column(Integer, ForeignKey('users.user_id'), primary_key=True)
    channel_id = Column(Integer, ForeignKey('notification_channels.channel_id'), primary_key=True)
    notification_type = Column(String(50), primary_key=True)
    is_enabled = Column(Boolean, default=True)
    frequency = Column(String(20), default='instant')  # instant, daily, weekly, never
    
    # Связи - используем строки для отложенной инициализации
    user = relationship("User", back_populates="notification_settings")
    channel = relationship("NotificationChannel", back_populates="user_settings")
    
    def __repr__(self):
        return f"<UserNotificationSettings {self.user_id}:{self.notification_type}>"


class Notification(BaseModel):
    """Уведомления пользователей"""
    __tablename__ = 'notifications'
    
    notification_id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.user_id'), nullable=False)
    channel_id = Column(Integer, ForeignKey('notification_channels.channel_id'), nullable=False)
    template_id = Column(Integer, ForeignKey('notification_templates.template_id'))
    title = Column(String(255))
    message = Column(Text, nullable=False)
    notification_type = Column(String(50))
    related_entity_id = Column(Integer, ForeignKey('global_entities.entity_id'))
    template_data = Column(JSONB, default={})
    status = Column(String(20), default='pending')  # pending, sent, delivered, failed, opened
    scheduled_date = Column(DateTime, default=datetime.utcnow)
    sent_date = Column(DateTime)
    opened_date = Column(DateTime)
    attempts_count = Column(Integer, default=0)
    error_message = Column(Text)
    external_id = Column(String(255))
    
    # Relationships
    user = relationship('User', backref=backref('notifications', lazy='dynamic'))
    channel = relationship('NotificationChannel', back_populates='notifications')
    template = relationship('NotificationTemplate', back_populates='notifications')
    related_entity = relationship('GlobalEntity', foreign_keys=[related_entity_id])
    
    @property
    def is_read(self):
        """Проверка, прочитано ли уведомление"""
        return self.status == 'opened' and self.opened_date is not None
    
    @property
    def is_sent(self):
        """Проверка, отправлено ли уведомление"""
        return self.status in ['sent', 'delivered', 'opened']
    
    def mark_as_read(self):
        """Отметить уведомление как прочитанное"""
        if self.status in ['sent', 'delivered']:
            self.status = 'opened'
            self.opened_date = datetime.utcnow()
    
    def mark_as_sent(self):
        """Отметить уведомление как отправленное"""
        self.status = 'sent'
        self.sent_date = datetime.utcnow()
    
    def mark_as_failed(self, error_message=None):
        """Отметить уведомление как неудачное"""
        self.status = 'failed'
        self.error_message = error_message
        self.attempts_count += 1
    
    def __repr__(self):
        return f'<Notification {self.notification_id}: {self.title}>'