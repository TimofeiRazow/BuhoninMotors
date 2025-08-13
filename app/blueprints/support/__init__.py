# app/blueprints/support/__init__.py
"""
Support Blueprint для системы поддержки
"""

from flask import Blueprint

support_bp = Blueprint('support', __name__, url_prefix='/api/support')

from app.blueprints.support import routes




