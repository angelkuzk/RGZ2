import sys
import os

path = '/home/angelkuzk2004/RGZ2'
if path not in sys.path:
    sys.path.append(path)

from app_simple import app as application

with application.app_context():
    from app_simple import init_db
    init_db()