# app/models/support.py
"""
Модели для системы поддержки
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime

from app.models.base import BaseModel


class SupportTicket(BaseModel):
    """Модель тикета поддержки"""
    __tablename__ = 'support_tickets'
    
    ticket_id = Column(Integer, primary_key=True, autoincrement=True)
    entity_id = Column(Integer, ForeignKey('global_entities.entity_id'), nullable=False)
    user_id = Column(Integer, ForeignKey('users.user_id'), nullable=False)
    category_id = Column(Integer, ForeignKey('categories.category_id'), nullable=True)
    priority = Column(String(20), nullable=False, default='medium')  # low, medium, high, critical
    subject = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    status_id = Column(Integer, nullable=False, default=1)  # 1-открыт, 2-в работе, 3-решен, 4-закрыт, 5-отклонен
    assigned_to = Column(Integer, ForeignKey('users.user_id'), nullable=True)
    created_date = Column(DateTime, nullable=False, default=datetime.utcnow)
    first_response_date = Column(DateTime, nullable=True)
    resolved_date = Column(DateTime, nullable=True)
    customer_satisfaction = Column(Integer, nullable=True)  # 1-5 оценка удовлетворенности
    
    # Relationships
    entity = relationship("GlobalEntity", back_populates="support_tickets")
    user = relationship("User", foreign_keys=[user_id], back_populates="support_tickets")
    assigned_user = relationship("User", foreign_keys=[assigned_to], back_populates="assigned_tickets")
    category = relationship("Category", back_populates="support_tickets")
    
    def __repr__(self):
        return f'<SupportTicket {self.ticket_id}: {self.subject}>'
    
    @property
    def status_name(self):
        """Возвращает название статуса"""
        status_map = {
            1: 'Открыт',
            2: 'В работе',
            3: 'Решен',
            4: 'Закрыт',
            5: 'Отклонен'
        }
        return status_map.get(self.status_id, 'Неизвестно')
    
    @property
    def priority_level(self):
        """Возвращает числовой уровень приоритета для сортировки"""
        priority_map = {
            'low': 1,
            'medium': 2,
            'high': 3,
            'critical': 4
        }
        return priority_map.get(self.priority, 2)
    
    @property
    def is_open(self):
        """Проверяет, открыт ли тикет"""
        return self.status_id in [1, 2]
    
    @property
    def is_resolved(self):
        """Проверяет, решен ли тикет"""
        return self.status_id in [3, 4]


class SupportCategory(BaseModel):
    """Модель категории поддержки (если нужна отдельная от общих категорий)"""
    __tablename__ = 'support_categories'
    
    category_id = Column(Integer, primary_key=True, autoincrement=True)
    entity_id = Column(Integer, ForeignKey('global_entities.entity_id'), nullable=False)
    category_name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    parent_category_id = Column(Integer, ForeignKey('support_categories.category_id'), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    sort_order = Column(Integer, nullable=False, default=0)
    created_date = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    # Relationships
    entity = relationship("GlobalEntity")
    parent_category = relationship("SupportCategory", remote_side=[category_id])
    tickets = relationship("SupportTicket", back_populates="support_category")
    
    def __repr__(self):
        return f'<SupportCategory {self.category_id}: {self.category_name}>'


class TicketResponse(BaseModel):
    """Модель ответа на тикет (связана с сообщениями)"""
    __tablename__ = 'ticket_responses'
    
    response_id = Column(Integer, primary_key=True, autoincrement=True)
    entity_id = Column(Integer, ForeignKey('global_entities.entity_id'), nullable=False)
    ticket_id = Column(Integer, ForeignKey('support_tickets.ticket_id'), nullable=False)
    message_id = Column(Integer, ForeignKey('messages.message_id'), nullable=False)
    user_id = Column(Integer, ForeignKey('users.user_id'), nullable=False)
    is_internal = Column(Boolean, nullable=False, default=False)  # внутренняя заметка для админов
    created_date = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    # Relationships
    entity = relationship("GlobalEntity")
    ticket = relationship("SupportTicket", back_populates="responses")
    message = relationship("Message")
    user = relationship("User")
    
    def __repr__(self):
        return f'<TicketResponse {self.response_id} for ticket {self.ticket_id}>'


class SupportFAQ(BaseModel):
    """Модель FAQ"""
    __tablename__ = 'support_faq'
    
    faq_id = Column(Integer, primary_key=True, autoincrement=True)
    entity_id = Column(Integer, ForeignKey('global_entities.entity_id'), nullable=False)
    category_id = Column(Integer, ForeignKey('support_categories.category_id'), nullable=True)
    question = Column(String(500), nullable=False)
    answer = Column(Text, nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)
    sort_order = Column(Integer, nullable=False, default=0)
    view_count = Column(Integer, nullable=False, default=0)
    created_date = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_date = Column(DateTime, nullable=True)
    
    # Relationships
    entity = relationship("GlobalEntity")
    category = relationship("SupportCategory")
    
    def __repr__(self):
        return f'<SupportFAQ {self.faq_id}: {self.question[:50]}...>'