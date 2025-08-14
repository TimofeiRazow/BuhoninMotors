# app/blueprints/users/__init__.py
"""
Users Blueprint для управления пользователями
"""

from flask import Blueprint

bp = Blueprint('users', __name__, url_prefix='/api/users')

from app.blueprints.users import routes