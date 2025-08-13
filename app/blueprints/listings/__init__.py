# app/blueprints/listings/__init__.py
from flask import Blueprint

bp = Blueprint('listings', __name__)

from app.blueprints.listings import routes


