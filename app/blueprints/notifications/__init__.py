# app/blueprints/notifications/__init__.py
"""
Notifications Blueprint для управления уведомлениями
"""

from flask import Blueprint

notifications_bp = Blueprint('notifications', __name__, url_prefix='/api/notifications')

from app.blueprints.notifications import routes



