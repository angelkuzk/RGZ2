from app import app, db
from models import User, Employee

def reset_database():
    with app.app_context():
        db.drop_all()
        db.create_all()
        print("База данных пересоздана!")

if __name__ == '__main__':
    reset_database()