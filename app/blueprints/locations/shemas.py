# app/blueprints/locations/schemas.py
from marshmallow import Schema, fields, validate


class CountrySchema(Schema):
    """Схема для страны"""
    country_id = fields.Int(dump_only=True)
    country_code = fields.Str(required=True, validate=validate.Length(equal=2))
    country_name = fields.Str(required=True, validate=validate.Length(min=1, max=100))
    phone_code = fields.Str(required=False, validate=validate.Length(max=10))
    regions_count = fields.Int(dump_only=True)


class RegionSchema(Schema):
    """Схема для региона"""
    region_id = fields.Int(dump_only=True)
    region_name = fields.Str(required=True, validate=validate.Length(min=1, max=100))
    country_id = fields.Int(required=True)
    country_name = fields.Str(dump_only=True)
    region_code = fields.Str(required=False, validate=validate.Length(max=10))
    sort_order = fields.Int(required=False, default=0)
    cities_count = fields.Int(dump_only=True)


class CitySchema(Schema):
    """Схема для города"""
class CitySchema(Schema):
    """Схема для города"""
    city_id = fields.Int(dump_only=True)
    city_name = fields.Str(required=True, validate=validate.Length(min=1, max=100))
    region_id = fields.Int(required=True)
    region_name = fields.Str(dump_only=True)
    country_name = fields.Str(dump_only=True)
    full_name = fields.Str(dump_only=True)
    latitude = fields.Decimal(required=False, validate=validate.Range(min=-90, max=90))
    longitude = fields.Decimal(required=False, validate=validate.Range(min=-180, max=180))
    population = fields.Int(required=False, validate=validate.Range(min=0))
    sort_order = fields.Int(required=False, default=0)
    distance_km = fields.Decimal(dump_only=True)


class LocationSearchSchema(Schema):
    """Схема для поиска местоположений"""
    query = fields.Str(required=True, validate=validate.Length(min=2, max=100))
    country_id = fields.Int(required=False)
    region_id = fields.Int(required=False)
    limit = fields.Int(required=False, validate=validate.Range(min=1, max=100), default=10)


class NearbySearchSchema(Schema):
    """Схема для поиска поблизости"""
    latitude = fields.Decimal(required=True, validate=validate.Range(min=-90, max=90))
    longitude = fields.Decimal(required=True, validate=validate.Range(min=-180, max=180))
    radius = fields.Int(required=False, validate=validate.Range(min=1, max=1000), default=50)
    limit = fields.Int(required=False, validate=validate.Range(min=1, max=100), default=20)

