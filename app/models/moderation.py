# app/models/moderation.py
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, DECIMAL, Index
from sqlalchemy.dialects.postgresql import JSONB
from app.models.base import BaseModel
from app.extensions import db


class ModerationQueue(BaseModel):
    """Модель очереди модерации"""
    __tablename__ = 'moderation_queue'
    
    moderation_id = Column(Integer, primary_key=True)
    entity_id = Column(Integer, ForeignKey('global_entities.entity_id'), nullable=False)
    user_id = Column(Integer, ForeignKey('users.user_id'), nullable=False)
    moderator_id = Column(Integer, ForeignKey('users.user_id'))
    status_id = Column(Integer, ForeignKey('statuses.status_id'), nullable=False)
    priority = Column(Integer, default=0)
    rejection_reason = Column(Text)
    submitted_date = Column(DateTime, default=datetime.utcnow)
    moderated_date = Column(DateTime)
    notes = Column(Text)
    auto_moderation_score = Column(DECIMAL(5, 2))
    
    __table_args__ = (
        Index('idx_moderation_status_priority', 'status_id', 'priority', 'submitted_date'),
        Index('idx_moderation_user', 'user_id', 'submitted_date'),
    )
    
    # Отношения
    entity = db.relationship('GlobalEntity', backref='moderation_items')
    user = db.relationship('User', foreign_keys=[user_id], backref='submitted_for_moderation')
    moderator = db.relationship('User', foreign_keys=[moderator_id], backref='moderated_items')
    status = db.relationship('Status')
    
    def approve(self, moderator_id, notes=None):
        """Одобрение контента"""
        from app.models.base import get_status_by_code
        
        approved_status = get_status_by_code('moderation_status', 'approved')
        self.status_id = approved_status.status_id
        self.moderator_id = moderator_id
        self.moderated_date = datetime.utcnow()
        self.notes = notes
        self.save()
    
    def reject(self, moderator_id, reason, notes=None):
        """Отклонение контента"""
        from app.models.base import get_status_by_code
        
        rejected_status = get_status_by_code('moderation_status', 'rejected')
        self.status_id = rejected_status.status_id
        self.moderator_id = moderator_id
        self.rejection_reason = reason
        self.moderated_date = datetime.utcnow()
        self.notes = notes
        self.save()
    
    def to_dict(self):
        """Преобразование в словарь"""
        return {
            'moderation_id': self.moderation_id,
            'entity_id': self.entity_id,
            'user_id': self.user_id,
            'user_name': self.user.full_name if self.user else None,
            'moderator_id': self.moderator_id,
            'moderator_name': self.moderator.full_name if self.moderator else None,
            'status': self.status.status_name if self.status else None,
            'priority': self.priority,
            'rejection_reason': self.rejection_reason,
            'submitted_date': self.submitted_date.isoformat() if self.submitted_date else None,
            'moderated_date': self.moderated_date.isoformat() if self.moderated_date else None,
            'notes': self.notes,
            'auto_moderation_score': float(self.auto_moderation_score) if self.auto_moderation_score else None
        }


class ReportedContent(BaseModel):
    """Модель жалоб на контент"""
    __tablename__ = 'reported_content'
    
    report_id = Column(Integer, primary_key=True)
    reporter_id = Column(Integer, ForeignKey('users.user_id'), nullable=False)
    entity_id = Column(Integer, ForeignKey('global_entities.entity_id'), nullable=False)
    report_reason = Column(String(50), nullable=False)
    description = Column(Text)
    status_id = Column(Integer, ForeignKey('statuses.status_id'), nullable=False)
    resolved_date = Column(DateTime)
    resolved_by = Column(Integer, ForeignKey('users.user_id'))
    resolution_notes = Column(Text)
    
    __table_args__ = (
        Index('idx_reports_status', 'status_id', 'created_date'),
    )
    
    # Отношения
    reporter = db.relationship('User', foreign_keys=[reporter_id], backref='submitted_reports')
    entity = db.relationship('GlobalEntity', backref='reports')
    resolver = db.relationship('User', foreign_keys=[resolved_by])
    status = db.relationship('Status')
    
    def resolve(self, resolver_id, notes=None):
        """Разрешение жалобы"""
        from app.models.base import get_status_by_code
        
        resolved_status = get_status_by_code('report_status', 'resolved')
        self.status_id = resolved_status.status_id
        self.resolved_by = resolver_id
        self.resolved_date = datetime.utcnow()
        self.resolution_notes = notes
        self.save()
    
    def to_dict(self):
        """Преобразование в словарь"""
        return {
            'report_id': self.report_id,
            'reporter_id': self.reporter_id,
            'reporter_name': self.reporter.full_name if self.reporter else None,
            'entity_id': self.entity_id,
            'report_reason': self.report_reason,
            'description': self.description,
            'status': self.status.status_name if self.status else None,
            'created_date': self.created_date.isoformat() if self.created_date else None,
            'resolved_date': self.resolved_date.isoformat() if self.resolved_date else None,
            'resolver_name': self.resolver.full_name if self.resolver else None,
            'resolution_notes': self.resolution_notes
        }