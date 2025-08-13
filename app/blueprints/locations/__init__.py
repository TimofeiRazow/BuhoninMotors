# app/blueprints/locations/__init__.py
from flask import Blueprint

bp = Blueprint('locations', __name__)

from app.blueprints.locations import routes