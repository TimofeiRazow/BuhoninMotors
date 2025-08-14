# app/blueprints/admin/schemas.py
from marshmallow import Schema, fields, validate


class ModerationActionSchema(Schema):
    """Схема для действий модерации"""
    action = fields.Str(required=True, validate=validate.OneOf(['approve', 'reject']))
    reason = fields.Str(required=False, validate=validate.Length(max=1000))
    notes = fields.Str(required=False, validate=validate.Length(max=2000))


class ReportContentSchema(Schema):
    """Схема для жалобы на контент"""
    entity_id = fields.Int(required=True)
    report_reason = fields.Str(required=True, validate=validate.OneOf([
        'spam', 'fraud', 'inappropriate', 'duplicate', 'wrong_category', 'other'
    ]))
    description = fields.Str(required=False, validate=validate.Length(max=1000))


class ResolveReportSchema(Schema):
    """Схема для разрешения жалобы"""
    action = fields.Str(required=True, validate=validate.OneOf(['resolve', 'dismiss']))
    notes = fields.Str(required=False, validate=validate.Length(max=2000))


class UserActionSchema(Schema):
    """Схема для действий с пользователями"""
    action = fields.Str(required=True, validate=validate.OneOf([
        'block', 'unblock', 'warn', 'promote', 'demote'
    ]))
    reason = fields.Str(required=False, validate=validate.Length(max=1000))
    duration_days = fields.Int(required=False, validate=validate.Range(min=1, max=365))


class AdminStatsSchema(Schema):
    """Схема для административной статистики"""
    users_count = fields.Int(dump_only=True)
    new_users_today = fields.Int(dump_only=True)
    new_users_month = fields.Int(dump_only=True)
    listings_count = fields.Int(dump_only=True)
    active_listings_count = fields.Int(dump_only=True)
    new_listings_today = fields.Int(dump_only=True)
    pending_moderation_count = fields.Int(dump_only=True)
    pending_reports_count = fields.Int(dump_only=True)