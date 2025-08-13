# app/blueprints/cars/schemas.py
from marshmallow import Schema, fields, validate


class BrandSchema(Schema):
    """Схема для марки автомобиля"""
    brand_id = fields.Int(dump_only=True)
    brand_name = fields.Str(required=True, validate=validate.Length(min=1, max=100))
    brand_slug = fields.Str(dump_only=True)
    logo_url = fields.Url(required=False, allow_none=True)
    country_origin = fields.Str(required=False, validate=validate.Length(max=100))
    sort_order = fields.Int(required=False, default=0)
    models_count = fields.Int(dump_only=True)


class ModelSchema(Schema):
    """Схема для модели автомобиля"""
    model_id = fields.Int(dump_only=True)
    brand_id = fields.Int(required=True)
    brand_name = fields.Str(dump_only=True)
    model_name = fields.Str(required=True, validate=validate.Length(min=1, max=100))
    model_slug = fields.Str(dump_only=True)
    full_name = fields.Str(dump_only=True)
    start_year = fields.Int(required=False, validate=validate.Range(min=1950, max=2030))
    end_year = fields.Int(required=False, validate=validate.Range(min=1950, max=2030))
    body_type_id = fields.Int(required=False)
    body_type_name = fields.Str(dump_only=True)
    generations_count = fields.Int(dump_only=True)


class GenerationSchema(Schema):
    """Схема для поколения автомобиля"""
    generation_id = fields.Int(dump_only=True)
    model_id = fields.Int(required=True)
    generation_name = fields.Str(required=True, validate=validate.Length(min=1, max=100))
    start_year = fields.Int(required=False, validate=validate.Range(min=1950, max=2030))
    end_year = fields.Int(required=False, validate=validate.Range(min=1950, max=2030))
    years_range = fields.Str(dump_only=True)
    description = fields.Str(required=False, validate=validate.Length(max=1000))


class BodyTypeSchema(Schema):
    """Схема для типа кузова"""
    body_type_id = fields.Int(dump_only=True)
    body_type_name = fields.Str(required=True, validate=validate.Length(min=1, max=50))
    icon_url = fields.Url(required=False, allow_none=True)
    sort_order = fields.Int(required=False, default=0)


class EngineTypeSchema(Schema):
    """Схема для типа двигателя"""
    engine_type_id = fields.Int(dump_only=True)
    engine_type_name = fields.Str(required=True, validate=validate.Length(min=1, max=50))
    sort_order = fields.Int(required=False, default=0)


class TransmissionTypeSchema(Schema):
    """Схема для типа трансмиссии"""
    transmission_id = fields.Int(dump_only=True)
    transmission_name = fields.Str(required=True, validate=validate.Length(min=1, max=50))
    sort_order = fields.Int(required=False, default=0)


class DriveTypeSchema(Schema):
    """Схема для типа привода"""
    drive_type_id = fields.Int(dump_only=True)
    drive_type_name = fields.Str(required=True, validate=validate.Length(min=1, max=50))
    sort_order = fields.Int(required=False, default=0)


class ColorSchema(Schema):
    """Схема для цвета автомобиля"""
    color_id = fields.Int(dump_only=True)
    color_name = fields.Str(required=True, validate=validate.Length(min=1, max=50))
    color_hex = fields.Str(required=False, validate=validate.Regexp(r'^#[0-9A-Fa-f]{6}$'))
    sort_order = fields.Int(required=False, default=0)


class FeatureSchema(Schema):
    """Схема для особенности автомобиля"""
    feature_id = fields.Int(dump_only=True)
    feature_name = fields.Str(required=True, validate=validate.Length(min=1, max=100))
    category_id = fields.Int(required=False)
    category_name = fields.Str(dump_only=True)
    icon_url = fields.Url(required=False, allow_none=True)
    sort_order = fields.Int(required=False, default=0)


class AttributeGroupSchema(Schema):
    """Схема для группы атрибутов"""
    group_id = fields.Int(dump_only=True)
    group_name = fields.Str(required=True, validate=validate.Length(min=1, max=100))
    group_code = fields.Str(required=True, validate=validate.Length(min=1, max=50))
    sort_order = fields.Int(required=False, default=0)
    attributes = fields.List(fields.Nested('AttributeSchema'), dump_only=True)


class AttributeSchema(Schema):
    """Схема для атрибута автомобиля"""
    attribute_id = fields.Int(dump_only=True)
    group_id = fields.Int(required=True)
    attribute_code = fields.Str(required=True, validate=validate.Length(min=1, max=100))
    attribute_name = fields.Str(required=True, validate=validate.Length(min=1, max=100))
    attribute_type = fields.Str(required=True, validate=validate.OneOf([
        'string', 'number', 'boolean', 'reference', 'multi_select'
    ]))
    reference_table = fields.Str(required=False, allow_none=True)
    is_required = fields.Bool(required=False, default=False)
    is_searchable = fields.Bool(required=False, default=False)
    is_filterable = fields.Bool(required=False, default=False)
    validation_rules = fields.Raw(required=False)
    default_value = fields.Str(required=False, allow_none=True)