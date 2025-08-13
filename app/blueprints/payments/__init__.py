# app/blueprints/payments/__init__.py
"""
Payments Blueprint для управления платежами и продвижением
"""

from flask import Blueprint

payments_bp = Blueprint('payments', __name__, url_prefix='/api/payments')

from app.blueprints.payments import routes


