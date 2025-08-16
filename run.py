# run.py
import os
from flask.cli import FlaskGroup
from app import create_app
from app.extensions import db
from app.config import config

# Получаем конфигурацию из переменной окружения
config_name = os.environ.get('FLASK_ENV', 'development')
app = create_app(config[config_name])

# Создаем CLI группу для Flask команд
cli = FlaskGroup(app)

print(db.metadata.tables.keys())
@app.cli.command()
def init_db():
    """Инициализация базы данных"""
    print("Создание таблиц базы данных...")
    db.create_all()
    print("Таблицы созданы успешно!")


@app.cli.command()
def drop_db():
    """Удаление всех таблиц"""
    if input("Вы уверены? Это удалит все данные! (yes/no): ") == 'yes':
        print("Удаление таблиц...")
        db.drop_all()
        print("Таблицы удалены!")


@app.cli.command()
def reset_db():
    """Пересоздание базы данных"""
    print("Пересоздание базы данных...")
    db.drop_all()
    db.create_all()
    print("База данных пересоздана!")


@app.cli.command()
def seed_data():
    """Заполнение базы данных базовыми данными"""
    from scripts.seed_data import seed_initial_data
    print("Заполнение базовых данных...")
    seed_initial_data()
    print("Базовые данные загружены!")


@app.shell_context_processor
def make_shell_context():
    """Контекст для Flask shell"""
    from app import models
    return {
        'db': db,
        'User': User,
        'Listing': Listing,
        'CarBrand': CarBrand,
        'CarModel': CarModel,
        'Country': Country,
        'Region': Region,
        'City': City
    }


@app.route('/health')
def health_check():
    """Проверка работоспособности API"""
    return {
        'status': 'healthy',
        'timestamp': db.func.now(),
        'version': '1.0.0'
    }


@app.route('/')
def index():
    """Главная страница API"""
    return {
        'message': 'Kolesa.kz API',
        'version': '1.0.0',
        'endpoints': {
            'auth': '/api/auth',
            'users': '/api/users',
            'listings': '/api/listings',
            'cars': '/api/cars',
            'locations': '/api/locations',
            'health': '/health'
        }
    }


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)