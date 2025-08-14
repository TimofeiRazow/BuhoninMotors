

# app/blueprints/conversations/schemas.py
from marshmallow import Schema, fields, validate, validates, ValidationError


class CreateConversationSchema(Schema):
    """Схема для создания диалога"""
    conversation_type = fields.Str(required=True, validate=validate.OneOf(['user_chat', 'support', 'system']))
    subject = fields.Str(required=False, validate=validate.Length(max=255))
    participant_id = fields.Int(required=True)  # ID другого участника
    related_entity_id = fields.Int(required=False)  # ID связанной сущности (например, объявления)
    initial_message = fields.Str(required=True, validate=validate.Length(min=1, max=5000))


class SendMessageSchema(Schema):
    """Схема для отправки сообщения"""
    message_text = fields.Str(required=True, validate=validate.Length(min=1, max=5000))
    message_type = fields.Str(required=False, validate=validate.OneOf(['text', 'media', 'action']), default='text')
    parent_message_id = fields.Int(required=False)
    meta_data = fields.Raw(required=False)


class EditMessageSchema(Schema):
    """Схема для редактирования сообщения"""
    message_text = fields.Str(required=True, validate=validate.Length(min=1, max=5000))


class ConversationSchema(Schema):
    """Схема для диалога"""
    conversation_id = fields.Int(dump_only=True)
    entity_id = fields.Int(dump_only=True)
    conversation_type = fields.Str(dump_only=True)
    subject = fields.Str(dump_only=True)
    related_entity_id = fields.Int(dump_only=True)
    status = fields.Str(dump_only=True)
    last_message_date = fields.DateTime(dump_only=True)
    created_date = fields.DateTime(dump_only=True)
    participants_count = fields.Int(dump_only=True)
    unread_count = fields.Int(dump_only=True)
    is_participant = fields.Bool(dump_only=True)
    last_message = fields.Raw(dump_only=True)
    participants = fields.List(fields.Raw(), dump_only=True)


class MessageSchema(Schema):
    """Схема для сообщения"""
    message_id = fields.Int(dump_only=True)
    entity_id = fields.Int(dump_only=True)
    conversation_id = fields.Int(dump_only=True)
    sender_id = fields.Int(dump_only=True)
    sender_name = fields.Str(dump_only=True)
    message_text = fields.Str(dump_only=True)
    message_type = fields.Str(dump_only=True)
    sent_date = fields.DateTime(dump_only=True)
    edited_date = fields.DateTime(dump_only=True)
    is_deleted = fields.Bool(dump_only=True)
    parent_message_id = fields.Int(dump_only=True)
    meta_data = fields.Raw(dump_only=True)
    attachments = fields.List(fields.Raw(), dump_only=True)

