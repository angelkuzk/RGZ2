from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os
import re

app = Flask(__name__)

# Для PythonAnywhere используем переменные окружения напрямую
app.secret_key = os.environ.get('SECRET_KEY', 'production-secret-key-2025')

# Конфигурация PostgreSQL для PythonAnywhere
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Модели
class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    login = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Employee(db.Model):
    __tablename__ = 'employees'
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(100), nullable=False)
    position = db.Column(db.String(100), nullable=False)
    gender = db.Column(db.String(10), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    email = db.Column(db.String(100), nullable=False)
    on_probation = db.Column(db.Boolean, default=False)
    hire_date = db.Column(db.Date, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

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

@app.route('/')
def index():
    try:
        employees_count = Employee.query.count()
        users_count = User.query.count()
        return render_template('index.html', 
                             employees_count=employees_count,
                             users_count=users_count)
    except Exception as e:
        return render_template('index.html', 
                             employees_count=0,
                             users_count=0)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        login = request.form.get('login')
        password = request.form.get('password')
        
        is_valid, message = validate_credentials(login, password)
        if not is_valid:
            flash(message, 'error')
            return render_template('login.html')
        
        try:
            user = User.query.filter_by(login=login).first()
            if user and user.check_password(password):
                session['user_id'] = user.id
                session['user_login'] = user.login
                flash('Успешный вход!', 'success')
                return redirect(url_for('employees'))
            else:
                flash('Неверный логин или пароль', 'error')
        except Exception as e:
            flash('Ошибка при входе в систему', 'error')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Вы вышли из системы', 'info')
    return redirect(url_for('index'))

@app.route('/delete_account', methods=['POST'])
def delete_account():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    try:
        user = User.query.get(session['user_id'])
        if user:
            db.session.delete(user)
            db.session.commit()
            session.clear()
            flash('Ваш аккаунт удален', 'info')
    except Exception as e:
        flash('Ошибка при удалении аккаунта', 'error')
    
    return redirect(url_for('index'))

@app.route('/employees')
def employees():
    try:
        page = request.args.get('page', 1, type=int)
        per_page = 20
        search = request.args.get('search', '')
        sort_field = request.args.get('sort', 'id')
        sort_order = request.args.get('order', 'asc')
        
        query = Employee.query
        
        if search:
            search_filter = (
                Employee.full_name.ilike(f'%{search}%') |
                Employee.position.ilike(f'%{search}%') |
                Employee.phone.ilike(f'%{search}%') |
                Employee.email.ilike(f'%{search}%')
            )
            query = query.filter(search_filter)
        
        # Сортировка
        if sort_field in ['full_name', 'position', 'gender', 'phone', 'email', 'hire_date', 'on_probation']:
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
    except Exception as e:
        flash('Ошибка при загрузке списка сотрудников', 'error')
        return redirect(url_for('index'))

@app.route('/add_employee', methods=['GET', 'POST'])
def add_employee():
    if 'user_id' not in session:
        flash('Требуется авторизация', 'error')
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
    if 'user_id' not in session:
        flash('Требуется авторизация', 'error')
        return redirect(url_for('login'))
    
    try:
        employee = Employee.query.get_or_404(employee_id)
    except Exception as e:
        flash('Сотрудник не найден', 'error')
        return redirect(url_for('employees'))
    
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
    if 'user_id' not in session:
        flash('Требуется авторизация', 'error')
        return redirect(url_for('login'))
    
    try:
        employee = Employee.query.get_or_404(employee_id)
        db.session.delete(employee)
        db.session.commit()
        flash('Сотрудник удален', 'success')
    except Exception as e:
        flash('Ошибка при удалении сотрудника', 'error')
    
    return redirect(url_for('employees'))

def init_db():
    with app.app_context():
        try:
            db.create_all()
            
            if User.query.count() == 0:
                admin = User(login='admin')
                admin.set_password('admin123')
                db.session.add(admin)
                
                angelina = User(login='angelkuz')
                angelina.set_password('02042004')
                db.session.add(angelina)
                
                db.session.commit()
                print("✅ Созданы пользователи:")
                print("   - login: admin, password: admin123")
                print("   - login: angelkuz, password: 02042004")
            
            # Создаем тестовых сотрудников
            if Employee.query.count() == 0:
                from faker import Faker
                fake = Faker('ru_RU')
                
                positions = ['Менеджер', 'Разработчик', 'Аналитик', 'Дизайнер', 'Тестировщик', 'Бухгалтер']
                
                employees = []
                for i in range(100):  
                    employee = Employee(
                        full_name=fake.name(),
                        position=fake.random.choice(positions),
                        gender=fake.random.choice(['male', 'female']),
                        phone=fake.phone_number(),
                        email=fake.email(),
                        on_probation=fake.boolean(chance_of_getting_true=30),
                        hire_date=fake.date_between(start_date='-3y', end_date='today')
                    )
                    employees.append(employee)
                
                db.session.add_all(employees)
                db.session.commit()
                print("✅ Создано 100 тестовых сотрудников")
                
        except Exception as e:
            print(f"❌ Ошибка инициализации БД: {e}")

if __name__ == '__main__':
    init_db()
    app.run(debug=False)