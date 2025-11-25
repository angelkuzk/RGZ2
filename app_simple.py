from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os
import re

app = Flask(__name__)
app.secret_key = 'simple-secret-key-2025'

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Модели базы данных
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    login = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Employee(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(100), nullable=False)
    position = db.Column(db.String(100), nullable=False)
    gender = db.Column(db.String(10), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    email = db.Column(db.String(100), nullable=False)
    on_probation = db.Column(db.Boolean, default=False)
    hire_date = db.Column(db.Date, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# Главная страница
@app.route('/')
def index():
    employees_count = Employee.query.count()
    users_count = User.query.count()
    return render_template('index.html', 
                         employees_count=employees_count,
                         users_count=users_count)

# Вход
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        login = request.form.get('login')
        password = request.form.get('password')
        
        user = User.query.filter_by(login=login).first()
        if user and user.check_password(password):
            session['user_id'] = user.id
            session['user_login'] = user.login
            flash('Успешный вход!', 'success')
            return redirect(url_for('employees'))
        else:
            flash('Неверный логин или пароль', 'error')
    
    return render_template('login.html')

# Выход
@app.route('/logout')
def logout():
    session.clear()
    flash('Вы вышли из системы', 'info')
    return redirect(url_for('index'))

# Список сотрудников
@app.route('/employees')
def employees():
    page = request.args.get('page', 1, type=int)
    per_page = 20
    search = request.args.get('search', '')
    sort_field = request.args.get('sort', 'id')
    sort_order = request.args.get('order', 'asc')
    
    query = Employee.query
    
    if search:
        query = query.filter(
            Employee.full_name.ilike(f'%{search}%') |
            Employee.position.ilike(f'%{search}%') |
            Employee.phone.ilike(f'%{search}%') |
            Employee.email.ilike(f'%{search}%')
        )
    
    # Сортировка
    if sort_field in ['full_name', 'position', 'gender', 'phone', 'email', 'hire_date']:
        if sort_order == 'desc':
            query = query.order_by(getattr(Employee, sort_field).desc())
        else:
            query = query.order_by(getattr(Employee, sort_field))
    else:
        query = query.order_by(Employee.id)
    
    employees = query.paginate(page=page, per_page=per_page, error_out=False)
    
    return render_template('employees.html', 
                         employees=employees,
                         search=search,
                         sort_field=sort_field,
                         sort_order=sort_order,
                         is_authenticated='user_id' in session)

# Добавление сотрудника
@app.route('/add_employee', methods=['GET', 'POST'])
def add_employee():
    if 'user_id' not in session:
        flash('Требуется авторизация', 'error')
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        try:
            employee = Employee(
                full_name=request.form['full_name'],
                position=request.form['position'],
                gender=request.form['gender'],
                phone=request.form['phone'],
                email=request.form['email'],
                on_probation='on_probation' in request.form,
                hire_date=datetime.strptime(request.form['hire_date'], '%Y-%m-%d')
            )
            db.session.add(employee)
            db.session.commit()
            flash('Сотрудник успешно добавлен', 'success')
            return redirect(url_for('employees'))
        except Exception as e:
            flash(f'Ошибка: {str(e)}', 'error')
    
    return render_template('edit_employee.html')

# Удаление сотрудника
@app.route('/delete_employee/<int:employee_id>')
def delete_employee(employee_id):
    if 'user_id' not in session:
        flash('Требуется авторизация', 'error')
        return redirect(url_for('login'))
    
    employee = Employee.query.get_or_404(employee_id)
    db.session.delete(employee)
    db.session.commit()
    flash('Сотрудник удален', 'success')
    return redirect(url_for('employees'))

# Удаление аккаунта
@app.route('/delete_account', methods=['POST'])
def delete_account():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user = User.query.get(session['user_id'])
    if user:
        db.session.delete(user)
        db.session.commit()
        session.clear()
        flash('Аккаунт удален', 'info')
    
    return redirect(url_for('index'))

# Инициализация базы данных
def init_db():
    with app.app_context():
        db.create_all()
        
        # Создаем тестовых пользователей
        if User.query.count() == 0:
            admin = User(login='admin')
            admin.set_password('admin123')
            db.session.add(admin)
            
            angelina = User(login='angelkuz')
            angelina.set_password('02042004')
            db.session.add(angelina)
            
            db.session.commit()
            print("✅ Пользователи созданы")
        
        # Создаем тестовых сотрудников
        if Employee.query.count() == 0:
            from faker import Faker
            fake = Faker('ru_RU')
            
            positions = ['Менеджер', 'Разработчик', 'Аналитик', 'Дизайнер', 'Тестировщик', 'Бухгалтер']
            
            for i in range(100):
                employee = Employee(
                    full_name=fake.name(),
                    position=fake.random.choice(positions),
                    gender=fake.random.choice(['male', 'female']),
                    phone=fake.phone_number(),
                    email=fake.email(),
                    on_probation=fake.boolean(chance_of_getting_true=30),
                    hire_date=fake.date_between(start_date='-5y', end_date='today')
                )
                db.session.add(employee)
            
            db.session.commit()
            print("✅ 100 сотрудников создано")

if __name__ == '__main__':
    init_db()
    app.run(debug=True)