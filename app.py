from flask import Flask, render_template, request, redirect, url_for, flash, session
from models import db, User, Employee
from datetime import datetime
import os
import re
from dotenv import load_dotenv

# Проверяем, работаем ли на PythonAnywhere
is_pythonanywhere = 'PYTHONANYWHERE_DOMAIN' in os.environ

if is_pythonanywhere:
    # Настройки для PythonAnywhere
    app = Flask(__name__)
    app.secret_key = os.environ.get('SECRET_KEY', 'pythonanywhere-secret-key-2024')
    
    # Используем SQLite на PythonAnywhere
    database_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'instance', 'hr_database.db')
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{database_path}'
else:
    # Локальные настройки
    load_dotenv()
    app = Flask(__name__)
    app.secret_key = os.getenv('SECRET_KEY', 'dev-secret-key')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Создаем папку instance если ее нет
if not os.path.exists('instance'):
    os.makedirs('instance')

db.init_app(app)

# Валидация данных
def validate_credentials(login, password):
    if not login or not password:
        return False, "Логин и пароль не могут быть пустыми"
    
    if not re.match(r'^[a-zA-Z0-9!@#$%^&*()_+\-=\[\]{};\':"\\|,.<>\/?]*$', login):
        return False, "Логин может содержать только латинские буквы, цифры и знаки препинания"
    
    if not re.match(r'^[a-zA-Z0-9!@#$%^&*()_+\-=\[\]{};\':"\\|,.<>\/?]*$', password):
        return False, "Пароль может содержать только латинские буквы, цифры и знаки препинания"
    
    return True, ""

def validate_employee_data(data):
    errors = []
    
    if not data.get('full_name') or len(data['full_name'].strip()) < 2:
        errors.append("ФИО должно содержать не менее 2 символов")
    
    if not data.get('position'):
        errors.append("Должность не может быть пустой")
    
    if not data.get('gender') or data['gender'] not in ['male', 'female']:
        errors.append("Укажите пол")
    
    if not data.get('phone') or not re.match(r'^[\d\s\-\+\(\)]+$', data['phone']):
        errors.append("Некорректный формат телефона")
    
    if not data.get('email') or not re.match(r'^[^@]+@[^@]+\.[^@]+$', data['email']):
        errors.append("Некорректный формат email")
    
    if not data.get('hire_date'):
        errors.append("Дата устройства на работу обязательна")
    
    return errors

# Фиксированный список сотрудников (остается без изменений)
def get_employees_data():
    return [
        # ... ваш существующий список сотрудников ...
        # (оставьте без изменений)
    ]

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        login = request.form.get('login')
        password = request.form.get('password')
        
        is_valid, message = validate_credentials(login, password)
        if not is_valid:
            flash(message, 'error')
            return render_template('login.html')
        
        user = User.query.filter_by(login=login).first()
        if user and user.check_password(password):
            session['user_id'] = user.id
            session['user_login'] = user.login
            session['is_hr'] = user.is_hr
            flash('Успешный вход!', 'success')
            return redirect(url_for('employees'))
        else:
            flash('Неверный логин или пароль', 'error')
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if 'user_id' not in session or not session.get('is_hr'):
        flash('Доступ запрещен. Требуются права кадровика.', 'error')
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        login = request.form.get('login')
        password = request.form.get('password')
        is_hr = False
        
        is_valid, message = validate_credentials(login, password)
        if not is_valid:
            flash(message, 'error')
            return render_template('register.html')
        
        existing_user = User.query.filter_by(login=login).first()
        if existing_user:
            flash('Пользователь с таким логином уже существует', 'error')
            return render_template('register.html')
        
        try:
            user = User(login=login, is_hr=is_hr)
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            flash('Пользователь успешно зарегистрирован как обычный пользователь', 'success')
            return redirect(url_for('employees'))
        except Exception as e:
            flash(f'Ошибка при регистрации: {str(e)}', 'error')
    
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Вы вышли из системы', 'info')
    return redirect(url_for('index'))

@app.route('/delete_account', methods=['POST'])
def delete_account():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user = User.query.get(session['user_id'])
    if user:
        db.session.delete(user)
        db.session.commit()
        session.clear()
        flash('Ваш аккаунт удален', 'info')
    
    return redirect(url_for('index'))

@app.route('/employees')
def employees():
    page = request.args.get('page', 1, type=int)
    per_page = 20
    search = request.args.get('search', '')
    sort_field = request.args.get('sort', 'id')
    sort_order = request.args.get('order', 'asc')
    
    # Получаем всех сотрудников
    all_employees = Employee.query.all()
    
    # Применяем поиск без учета регистра
    if search:
        search_lower = search.lower()
        filtered_employees = []
        for employee in all_employees:
            if (search_lower in employee.full_name.lower() or 
                search_lower in employee.position.lower() or 
                search_lower in employee.phone.lower() or 
                search_lower in employee.email.lower()):
                filtered_employees.append(employee)
        all_employees = filtered_employees
    
    # Применяем сортировку
    if sort_field in ['full_name', 'position', 'gender', 'phone', 'email', 'hire_date', 'on_probation']:
        reverse = (sort_order == 'desc')
        
        # Специальная обработка для разных типов данных
        if sort_field == 'hire_date':
            all_employees.sort(key=lambda x: getattr(x, sort_field), reverse=reverse)
        elif sort_field == 'on_probation':
            all_employees.sort(key=lambda x: str(getattr(x, sort_field)), reverse=reverse)
        else:
            all_employees.sort(key=lambda x: getattr(x, sort_field).lower() if getattr(x, sort_field) else '', reverse=reverse)
    
    # Пагинация вручную
    total = len(all_employees)
    start = (page - 1) * per_page
    end = start + per_page
    employees_page = all_employees[start:end]
    
    # Создаем объект пагинации вручную
    class Pagination:
        def __init__(self, items, page, per_page, total):
            self.items = items
            self.page = page
            self.per_page = per_page
            self.total = total
            self.pages = (total + per_page - 1) // per_page if per_page > 0 else 1
            
        @property
        def has_prev(self):
            return self.page > 1
            
        @property
        def has_next(self):
            return self.page < self.pages
            
        @property
        def prev_num(self):
            return self.page - 1
            
        @property
        def next_num(self):
            return self.page + 1
    
    employees_paginated = Pagination(employees_page, page, per_page, total)
    
    return render_template('employees.html', 
                         employees=employees_paginated,
                         search=search,
                         sort_field=sort_field,
                         sort_order=sort_order,
                         is_authenticated='user_id' in session,
                         is_hr=session.get('is_hr', False))

@app.route('/add_employee', methods=['GET', 'POST'])
def add_employee():
    if 'user_id' not in session or not session.get('is_hr'):
        flash('Требуются права кадровика', 'error')
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        errors = validate_employee_data(request.form)
        if errors:
            for error in errors:
                flash(error, 'error')
            return render_template('edit_employee.html')
        
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
            flash(f'Ошибка при добавлении сотрудника: {str(e)}', 'error')
    
    return render_template('edit_employee.html')

@app.route('/edit_employee/<int:employee_id>', methods=['GET', 'POST'])
def edit_employee(employee_id):
    if 'user_id' not in session or not session.get('is_hr'):
        flash('Требуются права кадровика', 'error')
        return redirect(url_for('login'))
    
    employee = Employee.query.get_or_404(employee_id)
    
    if request.method == 'POST':
        errors = validate_employee_data(request.form)
        if errors:
            for error in errors:
                flash(error, 'error')
            return render_template('edit_employee.html', employee=employee)
        
        try:
            employee.full_name = request.form['full_name']
            employee.position = request.form['position']
            employee.gender = request.form['gender']
            employee.phone = request.form['phone']
            employee.email = request.form['email']
            employee.on_probation = 'on_probation' in request.form
            employee.hire_date = datetime.strptime(request.form['hire_date'], '%Y-%m-%d')
            
            db.session.commit()
            flash('Данные сотрудника обновлены', 'success')
            return redirect(url_for('employees'))
        except Exception as e:
            flash(f'Ошибка при обновлении данных: {str(e)}', 'error')
    
    return render_template('edit_employee.html', employee=employee)

@app.route('/delete_employee/<int:employee_id>')
def delete_employee(employee_id):
    if 'user_id' not in session or not session.get('is_hr'):
        flash('Требуются права кадровика', 'error')
        return redirect(url_for('login'))
    
    employee = Employee.query.get_or_404(employee_id)
    db.session.delete(employee)
    db.session.commit()
    flash('Сотрудник удален', 'success')
    return redirect(url_for('employees'))

def init_db():
    with app.app_context():
        # Удаляем все таблицы и создаем заново
        db.drop_all()
        db.create_all()
        
        print("✅ База данных пересоздана")
        
        # Создаем тестовых пользователей (кадровиков)
        admin = User(login='admin', is_hr=True)
        admin.set_password('admin123')
        db.session.add(admin)
        
        angelina = User(login='angelkuz', is_hr=True)
        angelina.set_password('02042004')
        db.session.add(angelina)
        
        # Добавляем обычных пользователей без прав кадровика
        user1 = User(login='user1', is_hr=False)
        user1.set_password('user123')
        db.session.add(user1)
        
        test_user = User(login='test', is_hr=False)
        test_user.set_password('test123')
        db.session.add(test_user)
        
        db.session.commit()
        print("✅ Созданы пользователи:")
        print("   👑 Кадровики:")
        print("      - login: admin, password: admin123")
        print("      - login: angelkuz, password: 02042004")
        print("   👤 Пользователи:")
        print("      - login: user1, password: user123")
        print("      - login: test, password: test123")
        
        # Создаем тестовых сотрудников из фиксированного списка
        if Employee.query.count() == 0:
            employees_data = get_employees_data()
            for data in employees_data:
                employee = Employee(
                    full_name=data['full_name'],
                    position=data['position'],
                    gender=data['gender'],
                    phone=data['phone'],
                    email=data['email'],
                    on_probation=data['on_probation'],
                    hire_date=datetime.strptime(data['hire_date'], '%Y-%m-%d')
                )
                db.session.add(employee)
            db.session.commit()
            print(f"✅ Создано {len(employees_data)} тестовых сотрудников с нормальными ФИО")

if __name__ == '__main__':
    init_db()
    app.run(debug=True)