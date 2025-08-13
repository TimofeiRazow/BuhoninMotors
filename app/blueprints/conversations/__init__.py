# app/blueprints/conversations/__init__.py
from flask import Blueprint

bp = Blueprint('conversations', __name__)

from app.blueprints.conversations import routes