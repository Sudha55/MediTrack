#!/usr/bin/env python3
import sqlite3
import os
import hashlib
import secrets
import json
from flask import Flask, jsonify, send_from_directory, request
from flask_cors import CORS
from datetime import datetime, timedelta
from functools import wraps

BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BACKEND_DIR)
FRONTEND_DIR = os.path.join(PROJECT_ROOT, 'frontend')
DEFAULT_DB_PATH = os.path.join(PROJECT_ROOT, 'database', 'hospital_data.db')
DB_PATH = os.environ.get('DATABASE_PATH', DEFAULT_DB_PATH)
SCHEMA_PATH = os.path.join(PROJECT_ROOT, 'database', 'schema.sql')
SAMPLE_DATA_PATH = os.path.join(PROJECT_ROOT, 'database', 'sample_data.sql')
USERS_SCHEMA_PATH = os.path.join(PROJECT_ROOT, 'database', 'users_schema.sql')
APP_ENV = os.environ.get('APP_ENV', 'development').lower()
IS_PRODUCTION = APP_ENV == 'production'
PORT = int(os.environ.get('PORT', '5001'))
HOST = os.environ.get('HOST', '127.0.0.1')
DEFAULT_ADMIN_USERNAME = os.environ.get('DEFAULT_ADMIN_USERNAME', 'admin')
DEFAULT_ADMIN_EMAIL = os.environ.get('DEFAULT_ADMIN_EMAIL', 'admin@meditrack.com')
DEFAULT_ADMIN_FIRST_NAME = os.environ.get('DEFAULT_ADMIN_FIRST_NAME', 'Admin')
DEFAULT_ADMIN_LAST_NAME = os.environ.get('DEFAULT_ADMIN_LAST_NAME', 'User')
DEFAULT_ADMIN_PASSWORD = os.environ.get('DEFAULT_ADMIN_PASSWORD')
LOCAL_DEV_ADMIN_PASSWORD = 'admin123'
LOCAL_DEV_SECRET_KEY = 'meditrack-local-dev-secret-key'
db_initialized = False

app = Flask(__name__, static_folder=FRONTEND_DIR, static_url_path='')
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY') or (
    LOCAL_DEV_SECRET_KEY if not IS_PRODUCTION else secrets.token_hex(32)
)

CORS(app, supports_credentials=True)

# In-memory token store (replace with Redis in production)
active_tokens = {}

def get_db_connection():
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys = ON')
    return conn

def hash_password(password):
    salt = secrets.token_hex(16)
    pwd_hash = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000)
    return f"{salt}${pwd_hash.hex()}"

def verify_password(stored_hash, password):
    try:
        salt, pwd_hash = stored_hash.split('$')
        new_hash = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000).hex()
        return new_hash == pwd_hash
    except:
        return False

def generate_token():
    return secrets.token_urlsafe(32)

def require_auth(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        
        if not token or token not in active_tokens:
            return jsonify({'error': 'Unauthorized', 'code': 'AUTH_REQUIRED'}), 401
        
        return f(*args, **kwargs)
    return decorated_function

def get_current_user():
    token = request.headers.get('Authorization', '').replace('Bearer ', '')
    if token in active_tokens:
        return active_tokens[token]
    return None

def validate_email(email):
    """Simple email validation"""
    return '@' in email and '.' in email

def validate_date(date_str):
    """Validate date format YYYY-MM-DD"""
    try:
        datetime.strptime(date_str, '%Y-%m-%d')
        return True
    except:
        return False

def get_seed_admin_password():
    if DEFAULT_ADMIN_PASSWORD:
        return DEFAULT_ADMIN_PASSWORD
    if IS_PRODUCTION:
        return None
    return LOCAL_DEV_ADMIN_PASSWORD

def init_db():
    global db_initialized
    if db_initialized:
        return

    print("Initializing database...")
    db_dir = os.path.dirname(DB_PATH)
    if not os.path.exists(db_dir):
        os.makedirs(db_dir)
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    with open(SCHEMA_PATH, 'r') as f:
        cursor.executescript(f.read())
    
    with open(USERS_SCHEMA_PATH, 'r') as f:
        cursor.executescript(f.read())
    
    cursor.execute('SELECT COUNT(*) FROM patients')
    count = cursor.fetchone()[0]
    
    if count == 0:
        with open(SAMPLE_DATA_PATH, 'r') as f:
            cursor.executescript(f.read())
    
    cursor.execute('SELECT COUNT(*) FROM users')
    user_count = cursor.fetchone()[0]
    
    if user_count == 0:
        seed_admin_password = get_seed_admin_password()
        if seed_admin_password:
            admin_password = hash_password(seed_admin_password)
            cursor.execute('''
                INSERT INTO users (username, email, password_hash, first_name, last_name, role)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                DEFAULT_ADMIN_USERNAME,
                DEFAULT_ADMIN_EMAIL,
                admin_password,
                DEFAULT_ADMIN_FIRST_NAME,
                DEFAULT_ADMIN_LAST_NAME,
                'admin'
            ))
        else:
            print("Skipping admin bootstrap because DEFAULT_ADMIN_PASSWORD is not set.")
    
    conn.commit()
    conn.close()
    db_initialized = True
    print("Database initialized!")

init_db()

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Resource not found', 'code': 'NOT_FOUND'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error', 'code': 'SERVER_ERROR'}), 500

@app.route('/')
def serve_index():
    return send_from_directory(FRONTEND_DIR, 'index.html')

@app.route('/<path:path>')
def serve_static(path):
    try:
        return send_from_directory(FRONTEND_DIR, path)
    except:
        return send_from_directory(FRONTEND_DIR, 'index.html')

@app.route('/api/auth/register', methods=['POST', 'OPTIONS'])
def register():
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        data = request.get_json()
        
        # Validation
        if not data:
            return jsonify({'error': 'Request body required', 'code': 'INVALID_REQUEST'}), 400
        
        required_fields = ['username', 'email', 'password', 'first_name', 'last_name']
        missing = [f for f in required_fields if not data.get(f)]
        
        if missing:
            return jsonify({
                'error': f'Missing required fields: {", ".join(missing)}',
                'code': 'MISSING_FIELDS',
                'missing_fields': missing
            }), 400
        
        # Validate username
        username = data['username'].strip()
        if len(username) < 3:
            return jsonify({'error': 'Username must be at least 3 characters', 'code': 'INVALID_USERNAME'}), 400
        if len(username) > 50:
            return jsonify({'error': 'Username must be less than 50 characters', 'code': 'INVALID_USERNAME'}), 400
        if not username.isalnum():
            return jsonify({'error': 'Username can only contain letters and numbers', 'code': 'INVALID_USERNAME'}), 400
        
        # Validate email
        email = data['email'].strip()
        if not validate_email(email):
            return jsonify({'error': 'Invalid email format', 'code': 'INVALID_EMAIL'}), 400
        
        # Validate password
        password = data['password']
        if len(password) < 6:
            return jsonify({'error': 'Password must be at least 6 characters', 'code': 'WEAK_PASSWORD'}), 400
        
        # Validate names
        first_name = data['first_name'].strip()
        last_name = data['last_name'].strip()
        
        if not first_name or not last_name:
            return jsonify({'error': 'First and last names required', 'code': 'INVALID_NAME'}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check if user exists
        cursor.execute('SELECT user_id FROM users WHERE username = ? OR email = ?', 
                       (username, email))
        if cursor.fetchone():
            conn.close()
            return jsonify({'error': 'Username or email already exists', 'code': 'USER_EXISTS'}), 409
        
        password_hash = hash_password(password)
        role = data.get('role', 'doctor')
        
        if role not in ['admin', 'doctor', 'billing']:
            return jsonify({'error': 'Invalid role', 'code': 'INVALID_ROLE'}), 400
        
        cursor.execute('''
            INSERT INTO users (username, email, password_hash, first_name, last_name, role)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (username, email, password_hash, first_name, last_name, role))
        
        conn.commit()
        user_id = cursor.lastrowid
        conn.close()
        
        return jsonify({
            'message': 'User registered successfully',
            'user_id': user_id,
            'username': username,
            'code': 'REGISTRATION_SUCCESS'
        }), 201
        
    except Exception as e:
        return jsonify({'error': str(e), 'code': 'SERVER_ERROR'}), 500

@app.route('/api/auth/login', methods=['POST', 'OPTIONS'])
def login():
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'Request body required', 'code': 'INVALID_REQUEST'}), 400
        
        username = data.get('username', '').strip()
        password = data.get('password', '')
        
        if not username or not password:
            return jsonify({'error': 'Username and password required', 'code': 'MISSING_CREDENTIALS'}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
        user = cursor.fetchone()
        
        if not user or not verify_password(user['password_hash'], password):
            conn.close()
            return jsonify({'error': 'Invalid username or password', 'code': 'INVALID_CREDENTIALS'}), 401
        
        cursor.execute('UPDATE users SET last_login = ? WHERE user_id = ?',
                       (datetime.now().isoformat(), user['user_id']))
        conn.commit()
        conn.close()
        
        # Generate token
        token = generate_token()
        active_tokens[token] = {
            'user_id': user['user_id'],
            'username': user['username'],
            'role': user['role'],
            'first_name': user['first_name'],
            'last_name': user['last_name']
        }
        
        return jsonify({
            'message': 'Login successful',
            'token': token,
            'user_id': user['user_id'],
            'username': user['username'],
            'role': user['role'],
            'first_name': user['first_name'],
            'last_name': user['last_name'],
            'code': 'LOGIN_SUCCESS'
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e), 'code': 'SERVER_ERROR'}), 500

@app.route('/api/auth/me', methods=['GET'])
@require_auth
def get_current_user_endpoint():
    user = get_current_user()
    return jsonify(user), 200

@app.route('/api/auth/logout', methods=['POST'])
def logout():
    token = request.headers.get('Authorization', '').replace('Bearer ', '')
    if token in active_tokens:
        del active_tokens[token]
    return jsonify({'message': 'Logged out successfully', 'code': 'LOGOUT_SUCCESS'}), 200

@app.route('/api/patients', methods=['GET'])
@require_auth
def get_patients():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM patients ORDER BY last_name, first_name')
        patients = cursor.fetchall()
        
        result = []
        for patient in patients:
            cursor.execute('SELECT COUNT(*) FROM encounters WHERE patient_id = ?', (patient['patient_id'],))
            encounter_count = cursor.fetchone()[0]
            
            result.append({
                'patient_id': patient['patient_id'],
                'first_name': patient['first_name'],
                'last_name': patient['last_name'],
                'date_of_birth': patient['date_of_birth'],
                'gender': patient['gender'],
                'encounter_count': encounter_count
            })
        
        conn.close()
        return jsonify(result), 200
        
    except Exception as e:
        return jsonify({'error': str(e), 'code': 'SERVER_ERROR'}), 500

@app.route('/api/patients', methods=['POST'])
@require_auth
def add_patient():
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'Request body required', 'code': 'INVALID_REQUEST'}), 400
        
        # Validation
        first_name = data.get('first_name', '').strip()
        last_name = data.get('last_name', '').strip()
        date_of_birth = data.get('date_of_birth', '').strip()
        gender = data.get('gender', '').strip()
        
        errors = {}
        
        if not first_name:
            errors['first_name'] = 'First name required'
        if not last_name:
            errors['last_name'] = 'Last name required'
        if not date_of_birth:
            errors['date_of_birth'] = 'Date of birth required'
        elif not validate_date(date_of_birth):
            errors['date_of_birth'] = 'Invalid date format (YYYY-MM-DD)'
        if not gender or gender not in ['M', 'F', 'Other']:
            errors['gender'] = 'Valid gender required'
        
        if errors:
            return jsonify({'error': 'Validation failed', 'code': 'VALIDATION_ERROR', 'errors': errors}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO patients (first_name, last_name, date_of_birth, gender)
            VALUES (?, ?, ?, ?)
        ''', (first_name, last_name, date_of_birth, gender))
        
        conn.commit()
        patient_id = cursor.lastrowid
        conn.close()
        
        return jsonify({
            'patient_id': patient_id,
            'message': 'Patient added successfully',
            'code': 'PATIENT_CREATED'
        }), 201
        
    except Exception as e:
        return jsonify({'error': str(e), 'code': 'SERVER_ERROR'}), 500

@app.route('/api/patients/<int:patient_id>', methods=['DELETE'])
@require_auth
def delete_patient(patient_id):
    try:
        user = get_current_user()
        if user['role'] != 'admin':
            return jsonify({'error': 'Only admins can delete patients', 'code': 'FORBIDDEN'}), 403
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Verify patient exists
        cursor.execute('SELECT patient_id FROM patients WHERE patient_id = ?', (patient_id,))
        if not cursor.fetchone():
            conn.close()
            return jsonify({'error': 'Patient not found', 'code': 'NOT_FOUND'}), 404
        
        cursor.execute('DELETE FROM diagnoses WHERE encounter_id IN (SELECT encounter_id FROM encounters WHERE patient_id = ?)', (patient_id,))
        cursor.execute('DELETE FROM procedures WHERE encounter_id IN (SELECT encounter_id FROM encounters WHERE patient_id = ?)', (patient_id,))
        cursor.execute('DELETE FROM supplies WHERE encounter_id IN (SELECT encounter_id FROM encounters WHERE patient_id = ?)', (patient_id,))
        cursor.execute('DELETE FROM encounters WHERE patient_id = ?', (patient_id,))
        cursor.execute('DELETE FROM patients WHERE patient_id = ?', (patient_id,))
        
        conn.commit()
        conn.close()
        
        return jsonify({'message': 'Patient deleted successfully', 'code': 'PATIENT_DELETED'}), 200
        
    except Exception as e:
        return jsonify({'error': str(e), 'code': 'SERVER_ERROR'}), 500

@app.route('/api/encounters', methods=['GET'])
@require_auth
def get_encounters():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT e.encounter_id, e.patient_id, p.first_name, p.last_name,
                   e.admission_date, e.discharge_date, e.hospital_department
            FROM encounters e
            JOIN patients p ON e.patient_id = p.patient_id
            ORDER BY e.admission_date DESC
        ''')
        encounters = cursor.fetchall()
        conn.close()
        return jsonify([dict(row) for row in encounters]), 200
    except Exception as e:
        return jsonify({'error': str(e), 'code': 'SERVER_ERROR'}), 500

@app.route('/api/encounters/<int:encounter_id>', methods=['GET'])
@require_auth
def get_encounter(encounter_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT e.*, p.first_name, p.last_name
            FROM encounters e
            JOIN patients p ON e.patient_id = p.patient_id
            WHERE e.encounter_id = ?
        ''', (encounter_id,))
        encounter = cursor.fetchone()
        
        if not encounter:
            conn.close()
            return jsonify({'error': 'Encounter not found', 'code': 'NOT_FOUND'}), 404
        
        cursor.execute('SELECT * FROM diagnoses WHERE encounter_id = ?', (encounter_id,))
        diagnoses = cursor.fetchall()
        
        cursor.execute('SELECT * FROM procedures WHERE encounter_id = ?', (encounter_id,))
        procedures = cursor.fetchall()
        
        cursor.execute('SELECT * FROM supplies WHERE encounter_id = ?', (encounter_id,))
        supplies = cursor.fetchall()
        
        conn.close()
        
        return jsonify({
            'encounter': dict(encounter),
            'diagnoses': [dict(d) for d in diagnoses],
            'procedures': [dict(p) for p in procedures],
            'supplies': [dict(s) for s in supplies]
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e), 'code': 'SERVER_ERROR'}), 500

@app.route('/api/encounters', methods=['POST'])
@require_auth
def add_encounter():
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'Request body required', 'code': 'INVALID_REQUEST'}), 400
        
        patient_id = data.get('patient_id')
        admission_date = data.get('admission_date', '').strip()
        discharge_date = data.get('discharge_date', '').strip()
        department = data.get('hospital_department', '').strip()
        
        errors = {}
        
        if not patient_id:
            errors['patient_id'] = 'Patient ID required'
        if not admission_date:
            errors['admission_date'] = 'Admission date required'
        elif not validate_date(admission_date):
            errors['admission_date'] = 'Invalid date format (YYYY-MM-DD)'
        if not discharge_date:
            errors['discharge_date'] = 'Discharge date required'
        elif not validate_date(discharge_date):
            errors['discharge_date'] = 'Invalid date format (YYYY-MM-DD)'
        if not department:
            errors['department'] = 'Department required'
        
        if errors:
            return jsonify({'error': 'Validation failed', 'code': 'VALIDATION_ERROR', 'errors': errors}), 400
        
        # Verify patient exists
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT patient_id FROM patients WHERE patient_id = ?', (patient_id,))
        if not cursor.fetchone():
            conn.close()
            return jsonify({'error': 'Patient not found', 'code': 'NOT_FOUND'}), 404
        
        # Validate discharge after admission
        if discharge_date < admission_date:
            conn.close()
            return jsonify({'error': 'Discharge date must be after admission date', 'code': 'VALIDATION_ERROR'}), 400
        
        cursor.execute('''
            INSERT INTO encounters (patient_id, admission_date, discharge_date, hospital_department)
            VALUES (?, ?, ?, ?)
        ''', (patient_id, admission_date, discharge_date, department))
        
        conn.commit()
        encounter_id = cursor.lastrowid
        conn.close()
        
        return jsonify({
            'encounter_id': encounter_id,
            'message': 'Encounter created successfully',
            'code': 'ENCOUNTER_CREATED'
        }), 201
        
    except Exception as e:
        return jsonify({'error': str(e), 'code': 'SERVER_ERROR'}), 500

@app.route('/api/diagnoses', methods=['POST'])
@require_auth
def add_diagnosis():
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'Request body required', 'code': 'INVALID_REQUEST'}), 400
        
        encounter_id = data.get('encounter_id')
        icd10_code = data.get('icd10_code', '').strip().upper()
        diagnosis_description = data.get('diagnosis_description', '').strip()
        
        errors = {}
        
        if not encounter_id:
            errors['encounter_id'] = 'Encounter ID required'
        if not icd10_code:
            errors['icd10_code'] = 'ICD-10 code required'
        elif not (3 <= len(icd10_code) <= 7):
            errors['icd10_code'] = 'ICD-10 code must be 3-7 characters'
        if not diagnosis_description:
            errors['diagnosis_description'] = 'Description required'
        
        if errors:
            return jsonify({'error': 'Validation failed', 'code': 'VALIDATION_ERROR', 'errors': errors}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Verify encounter exists
        cursor.execute('SELECT encounter_id FROM encounters WHERE encounter_id = ?', (encounter_id,))
        if not cursor.fetchone():
            conn.close()
            return jsonify({'error': 'Encounter not found', 'code': 'NOT_FOUND'}), 404
        
        cursor.execute('''
            INSERT INTO diagnoses (encounter_id, icd10_code, diagnosis_description, is_primary)
            VALUES (?, ?, ?, ?)
        ''', (encounter_id, icd10_code, diagnosis_description, data.get('is_primary', 0)))
        
        conn.commit()
        diagnosis_id = cursor.lastrowid
        conn.close()
        
        return jsonify({
            'diagnosis_id': diagnosis_id,
            'message': 'Diagnosis added successfully',
            'code': 'DIAGNOSIS_CREATED'
        }), 201
        
    except Exception as e:
        return jsonify({'error': str(e), 'code': 'SERVER_ERROR'}), 500

@app.route('/api/procedures', methods=['POST'])
@require_auth
def add_procedure():
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'Request body required', 'code': 'INVALID_REQUEST'}), 400
        
        encounter_id = data.get('encounter_id')
        cpt_code = data.get('cpt_code', '').strip()
        procedure_description = data.get('procedure_description', '').strip()
        estimated_cost = data.get('estimated_cost')
        
        errors = {}
        
        if not encounter_id:
            errors['encounter_id'] = 'Encounter ID required'
        if not cpt_code:
            errors['cpt_code'] = 'CPT code required'
        elif not (4 <= len(cpt_code) <= 5):
            errors['cpt_code'] = 'CPT code must be 4-5 characters'
        if not procedure_description:
            errors['procedure_description'] = 'Description required'
        if estimated_cost is None:
            errors['estimated_cost'] = 'Cost required'
        elif not isinstance(estimated_cost, (int, float)) or estimated_cost < 0:
            errors['estimated_cost'] = 'Cost must be a positive number'
        
        if errors:
            return jsonify({'error': 'Validation failed', 'code': 'VALIDATION_ERROR', 'errors': errors}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT encounter_id FROM encounters WHERE encounter_id = ?', (encounter_id,))
        if not cursor.fetchone():
            conn.close()
            return jsonify({'error': 'Encounter not found', 'code': 'NOT_FOUND'}), 404
        
        cursor.execute('''
            INSERT INTO procedures (encounter_id, cpt_code, procedure_description, procedure_date, estimated_cost)
            VALUES (?, ?, ?, ?, ?)
        ''', (encounter_id, cpt_code, procedure_description, data.get('procedure_date'), estimated_cost))
        
        conn.commit()
        procedure_id = cursor.lastrowid
        conn.close()
        
        return jsonify({
            'procedure_id': procedure_id,
            'message': 'Procedure added successfully',
            'code': 'PROCEDURE_CREATED'
        }), 201
        
    except Exception as e:
        return jsonify({'error': str(e), 'code': 'SERVER_ERROR'}), 500

@app.route('/api/supplies', methods=['POST'])
@require_auth
def add_supply():
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'Request body required', 'code': 'INVALID_REQUEST'}), 400
        
        encounter_id = data.get('encounter_id')
        hcpcs_code = data.get('hcpcs_code', '').strip().upper()
        supply_name = data.get('supply_name', '').strip()
        quantity = data.get('quantity')
        unit_cost = data.get('unit_cost')
        
        errors = {}
        
        if not encounter_id:
            errors['encounter_id'] = 'Encounter ID required'
        if not hcpcs_code:
            errors['hcpcs_code'] = 'HCPCS code required'
        if not supply_name:
            errors['supply_name'] = 'Supply name required'
        if not quantity or not isinstance(quantity, int) or quantity <= 0:
            errors['quantity'] = 'Quantity must be a positive integer'
        if unit_cost is None or not isinstance(unit_cost, (int, float)) or unit_cost < 0:
            errors['unit_cost'] = 'Unit cost must be a non-negative number'
        
        if errors:
            return jsonify({'error': 'Validation failed', 'code': 'VALIDATION_ERROR', 'errors': errors}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT encounter_id FROM encounters WHERE encounter_id = ?', (encounter_id,))
        if not cursor.fetchone():
            conn.close()
            return jsonify({'error': 'Encounter not found', 'code': 'NOT_FOUND'}), 404
        
        cursor.execute('''
            INSERT INTO supplies (encounter_id, hcpcs_code, supply_name, quantity, unit_cost)
            VALUES (?, ?, ?, ?, ?)
        ''', (encounter_id, hcpcs_code, supply_name, quantity, unit_cost))
        
        conn.commit()
        supply_id = cursor.lastrowid
        conn.close()
        
        return jsonify({
            'supply_id': supply_id,
            'message': 'Supply added successfully',
            'code': 'SUPPLY_CREATED'
        }), 201
        
    except Exception as e:
        return jsonify({'error': str(e), 'code': 'SERVER_ERROR'}), 500

@app.route('/api/patients/<int:patient_id>/bill', methods=['GET'])
@require_auth
def get_patient_bill(patient_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM patients WHERE patient_id = ?', (patient_id,))
        patient = cursor.fetchone()
        
        if not patient:
            conn.close()
            return jsonify({'error': 'Patient not found', 'code': 'NOT_FOUND'}), 404
        
        cursor.execute('SELECT * FROM encounters WHERE patient_id = ? ORDER BY admission_date DESC', (patient_id,))
        encounters = cursor.fetchall()
        
        result_encounters = []
        for enc in encounters:
            cursor.execute('SELECT * FROM diagnoses WHERE encounter_id = ?', (enc['encounter_id'],))
            diags = cursor.fetchall()
            
            cursor.execute('SELECT * FROM procedures WHERE encounter_id = ?', (enc['encounter_id'],))
            procs = cursor.fetchall()
            
            cursor.execute('SELECT * FROM supplies WHERE encounter_id = ?', (enc['encounter_id'],))
            supps = cursor.fetchall()
            
            result_encounters.append({
                'encounter': dict(enc),
                'diagnoses': [dict(d) for d in diags],
                'procedures': [dict(p) for p in procs],
                'supplies': [dict(s) for s in supps]
            })
        
        conn.close()
        
        return jsonify({
            'patient': dict(patient),
            'encounters': result_encounters,
            'code': 'BILL_RETRIEVED'
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e), 'code': 'SERVER_ERROR'}), 500

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok', 'code': 'HEALTH_CHECK'}), 200

if __name__ == '__main__':
    print("\n" + "="*60)
    print("🏥 MediTrack - Clinical Patient Data Warehouse")
    print("="*60)
    print(f"Starting server on http://{HOST}:{PORT}")
    if not IS_PRODUCTION:
        print(f"Login credentials: {DEFAULT_ADMIN_USERNAME} / {LOCAL_DEV_ADMIN_PASSWORD}")
    elif DEFAULT_ADMIN_PASSWORD:
        print(f"Seeded admin user: {DEFAULT_ADMIN_USERNAME}")
    else:
        print("No default admin credentials were seeded.")
    print("="*60 + "\n")
    app.run(debug=False, port=PORT, host=HOST, threaded=True)
