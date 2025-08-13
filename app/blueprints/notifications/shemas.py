# app/blueprints/notifications/schemas.py
"""
Marshmallow схемы для уведомлений
"""

from marshmallow import Schema, fields, validate
from marshmallow.validate import Length, OneOf


class NotificationSchema(Schema):
    """Схема для уведомления"""
    notification_id = fields.Int(dump_only=True)
    title = fields.Str()
    message = fields.Str()
    notification_type = fields.Str()
    status = fields.Str()
    scheduled_date = fields.DateTime()
    sent_date = fields.DateTime(allow_none=True)
    opened_date = fields.DateTime(allow_none=True)
    template_data = fields.Raw()
    related_entity_id = fields.Int(allow_none=True)


class NotificationListSchema(Schema):
    """Схема для списка уведомлений"""
    notification_id = fields.Int()
    title = fields.Str()
    message = fields.Str()
    notification_type = fields.Str()
    status = fields.Str()
    scheduled_date = fields.DateTime()
    opened_date = fields.DateTime(allow_none=True)


class NotificationSettingsSchema(Schema):
    """Схема для настроек уведомлений"""
    channel_id = fields.Int(required=True)
    notification_type = fields.Str(required=True, validate=Length(min=1, max=50))
    is_enabled = fields.Bool(missing=True)
    frequency = fields.Str(
        missing='instant',
        validate=OneOf(['instant', 'daily', 'weekly', 'never'])
    )


class SendNotificationSchema(Schema):
    """Схема для отправки уведомления"""
    user_id = fields.Int(required=True)
    channel_id = fields.Int(required=True)
    template_id = fields.Int(allow_none=True)
    title = fields.Str(required=True, validate=Length(min=1, max=255))
    message = fields.Str(required=True, validate=Length(min=1))
    notification_type = fields.Str(required=True, validate=Length(min=1, max=50))
    related_entity_id = fields.Int(allow_none=True)
    template_data = fields.Raw(missing={})
    scheduled_date = fields.DateTime(allow_none=True)


class NotificationTemplateSchema(Schema):
    """Схема для шаблона уведомления"""
    template_id = fields.Int()
    template_code = fields.Str()
    template_name = fields.Str()
    channel_id = fields.Int()
    subject_template = fields.Str(allow_none=True)
    body_template = fields.Str()
    variables = fields.Raw()
    is_active = fields.Bool()