# app/tasks/__init__.py
from app.extensions import make_celery
from flask import current_app


def init_celery(app):
    """Инициализация Celery с Flask приложением"""
    celery = make_celery(app)
    
    # Импортируем все задачи
    from . import notifications
    from . import cleanup
    from . import indexing
    from . import analytics
    
    return celery