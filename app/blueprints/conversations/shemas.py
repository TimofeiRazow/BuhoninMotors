# app/models/conversation.py (дополнение к существующим моделям)
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, Index
from sqlalchemy.dialects.postgresql import JSONB
from app.models.base import BaseModel, EntityBasedModel
from app.extensions import db


class Conversation(EntityBasedModel):
    """Модель диалога"""
    __tablename__ = 'conversations'
    
    conversation_id = Column(Integer, primary_key=True)
    conversation_type = Column(String(20), nullable=False)
    subject = Column(String(255))
    related_entity_id = Column(Integer, ForeignKey('global_entities.entity_id'))
    status_id = Column(Integer, ForeignKey('statuses.status_id'))
    last_message_date = Column(DateTime)
    
    __table_args__ = (
        db.CheckConstraint(
            "conversation_type IN ('user_chat', 'support', 'system')",
            name='check_conversation_type'
        ),
        Index('idx_conversations_last_message', 'last_message_date'),
    )
    
    # Отношения
    related_entity = db.relationship('GlobalEntity', foreign_keys=[related_entity_id])
    status = db.relationship('Status')
    
    def get_participants(self):
        """Получение участников диалога"""
        return ConversationParticipant.query.filter(
            ConversationParticipant.conversation_id == self.conversation_id,
            ConversationParticipant.is_active == True
        ).all()
    
    def get_participant(self, user_id):
        """Получение конкретного участника"""
        return ConversationParticipant.query.filter(
            ConversationParticipant.conversation_id == self.conversation_id,
            ConversationParticipant.user_id == user_id,
            ConversationParticipant.is_active == True
        ).first()
    
    def add_participant(self, user_id, role='participant'):
        """Добавление участника в диалог"""
        existing = self.get_participant(user_id)
        if existing:
            return existing
        
        participant = ConversationParticipant(
            conversation_id=self.conversation_id,
            user_id=user_id,
            role=role
        )
        participant.save()
        return participant
    
    def get_last_message(self):
        """Получение последнего сообщения"""
        return Message.query.filter(
            Message.conversation_id == self.conversation_id,
            Message.is_deleted == False
        ).order_by(Message.sent_date.desc()).first()
    
    def get_unread_count(self, user_id):
        """Получение количества непрочитанных сообщений для пользователя"""
        participant = self.get_participant(user_id)
        if not participant:
            return 0
        
        return Message.query.filter(
            Message.conversation_id == self.conversation_id,
            Message.sender_id != user_id,
            Message.sent_date > (participant.last_read_date or datetime.min),
            Message.is_deleted == False
        ).count()
    
    def mark_as_read(self, user_id):
        """Отметка диалога как прочитанного"""
        participant = self.get_participant(user_id)
        if participant:
            participant.last_read_date = datetime.utcnow()
            participant.save()
    
    def update_last_message_date(self):
        """Обновление времени последнего сообщения"""
        last_message = self.get_last_message()
        if last_message:
            self.last_message_date = last_message.sent_date
            self.save()
    
    def to_dict(self, user_id=None):
        """Преобразование в словарь"""
        last_message = self.get_last_message()
        participants = self.get_participants()
        
        data = {
            'conversation_id': self.conversation_id,
            'entity_id': self.entity_id,
            'conversation_type': self.conversation_type,
            'subject': self.subject,
            'related_entity_id': self.related_entity_id,
            'status': self.status.status_name if self.status else None,
            'last_message_date': self.last_message_date.isoformat() if self.last_message_date else None,
            'created_date': self.created_date.isoformat() if self.created_date else None,
            'participants_count': len(participants),
            'participants': [p.to_dict() for p in participants]
        }
        
        if last_message:
            data['last_message'] = {
                'message_id': last_message.message_id,
                'sender_id': last_message.sender_id,
                'message_text': last_message.message_text,
                'sent_date': last_message.sent_date.isoformat(),
                'message_type': last_message.message_type
            }
        
        if user_id:
            data['unread_count'] = self.get_unread_count(user_id)
            data['is_participant'] = self.get_participant(user_id) is not None
        
        return data


class ConversationParticipant(BaseModel):
    """Модель участника диалога"""
    __tablename__ = 'conversation_participants'
    
    conversation_id = Column(Integer, ForeignKey('conversations.conversation_id'), nullable=False)
    user_id = Column(Integer, ForeignKey('users.user_id'), nullable=False)
    role = Column(String(20), default='participant')
    joined_date = Column(DateTime, default=datetime.utcnow)
    last_read_date = Column(DateTime)
    notification_settings = Column(JSONB, default={})
    
    __table_args__ = (
        db.PrimaryKeyConstraint('conversation_id', 'user_id'),
        db.CheckConstraint(
            "role IN ('participant', 'moderator', 'support', 'admin')",
            name='check_participant_role'
        ),
    )
    
    # Отношения
    conversation = db.relationship('Conversation', backref='participants')
    user = db.relationship('User', backref='conversation_participations')
    
    def to_dict(self):
        """Преобразование в словарь"""
        return {
            'conversation_id': self.conversation_id,
            'user_id': self.user_id,
            'user_name': self.user.full_name if self.user else None,
            'role': self.role,
            'joined_date': self.joined_date.isoformat() if self.joined_date else None,
            'last_read_date': self.last_read_date.isoformat() if self.last_read_date else None,
            'notification_settings': self.notification_settings
        }


class Message(EntityBasedModel):
    """Модель сообщения"""
    __tablename__ = 'messages'
    
    message_id = Column(Integer, primary_key=True)
    conversation_id = Column(Integer, ForeignKey('conversations.conversation_id'), nullable=False)
    sender_id = Column(Integer, ForeignKey('users.user_id'), nullable=False)
    message_text = Column(Text)
    message_type = Column(String(20), default='text')
    sent_date = Column(DateTime, default=datetime.utcnow)
    edited_date = Column(DateTime)
    is_deleted = Column(Boolean, default=False)
    parent_message_id = Column(Integer, ForeignKey('messages.message_id'))
    metadata = Column(JSONB, default={})
    
    __table_args__ = (
        db.CheckConstraint(
            "message_type IN ('text', 'system', 'media', 'action')",
            name='check_message_type'
        ),
        Index('idx_messages_conversation_date', 'conversation_id', 'sent_date'),
    )
    
    # Отношения
    conversation = db.relationship('Conversation', backref='messages')
    sender = db.relationship('User', backref='sent_messages')
    parent_message = db.relationship('Message', remote_side=[message_id], backref='replies')
    
    def soft_delete(self):
        """Мягкое удаление сообщения"""
        self.is_deleted = True
        self.message_text = None
        self.save()
    
    def edit_message(self, new_text):
        """Редактирование сообщения"""
        self.message_text = new_text
        self.edited_date = datetime.utcnow()
        self.save()
    
    def get_attachments(self):
        """Получение вложений сообщения"""
        return MessageAttachment.query.filter(
            MessageAttachment.message_id == self.message_id
        ).all()
    
    def to_dict(self, include_attachments=True):
        """Преобразование в словарь"""
        data = {
            'message_id': self.message_id,
            'entity_id': self.entity_id,
            'conversation_id': self.conversation_id,
            'sender_id': self.sender_id,
            'sender_name': self.sender.full_name if self.sender else None,
            'message_text': self.message_text,
            'message_type': self.message_type,
            'sent_date': self.sent_date.isoformat() if self.sent_date else None,
            'edited_date': self.edited_date.isoformat() if self.edited_date else None,
            'is_deleted': self.is_deleted,
            'parent_message_id': self.parent_message_id,
            'metadata': self.metadata
        }
        
        if include_attachments:
            attachments = self.get_attachments()
            data['attachments'] = [att.to_dict() for att in attachments]
        
        return data


class MessageAttachment(BaseModel):
    """Модель вложения сообщения"""
    __tablename__ = 'message_attachments'
    
    attachment_id = Column(Integer, primary_key=True)
    message_id = Column(Integer, ForeignKey('messages.message_id'), nullable=False)
    media_id = Column(Integer, ForeignKey('media_storage.media_id'), nullable=False)
    
    # Отношения
    message = db.relationship('Message', backref='attachments')
    media = db.relationship('MediaStorage', backref='message_attachments')
    
    def to_dict(self):
        """Преобразование в словарь"""
        return {
            'attachment_id': self.attachment_id,
            'message_id': self.message_id,
            'media_id': self.media_id,
            'media': self.media.to_dict() if self.media else None
        }
