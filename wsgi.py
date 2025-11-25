import sys
import os

path = '/home/angelkuzk2004/RGZ2'
if path not in sys.path:
    sys.path.append(path)

# Устанавливаем переменные окружения
os.environ['FLASK_ENV'] = 'production'

# Импортируем приложение
from app_production import app as application

# Инициализируем базу данных при запуске
with application.app_context():
    from app_production import init_db
    init_db()