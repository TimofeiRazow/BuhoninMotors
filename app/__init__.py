# app/__init__.py
from flask import Flask
from flask_cors import CORS
from app.extensions import db, jwt, migrate, ma, cache, limiter
from app.config import Config




def create_app(config_class=Config):
    """Factory function для создания Flask приложения"""
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # Инициализация расширений
    db.init_app(app)
    jwt.init_app(app)
    migrate.init_app(app, db)
    ma.init_app(app)
    cache.init_app(app)
    limiter.init_app(app)
    CORS(app)
    
    # Регистрация blueprints
    from app.blueprints.auth import bp as auth_bp
    from app.blueprints.users import bp as users_bp
    from app.blueprints.listings import bp as listings_bp
    from app.blueprints.cars import bp as cars_bp
    from app.blueprints.locations import bp as locations_bp
    from app.blueprints.conversations import bp as conversations_bp
    from app.blueprints.media import bp as media_bp
    from app.blueprints.notifications import notifications_bp
    from app.blueprints.payments import payments_bp
    from app.blueprints.admin import bp as admin_bp
    from app.blueprints.support import support_bp
    
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(users_bp, url_prefix='/api/users')
    app.register_blueprint(listings_bp, url_prefix='/api/listings')
    app.register_blueprint(cars_bp, url_prefix='/api/cars')
    app.register_blueprint(locations_bp, url_prefix='/api/locations')
    app.register_blueprint(conversations_bp, url_prefix='/api/conversations')
    app.register_blueprint(media_bp, url_prefix='/api/media')
    app.register_blueprint(notifications_bp, url_prefix='/api/notifications')
    app.register_blueprint(payments_bp, url_prefix='/api/payments')
    app.register_blueprint(admin_bp, url_prefix='/api/admin')
    app.register_blueprint(support_bp, url_prefix='/api/support')
    
    # Регистрация обработчиков ошибок
    register_error_handlers(app)
    
    # Импорт моделей для правильной работы миграций
    from app import models
    
    return app


def register_error_handlers(app):
    """Регистрация обработчиков ошибок"""
    from flask import jsonify
    from werkzeug.exceptions import HTTPException
    from app.utils.exceptions import ValidationError, AuthenticationError, AuthorizationError
    
    @app.errorhandler(ValidationError)
    def handle_validation_error(e):
        return jsonify({'error': 'Validation error', 'message': str(e)}), 400
    
    @app.errorhandler(AuthenticationError)
    def handle_authentication_error(e):
        return jsonify({'error': 'Authentication error', 'message': str(e)}), 401
    
    @app.errorhandler(AuthorizationError)
    def handle_authorization_error(e):
        return jsonify({'error': 'Authorization error', 'message': str(e)}), 403
    
    @app.errorhandler(404)
    def handle_not_found(e):
        return jsonify({'error': 'Not found', 'message': 'Resource not found'}), 404
    
    @app.errorhandler(500)
    def handle_internal_error(e):
        return jsonify({'error': 'Internal server error', 'message': 'Something went wrong'}), 500