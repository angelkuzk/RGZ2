import sys
import os

path = '/home/angelkuzk2004/RGZ2'
if path not in sys.path:
    sys.path.append(path)

# Устанавливаем переменные окружения
os.environ['SECRET_KEY'] = 'your-secret-key-for-pythonanywhere'
os.environ['DATABASE_URL'] = 'sqlite:///' + os.path.join(path, 'instance', 'hr_database.db')

from app import app as application

# Инициализация базы данных при первом запуске
with application.app_context():
    from app import init_db
    try:
        init_db()
        print("✅ База данных инициализирована")
    except Exception as e:
        print(f"⚠️ База данных уже существует: {e}")