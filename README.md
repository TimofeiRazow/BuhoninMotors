# 1. Установка зависимостей
pip install -r requirements.txt

# 2. Настройка окружения
cp .env.example .env
# Отредактируйте .env файл

# 3. Инициализация БД
python scripts/init_db.py

# 4. Запуск приложения
python run.py