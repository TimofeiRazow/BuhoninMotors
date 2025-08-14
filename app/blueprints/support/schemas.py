# app/blueprints/support/schemas.py
"""
Marshmallow схемы для поддержки
"""

from marshmallow import Schema, fields, validate
from marshmallow.validate import Length, OneOf, Range


class SupportTicketSchema(Schema):
    """Схема для тикета поддержки"""
    ticket_id = fields.Int(dump_only=True)
    entity_id = fields.Int(dump_only=True)
    user_id = fields.Int(dump_only=True)
    category_id = fields.Int(allow_none=True)
    priority = fields.Str()
    subject = fields.Str()
    description = fields.Str()
    status_id = fields.Int()
    assigned_to = fields.Int(allow_none=True)
    created_date = fields.DateTime(dump_only=True)
    first_response_date = fields.DateTime(allow_none=True, dump_only=True)
    resolved_date = fields.DateTime(allow_none=True, dump_only=True)
    customer_satisfaction = fields.Int(allow_none=True)
    
    # Вложенные объекты
    user = fields.Nested('UserSchema', dump_only=True, only=['user_id', 'first_name', 'last_name'])
    category = fields.Nested('CategorySchema', dump_only=True, only=['category_id', 'category_name'])
    assigned_user = fields.Nested('UserSchema', dump_only=True, only=['user_id', 'first_name', 'last_name'])


class TicketListSchema(Schema):
    """Схема для списка тикетов"""
    ticket_id = fields.Int()
    subject = fields.Str()
    priority = fields.Str()
    status_id = fields.Int()
    created_date = fields.DateTime()
    category_name = fields.Str(attribute='category.category_name', allow_none=True)
    assigned_to_name = fields.Method('get_assigned_name')
    
    def get_assigned_name(self, obj):
        if obj.assigned_user:
            return f"{obj.assigned_user.first_name} {obj.assigned_user.last_name}".strip()
        return None


class CreateTicketSchema(Schema):
    """Схема для создания тикета"""
    category_id = fields.Int(allow_none=True)
    priority = fields.Str(
        missing='medium',
        validate=OneOf(['low', 'medium', 'high', 'critical'])
    )
    subject = fields.Str(
        required=True,
        validate=Length(min=5, max=255)
    )
    description = fields.Str(
        required=True,
        validate=Length(min=10, max=5000)
    )


class UpdateTicketSchema(Schema):
    """Схема для обновления тикета администратором"""
    status_id = fields.Int(validate=Range(min=1, max=5))
    priority = fields.Str(validate=OneOf(['low', 'medium', 'high', 'critical']))
    assigned_to = fields.Int(allow_none=True)
    category_id = fields.Int(allow_none=True)


class TicketResponseSchema(Schema):
    """Схема для ответа на тикет"""
    message = fields.Str(
        required=True,
        validate=Length(min=1, max=5000)
    )
    is_internal = fields.Bool(missing=False)  # внутренняя заметка для админов


class CategorySchema(Schema):
    """Схема для категории поддержки"""
    category_id = fields.Int()
    category_name = fields.Str()
    description = fields.Str(allow_none=True)
    parent_category_id = fields.Int(allow_none=True)


class UserSchema(Schema):
    """Базовая схема пользователя"""
    user_id = fields.Int()
    first_name = fields.Str(allow_none=True)
    last_name = fields.Str(allow_none=True)