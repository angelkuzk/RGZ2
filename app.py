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
        # Руководство
        {'full_name': 'Иванов Александр Сергеевич', 'position': 'Директор', 'gender': 'male', 'phone': '+7-495-100-10-01', 'email': 'ivanov@company.com', 'on_probation': False, 'hire_date': '2018-03-15'},
        {'full_name': 'Петрова Елена Владимировна', 'position': 'Заместитель директора', 'gender': 'female', 'phone': '+7-495-100-10-02', 'email': 'petrova@company.com', 'on_probation': False, 'hire_date': '2019-06-20'},
        {'full_name': 'Сидоров Дмитрий Николаевич', 'position': 'Начальник отдела', 'gender': 'male', 'phone': '+7-495-100-10-03', 'email': 'sidorov@company.com', 'on_probation': False, 'hire_date': '2018-11-10'},
        
        # Отдел разработки
        {'full_name': 'Козлов Артем Игоревич', 'position': 'Ведущий разработчик', 'gender': 'male', 'phone': '+7-495-100-10-04', 'email': 'kozlov@company.com', 'on_probation': False, 'hire_date': '2020-01-12'},
        {'full_name': 'Федорова Мария Петровна', 'position': 'Разработчик', 'gender': 'female', 'phone': '+7-495-100-10-05', 'email': 'fedorova@company.com', 'on_probation': False, 'hire_date': '2020-03-18'},
        {'full_name': 'Никитин Сергей Александрович', 'position': 'Разработчик', 'gender': 'male', 'phone': '+7-495-100-10-06', 'email': 'nikitin@company.com', 'on_probation': False, 'hire_date': '2021-07-22'},
        {'full_name': 'Орлова Анна Дмитриевна', 'position': 'Разработчик', 'gender': 'female', 'phone': '+7-495-100-10-07', 'email': 'orlova@company.com', 'on_probation': False, 'hire_date': '2021-09-14'},
        {'full_name': 'Белов Павел Олегович', 'position': 'Младший разработчик', 'gender': 'male', 'phone': '+7-495-100-10-08', 'email': 'belov@company.com', 'on_probation': True, 'hire_date': '2023-11-05'},
        {'full_name': 'Громова Ирина Викторовна', 'position': 'Младший разработчик', 'gender': 'female', 'phone': '+7-495-100-10-09', 'email': 'gromova@company.com', 'on_probation': True, 'hire_date': '2023-12-10'},
        {'full_name': 'Данилов Максим Сергеевич', 'position': 'Инженер', 'gender': 'male', 'phone': '+7-495-100-10-10', 'email': 'danilov@company.com', 'on_probation': False, 'hire_date': '2020-08-30'},
        
        # Отдел тестирования
        {'full_name': 'Семенова Ольга Игоревна', 'position': 'Ведущий тестировщик', 'gender': 'female', 'phone': '+7-495-100-10-11', 'email': 'semenova@company.com', 'on_probation': False, 'hire_date': '2019-04-25'},
        {'full_name': 'Тихонов Андрей Владимирович', 'position': 'Тестировщик', 'gender': 'male', 'phone': '+7-495-100-10-12', 'email': 'tikhonov@company.com', 'on_probation': False, 'hire_date': '2020-02-14'},
        {'full_name': 'Устинова Татьяна Михайловна', 'position': 'Тестировщик', 'gender': 'female', 'phone': '+7-495-100-10-13', 'email': 'ustinova@company.com', 'on_probation': False, 'hire_date': '2021-05-19'},
        {'full_name': 'Филиппов Алексей Николаевич', 'position': 'Тестировщик', 'gender': 'male', 'phone': '+7-495-100-10-14', 'email': 'filippov@company.com', 'on_probation': True, 'hire_date': '2023-10-08'},
        
        # Отдел аналитики
        {'full_name': 'Харитонова Екатерина Сергеевна', 'position': 'Ведущий аналитик', 'gender': 'female', 'phone': '+7-495-100-10-15', 'email': 'kharitonova@company.com', 'on_probation': False, 'hire_date': '2018-09-12'},
        {'full_name': 'Цветков Иван Петрович', 'position': 'Аналитик', 'gender': 'male', 'phone': '+7-495-100-10-16', 'email': 'tsvetkov@company.com', 'on_probation': False, 'hire_date': '2020-11-03'},
        {'full_name': 'Шестакова Людмила Анатольевна', 'position': 'Аналитик', 'gender': 'female', 'phone': '+7-495-100-10-17', 'email': 'shestakova@company.com', 'on_probation': False, 'hire_date': '2021-03-28'},
        
        # Отдел дизайна
        {'full_name': 'Щербаков Денис Олегович', 'position': 'Ведущий дизайнер', 'gender': 'male', 'phone': '+7-495-100-10-18', 'email': 'shcherbakov@company.com', 'on_probation': False, 'hire_date': '2019-07-15'},
        {'full_name': 'Яковлева Наталья Владимировна', 'position': 'Дизайнер', 'gender': 'female', 'phone': '+7-495-100-10-19', 'email': 'yakovleva@company.com', 'on_probation': False, 'hire_date': '2020-04-22'},
        {'full_name': 'Абрамов Артем Ильич', 'position': 'Дизайнер', 'gender': 'male', 'phone': '+7-495-100-10-20', 'email': 'abramov@company.com', 'on_probation': True, 'hire_date': '2023-08-14'},
        
        # Отдел маркетинга
        {'full_name': 'Борисова Светлана Александровна', 'position': 'Руководитель маркетинга', 'gender': 'female', 'phone': '+7-495-100-10-21', 'email': 'borisova@company.com', 'on_probation': False, 'hire_date': '2018-12-05'},
        {'full_name': 'Волков Михаил Юрьевич', 'position': 'Маркетолог', 'gender': 'male', 'phone': '+7-495-100-10-22', 'email': 'volkov@company.com', 'on_probation': False, 'hire_date': '2020-06-18'},
        {'full_name': 'Григорьева Анастасия Павловна', 'position': 'Маркетолог', 'gender': 'female', 'phone': '+7-495-100-10-23', 'email': 'grigoreva@company.com', 'on_probation': False, 'hire_date': '2021-09-30'},
        {'full_name': 'Дмитриев Константин Викторович', 'position': 'Маркетолог', 'gender': 'male', 'phone': '+7-495-100-10-24', 'email': 'dmitriev@company.com', 'on_probation': True, 'hire_date': '2023-11-20'},
        
        # Отдел продаж
        {'full_name': 'Ефимова Ольга Сергеевна', 'position': 'Руководитель продаж', 'gender': 'female', 'phone': '+7-495-100-10-25', 'email': 'efimova@company.com', 'on_probation': False, 'hire_date': '2019-02-14'},
        {'full_name': 'Жуков Алексей Дмитриевич', 'position': 'Менеджер по продажам', 'gender': 'male', 'phone': '+7-495-100-10-26', 'email': 'zhukov@company.com', 'on_probation': False, 'hire_date': '2020-08-11'},
        {'full_name': 'Зайцева Марина Игоревна', 'position': 'Менеджер по продажам', 'gender': 'female', 'phone': '+7-495-100-10-27', 'email': 'zaitseva@company.com', 'on_probation': False, 'hire_date': '2021-01-25'},
        {'full_name': 'Ильин Павел Анатольевич', 'position': 'Менеджер по продажам', 'gender': 'male', 'phone': '+7-495-100-10-28', 'email': 'ilin@company.com', 'on_probation': True, 'hire_date': '2023-10-15'},
        
        # Бухгалтерия
        {'full_name': 'Карпова Виктория Олеговна', 'position': 'Главный бухгалтер', 'gender': 'female', 'phone': '+7-495-100-10-29', 'email': 'karpova@company.com', 'on_probation': False, 'hire_date': '2018-05-20'},
        {'full_name': 'Ларин Александр Владимирович', 'position': 'Бухгалтер', 'gender': 'male', 'phone': '+7-495-100-10-30', 'email': 'larin@company.com', 'on_probation': False, 'hire_date': '2019-11-08'},
        {'full_name': 'Максимова Елена Николаевна', 'position': 'Бухгалтер', 'gender': 'female', 'phone': '+7-495-100-10-31', 'email': 'maksimova@company.com', 'on_probation': False, 'hire_date': '2020-07-12'},
        
        # Отдел кадров
        {'full_name': 'Носова Ирина Васильевна', 'position': 'Специалист по кадрам', 'gender': 'female', 'phone': '+7-495-100-10-32', 'email': 'nosova@company.com', 'on_probation': False, 'hire_date': '2019-03-18'},
        {'full_name': 'Овчинников Денис Сергеевич', 'position': 'Специалист по кадрам', 'gender': 'male', 'phone': '+7-495-100-10-33', 'email': 'ovchinnikov@company.com', 'on_probation': False, 'hire_date': '2020-09-22'},
        {'full_name': 'Павлова Анна Александровна', 'position': 'Специалист по кадрам', 'gender': 'female', 'phone': '+7-495-100-10-34', 'email': 'pavlova@company.com', 'on_probation': True, 'hire_date': '2023-12-01'},
        
        # Административный отдел
        {'full_name': 'Романов Кирилл Игоревич', 'position': 'Администратор', 'gender': 'male', 'phone': '+7-495-100-10-35', 'email': 'romanov@company.com', 'on_probation': False, 'hire_date': '2020-02-10'},
        {'full_name': 'Савельева Татьяна Дмитриевна', 'position': 'Администратор', 'gender': 'female', 'phone': '+7-495-100-10-36', 'email': 'savelieva@company.com', 'on_probation': False, 'hire_date': '2021-04-15'},
        
        # Технический отдел
        {'full_name': 'Тарасов Владимир Петрович', 'position': 'Системный администратор', 'gender': 'male', 'phone': '+7-495-100-10-37', 'email': 'tarasov@company.com', 'on_probation': False, 'hire_date': '2018-08-12'},
        {'full_name': 'Уварова Мария Сергеевна', 'position': 'Технический специалист', 'gender': 'female', 'phone': '+7-495-100-10-38', 'email': 'uvarova@company.com', 'on_probation': False, 'hire_date': '2020-10-05'},
        
        # Дополнительные сотрудники
        {'full_name': 'Фомин Алексей Николаевич', 'position': 'Разработчик', 'gender': 'male', 'phone': '+7-495-100-10-39', 'email': 'fomin@company.com', 'on_probation': False, 'hire_date': '2021-06-20'},
        {'full_name': 'Хохлов Дмитрий Владимирович', 'position': 'Разработчик', 'gender': 'male', 'phone': '+7-495-100-10-40', 'email': 'khokhlov@company.com', 'on_probation': False, 'hire_date': '2021-08-14'},
        {'full_name': 'Царева Ольга Игоревна', 'position': 'Аналитик', 'gender': 'female', 'phone': '+7-495-100-10-41', 'email': 'tsareva@company.com', 'on_probation': False, 'hire_date': '2022-01-10'},
        {'full_name': 'Чернов Артем Сергеевич', 'position': 'Тестировщик', 'gender': 'male', 'phone': '+7-495-100-10-42', 'email': 'chernov@company.com', 'on_probation': True, 'hire_date': '2023-09-05'},
        {'full_name': 'Широков Иван Алексеевич', 'position': 'Дизайнер', 'gender': 'male', 'phone': '+7-495-100-10-43', 'email': 'shirokov@company.com', 'on_probation': False, 'hire_date': '2020-12-18'},
        {'full_name': 'Щукина Екатерина Викторовна', 'position': 'Маркетолог', 'gender': 'female', 'phone': '+7-495-100-10-44', 'email': 'shchukina@company.com', 'on_probation': False, 'hire_date': '2021-02-22'},
        {'full_name': 'Юдин Павел Олегович', 'position': 'Менеджер по продажам', 'gender': 'male', 'phone': '+7-495-100-10-45', 'email': 'yudin@company.com', 'on_probation': True, 'hire_date': '2023-11-30'},
        {'full_name': 'Яковлев Андрей Николаевич', 'position': 'Бухгалтер', 'gender': 'male', 'phone': '+7-495-100-10-46', 'email': 'yakovlev@company.com', 'on_probation': False, 'hire_date': '2019-10-15'},
        {'full_name': 'Антонова Светлана Дмитриевна', 'position': 'Специалист по кадрам', 'gender': 'female', 'phone': '+7-495-100-10-47', 'email': 'antonova@company.com', 'on_probation': False, 'hire_date': '2020-05-20'},
        {'full_name': 'Беляев Михаил Сергеевич', 'position': 'Разработчик', 'gender': 'male', 'phone': '+7-495-100-10-48', 'email': 'belyaev@company.com', 'on_probation': False, 'hire_date': '2021-07-08'},
        {'full_name': 'Васнецова Анастасия Игоревна', 'position': 'Аналитик', 'gender': 'female', 'phone': '+7-495-100-10-49', 'email': 'vasnetsova@company.com', 'on_probation': False, 'hire_date': '2022-03-12'},
        {'full_name': 'Горбунов Денис Владимирович', 'position': 'Тестировщик', 'gender': 'male', 'phone': '+7-495-100-10-50', 'email': 'gorbunov@company.com', 'on_probation': True, 'hire_date': '2023-10-25'},
        {'full_name': 'Демин Алексей Петрович', 'position': 'Дизайнер', 'gender': 'male', 'phone': '+7-495-100-10-51', 'email': 'demin@company.com', 'on_probation': False, 'hire_date': '2020-11-30'},
        {'full_name': 'Ершова Марина Александровна', 'position': 'Маркетолог', 'gender': 'female', 'phone': '+7-495-100-10-52', 'email': 'ershova@company.com', 'on_probation': False, 'hire_date': '2021-04-05'},
        {'full_name': 'Жданов Игорь Викторович', 'position': 'Менеджер по продажам', 'gender': 'male', 'phone': '+7-495-100-10-53', 'email': 'zhdanov@company.com', 'on_probation': True, 'hire_date': '2023-12-15'},
        {'full_name': 'Зимин Сергей Олегович', 'position': 'Бухгалтер', 'gender': 'male', 'phone': '+7-495-100-10-54', 'email': 'zimin@company.com', 'on_probation': False, 'hire_date': '2019-08-22'},
        {'full_name': 'Исакова Юлия Владимировна', 'position': 'Специалист по кадрам', 'gender': 'female', 'phone': '+7-495-100-10-55', 'email': 'isakova@company.com', 'on_probation': False, 'hire_date': '2020-06-14'},
        {'full_name': 'Калашников Артем Дмитриевич', 'position': 'Разработчик', 'gender': 'male', 'phone': '+7-495-100-10-56', 'email': 'kalashnikov@company.com', 'on_probation': False, 'hire_date': '2021-09-28'},
        {'full_name': 'Лебедева Ольга Сергеевна', 'position': 'Аналитик', 'gender': 'female', 'phone': '+7-495-100-10-57', 'email': 'lebedeva@company.com', 'on_probation': False, 'hire_date': '2022-02-18'},
        {'full_name': 'Морозов Дмитрий Игоревич', 'position': 'Тестировщик', 'gender': 'male', 'phone': '+7-495-100-10-58', 'email': 'morozov@company.com', 'on_probation': True, 'hire_date': '2023-11-10'},
        {'full_name': 'Некрасова Анна Владимировна', 'position': 'Дизайнер', 'gender': 'female', 'phone': '+7-495-100-10-59', 'email': 'nekrasova@company.com', 'on_probation': False, 'hire_date': '2020-12-03'},
        {'full_name': 'Осипов Владимир Александрович', 'position': 'Маркетолог', 'gender': 'male', 'phone': '+7-495-100-10-60', 'email': 'osipov@company.com', 'on_probation': False, 'hire_date': '2021-05-25'},
        {'full_name': 'Поляков Илья Сергеевич', 'position': 'Менеджер по продажам', 'gender': 'male', 'phone': '+7-495-100-10-61', 'email': 'polyakov@company.com', 'on_probation': True, 'hire_date': '2023-10-20'},
        {'full_name': 'Рожкова Елена Викторовна', 'position': 'Бухгалтер', 'gender': 'female', 'phone': '+7-495-100-10-62', 'email': 'rozhkova@company.com', 'on_probation': False, 'hire_date': '2019-07-30'},
        {'full_name': 'Сазонов Алексей Николаевич', 'position': 'Специалист по кадрам', 'gender': 'male', 'phone': '+7-495-100-10-63', 'email': 'sazonov@company.com', 'on_probation': False, 'hire_date': '2020-08-08'},
        {'full_name': 'Тихомирова Ирина Олеговна', 'position': 'Разработчик', 'gender': 'female', 'phone': '+7-495-100-10-64', 'email': 'tikhomirova@company.com', 'on_probation': False, 'hire_date': '2021-11-12'},
        {'full_name': 'Ушаков Денис Владимирович', 'position': 'Аналитик', 'gender': 'male', 'phone': '+7-495-100-10-65', 'email': 'ushakov@company.com', 'on_probation': False, 'hire_date': '2022-04-20'},
        {'full_name': 'Федосеев Максим Игоревич', 'position': 'Тестировщик', 'gender': 'male', 'phone': '+7-495-100-10-66', 'email': 'fedoseev@company.com', 'on_probation': True, 'hire_date': '2023-09-15'},
        {'full_name': 'Хромова Наталья Александровна', 'position': 'Дизайнер', 'gender': 'female', 'phone': '+7-495-100-10-67', 'email': 'khromova@company.com', 'on_probation': False, 'hire_date': '2021-01-08'},
        {'full_name': 'Цыганков Павел Сергеевич', 'position': 'Маркетолог', 'gender': 'male', 'phone': '+7-495-100-10-68', 'email': 'tsygankov@company.com', 'on_probation': False, 'hire_date': '2021-06-14'},
        {'full_name': 'Чеботарев Андрей Викторович', 'position': 'Менеджер по продажам', 'gender': 'male', 'phone': '+7-495-100-10-69', 'email': 'chebotarev@company.com', 'on_probation': True, 'hire_date': '2023-12-05'},
        {'full_name': 'Шмелева Оксана Дмитриевна', 'position': 'Бухгалтер', 'gender': 'female', 'phone': '+7-495-100-10-70', 'email': 'shmeleva@company.com', 'on_probation': False, 'hire_date': '2019-09-18'},
        {'full_name': 'Щедрин Владислав Олегович', 'position': 'Специалист по кадрам', 'gender': 'male', 'phone': '+7-495-100-10-71', 'email': 'shchedrin@company.com', 'on_probation': False, 'hire_date': '2020-07-22'},
        {'full_name': 'Юрьева Татьяна Сергеевна', 'position': 'Разработчик', 'gender': 'female', 'phone': '+7-495-100-10-72', 'email': 'yureva@company.com', 'on_probation': False, 'hire_date': '2021-10-30'},
        {'full_name': 'Яшин Алексей Дмитриевич', 'position': 'Аналитик', 'gender': 'male', 'phone': '+7-495-100-10-73', 'email': 'yashin@company.com', 'on_probation': False, 'hire_date': '2022-05-12'},
        {'full_name': 'Алексеев Константин Игоревич', 'position': 'Тестировщик', 'gender': 'male', 'phone': '+7-495-100-10-74', 'email': 'alekseev@company.com', 'on_probation': True, 'hire_date': '2023-08-28'},
        {'full_name': 'Богданова Мария Владимировна', 'position': 'Дизайнер', 'gender': 'female', 'phone': '+7-495-100-10-75', 'email': 'bogdanova@company.com', 'on_probation': False, 'hire_date': '2021-02-14'},
        {'full_name': 'Воронов Игорь Александрович', 'position': 'Маркетолог', 'gender': 'male', 'phone': '+7-495-100-10-76', 'email': 'voronov@company.com', 'on_probation': False, 'hire_date': '2021-07-20'},
        {'full_name': 'Гусев Дмитрий Сергеевич', 'position': 'Менеджер по продажам', 'gender': 'male', 'phone': '+7-495-100-10-77', 'email': 'gusev@company.com', 'on_probation': True, 'hire_date': '2023-11-25'},
        {'full_name': 'Давыдова Екатерина Игоревна', 'position': 'Бухгалтер', 'gender': 'female', 'phone': '+7-495-100-10-78', 'email': 'davydova@company.com', 'on_probation': False, 'hire_date': '2019-12-10'},
        {'full_name': 'Егоров Артем Владимирович', 'position': 'Специалист по кадрам', 'gender': 'male', 'phone': '+7-495-100-10-79', 'email': 'egorov@company.com', 'on_probation': False, 'hire_date': '2020-09-05'},
        {'full_name': 'Журавлева Надежда Петровна', 'position': 'Разработчик', 'gender': 'female', 'phone': '+7-495-100-10-80', 'email': 'zhuravleva@company.com', 'on_probation': False, 'hire_date': '2021-12-18'},
        {'full_name': 'Зуев Александр Олегович', 'position': 'Аналитик', 'gender': 'male', 'phone': '+7-495-100-10-81', 'email': 'zuev@company.com', 'on_probation': False, 'hire_date': '2022-06-22'},
        {'full_name': 'Игнатьев Сергей Викторович', 'position': 'Тестировщик', 'gender': 'male', 'phone': '+7-495-100-10-82', 'email': 'ignatev@company.com', 'on_probation': True, 'hire_date': '2023-10-10'},
        {'full_name': 'Казакова Анна Александровна', 'position': 'Дизайнер', 'gender': 'female', 'phone': '+7-495-100-10-83', 'email': 'kazakova@company.com', 'on_probation': False, 'hire_date': '2021-03-28'},
        {'full_name': 'Логинов Владимир Дмитриевич', 'position': 'Маркетолог', 'gender': 'male', 'phone': '+7-495-100-10-84', 'email': 'loginov@company.com', 'on_probation': False, 'hire_date': '2021-08-15'},
        {'full_name': 'Матвеев Илья Сергеевич', 'position': 'Менеджер по продажам', 'gender': 'male', 'phone': '+7-495-100-10-85', 'email': 'matveev@company.com', 'on_probation': True, 'hire_date': '2023-12-20'},
        {'full_name': 'Новикова Ольга Викторовна', 'position': 'Бухгалтер', 'gender': 'female', 'phone': '+7-495-100-10-86', 'email': 'novikova@company.com', 'on_probation': False, 'hire_date': '2020-01-15'},
        {'full_name': 'Орлов Денис Александрович', 'position': 'Специалист по кадрам', 'gender': 'male', 'phone': '+7-495-100-10-87', 'email': 'orlov@company.com', 'on_probation': False, 'hire_date': '2020-10-12'},
        {'full_name': 'Петухова Ирина Сергеевна', 'position': 'Разработчик', 'gender': 'female', 'phone': '+7-495-100-10-88', 'email': 'petukhova@company.com', 'on_probation': False, 'hire_date': '2022-01-25'},
        {'full_name': 'Рубцов Алексей Игоревич', 'position': 'Аналитик', 'gender': 'male', 'phone': '+7-495-100-10-89', 'email': 'rubtsov@company.com', 'on_probation': False, 'hire_date': '2022-07-30'},
        {'full_name': 'Селиванова Марина Дмитриевна', 'position': 'Тестировщик', 'gender': 'female', 'phone': '+7-495-100-10-90', 'email': 'selivanova@company.com', 'on_probation': True, 'hire_date': '2023-09-20'},
        {'full_name': 'Трофимов Артем Владимирович', 'position': 'Дизайнер', 'gender': 'male', 'phone': '+7-495-100-10-91', 'email': 'trofimov@company.com', 'on_probation': False, 'hire_date': '2021-04-10'},
        {'full_name': 'Успенская Юлия Александровна', 'position': 'Маркетолог', 'gender': 'female', 'phone': '+7-495-100-10-92', 'email': 'uspenskaya@company.com', 'on_probation': False, 'hire_date': '2021-09-05'},
        {'full_name': 'Фролов Иван Сергеевич', 'position': 'Менеджер по продажам', 'gender': 'male', 'phone': '+7-495-100-10-93', 'email': 'frolov@company.com', 'on_probation': True, 'hire_date': '2023-11-15'},
        {'full_name': 'Хабаров Дмитрий Олегович', 'position': 'Бухгалтер', 'gender': 'male', 'phone': '+7-495-100-10-94', 'email': 'khabarov@company.com', 'on_probation': False, 'hire_date': '2020-02-28'},
        {'full_name': 'Цветаева Елена Викторовна', 'position': 'Специалист по кадрам', 'gender': 'female', 'phone': '+7-495-100-10-95', 'email': 'tsvetaeva@company.com', 'on_probation': False, 'hire_date': '2020-11-08'},
        {'full_name': 'Чижов Андрей Александрович', 'position': 'Разработчик', 'gender': 'male', 'phone': '+7-495-100-10-96', 'email': 'chizhov@company.com', 'on_probation': False, 'hire_date': '2022-02-14'},
        {'full_name': 'Шарова Ольга Игоревна', 'position': 'Аналитик', 'gender': 'female', 'phone': '+7-495-100-10-97', 'email': 'sharova@company.com', 'on_probation': False, 'hire_date': '2022-08-18'},
        {'full_name': 'Щеглов Павел Дмитриевич', 'position': 'Тестировщик', 'gender': 'male', 'phone': '+7-495-100-10-98', 'email': 'shcheglov@company.com', 'on_probation': True, 'hire_date': '2023-10-05'},
        {'full_name': 'Юдина Анна Владимировна', 'position': 'Дизайнер', 'gender': 'female', 'phone': '+7-495-100-10-99', 'email': 'yudina@company.com', 'on_probation': False, 'hire_date': '2021-05-22'},
        {'full_name': 'Якушев Михаил Сергеевич', 'position': 'Маркетолог', 'gender': 'male', 'phone': '+7-495-100-10-00', 'email': 'yakushev@company.com', 'on_probation': False, 'hire_date': '2021-10-12'}
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