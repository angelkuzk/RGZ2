import sys
import os

path = '/home/angelkuzk2004/RGZ2'
if path not in sys.path:
    sys.path.insert(0, path)

# Устанавливаем переменные окружения
os.environ['SECRET_KEY'] = 'pythonanywhere-secret-key-2024'

# Импортируем приложение
from app import app as application

# Инициализация базы данных
with application.app_context():
    from app import init_db
    try:
        init_db()
        print("✅ База данных инициализирована успешно")
    except Exception as e:
        print(f"⚠️ Ошибка при инициализации базы данных: {e}")