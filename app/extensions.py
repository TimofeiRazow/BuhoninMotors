# app/extensions.py
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_jwt_extended import JWTManager
from flask_marshmallow import Marshmallow
from flask_caching import Cache
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_mail import Mail
from celery import Celery

# Инициализация расширений
db = SQLAlchemy()
migrate = Migrate()
jwt = JWTManager()
ma = Marshmallow()
cache = Cache()
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"]
)
mail = Mail()


def make_celery(app):
    """Создание Celery instance с Flask контекстом"""
    celery = Celery(
        app.import_name,
        backend=app.config['CELERY_RESULT_BACKEND'],
        broker=app.config['CELERY_BROKER_URL']
    )
    celery.conf.update(app.config)

    class ContextTask(celery.Task):
        """Обертка для выполнения задач в контексте Flask приложения"""
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)

    celery.Task = ContextTask
    return celery


# Настройки JWT
@jwt.token_in_blocklist_loader
def check_if_token_revoked(jwt_header, jwt_payload):
    """Проверка токена в черном списке"""
    from app.models.user import RevokedToken
    jti = jwt_payload['jti']
    return RevokedToken.is_jti_blacklisted(jti)


@jwt.expired_token_loader
def expired_token_callback(jwt_header, jwt_payload):
    """Обработчик истекшего токена"""
    from flask import jsonify
    return jsonify({'error': 'Token has expired'}), 401


@jwt.invalid_token_loader
def invalid_token_callback(error):
    """Обработчик невалидного токена"""
    from flask import jsonify
    return jsonify({'error': 'Invalid token'}), 401


@jwt.unauthorized_loader
def missing_token_callback(error):
    """Обработчик отсутствующего токена"""
    from flask import jsonify
    return jsonify({'error': 'Authorization token is required'}), 401


@jwt.additional_claims_loader
def add_claims_to_jwt(identity):
    """Добавление дополнительных claims в JWT"""
    from app.models.user import User
    user = User.query.get(identity)
    return {
        'user_type': user.user_type if user else 'regular',
        'is_verified': user.verification_status == 'fully_verified' if user else False
    }