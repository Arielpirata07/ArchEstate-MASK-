# app.py - Aplicación principal de Flask para ArchEstate

import csv
import io
import os
import re
import sqlite3
import threading
import time

from datetime import datetime
from functools import wraps
from io import StringIO

import openpyxl
import pytz

from flask import Flask, render_template, jsonify, request, session, redirect, url_for, Response, send_file, flash, send_from_directory
from fpdf import FPDF
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

import config
import utils
from utils import allowed_file, convert_to_argentina_time
import decorators
import rate_limit
import validators
import models


app = Flask(__name__)
app.secret_key = config.SECRET_KEY
app.config['UPLOAD_FOLDER'] = os.path.join(app.root_path, config.UPLOAD_FOLDER)
app.jinja_env.autoescape = True


class FilterOptionsCache:
    """Caché simple en memoria para opciones de filtros de leads"""
    def __init__(self, ttl_seconds=300):
        self._cache = {}
        self._timestamps = {}
        self._ttl = ttl_seconds
        self._lock = threading.Lock()

    def get(self, key):
        with self._lock:
            if key in self._cache:
                if time.time() - self._timestamps[key] < self._ttl:
                    return self._cache[key]
                else:
                    del self._cache[key]
                    del self._timestamps[key]
        return None

    def set(self, key, value):
        with self._lock:
            self._cache[key] = value
            self._timestamps[key] = time.time()

    def invalidate(self):
        with self._lock:
            self._cache.clear()
            self._timestamps.clear()


filter_cache = FilterOptionsCache(ttl_seconds=300)


@app.after_request
def security_headers(response):
    """Agrega headers de seguridad HTTP a todas las respuestas"""
    if not request.path.startswith('/static/'):
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['X-XSS-Protection'] = '1; mode=block'
    return rate_limit.add_rate_limit_headers(response)


def get_db_connection():
    return models.get_db_connection()


def init_db():
    """Inicializa la base de datos de usuarios, leads, profesionales y auditoría si no existe"""
    with app.app_context():
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Tabla de Usuarios
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                email TEXT NOT NULL DEFAULT '',
                hash TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'client',
                doc_path TEXT DEFAULT '',
                is_active INTEGER NOT NULL DEFAULT 1
            )
        ''')
        
        # Migraciones de columnas faltantes
        cursor.execute('PRAGMA table_info(users)')
        user_columns = [row[1] for row in cursor.fetchall()]
        if 'email' not in user_columns:
            cursor.execute("ALTER TABLE users ADD COLUMN email TEXT NOT NULL DEFAULT ''")
        if 'phone' not in user_columns:
            cursor.execute("ALTER TABLE users ADD COLUMN phone TEXT NOT NULL DEFAULT ''")
        if 'is_active' not in user_columns:
            cursor.execute("ALTER TABLE users ADD COLUMN is_active INTEGER NOT NULL DEFAULT 1")

        # Tabla de Leads
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS leads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                type TEXT NOT NULL,
                property_type TEXT NOT NULL DEFAULT 'departamento',
                zone TEXT NOT NULL,
                budget TEXT NOT NULL,
                currency TEXT NOT NULL DEFAULT 'ARG',
                phone TEXT NOT NULL,
                email TEXT NOT NULL,
                floor_block TEXT DEFAULT '',
                usable_m2 INTEGER DEFAULT 0,
                elevator TEXT DEFAULT '',
                land_area INTEGER DEFAULT 0,
                built_area INTEGER DEFAULT 0,
                pool TEXT DEFAULT '',
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Actualizar esquemas antiguos sin las nuevas columnas
        cursor.execute('PRAGMA table_info(leads)')
        existing_columns = [row[1] for row in cursor.fetchall()]
        schema_updates = [
            ('property_type', "TEXT NOT NULL DEFAULT 'departamento'"),
            ('floor_block', "TEXT DEFAULT ''"),
            ('usable_m2', "INTEGER DEFAULT 0"),
            ('elevator', "TEXT DEFAULT ''"),
            ('land_area', "INTEGER DEFAULT 0"),
            ('built_area', "INTEGER DEFAULT 0"),
            ('pool', "TEXT DEFAULT ''"),
            ('architectural_style', "TEXT DEFAULT ''"),
            ('bedrooms', "INTEGER DEFAULT 0"),
            ('bathrooms', "INTEGER DEFAULT 0"),
            ('total_area', "INTEGER DEFAULT 0"),
            ('amenities', "TEXT DEFAULT ''"),
            ('ambientes', "INTEGER DEFAULT 0"),
            ('parking', "TEXT DEFAULT ''"),
            ('orientation', "TEXT DEFAULT ''"),
            ('property_condition', "TEXT DEFAULT ''"),
            ('property_age', "TEXT DEFAULT ''"),
        ]
        for column, column_type in schema_updates:
            if column not in existing_columns:
                cursor.execute(f"ALTER TABLE leads ADD COLUMN {column} {column_type}")

        # Tabla de Profesionales
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS professionals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER DEFAULT NULL,
                name TEXT NOT NULL,
                license TEXT NOT NULL UNIQUE,
                specialty TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        ''')

        # Migración: agregar user_id si no existe
        cursor.execute('PRAGMA table_info(professionals)')
        pro_columns = [row[1] for row in cursor.fetchall()]
        if 'user_id' not in pro_columns:
            cursor.execute('ALTER TABLE professionals ADD COLUMN user_id INTEGER DEFAULT NULL')
            # Poblar user_id para profesionales cuyo name coincide con username
            cursor.execute('''
                UPDATE professionals SET user_id = (
                    SELECT u.id FROM users u WHERE u.username = professionals.name
                ) WHERE user_id IS NULL
            ''')

        # Tabla de Auditoría
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                action TEXT NOT NULL,
                target TEXT NOT NULL,
                admin TEXT NOT NULL
            )
        ''')
        
        # CREAMOS EL ADMIN POR DEFECTO (Ahora con su rol)
        cursor.execute('SELECT COUNT(*) FROM users')
        if cursor.fetchone()[0] == 0:
            cursor.execute('INSERT INTO users (username, email, hash, role) VALUES (?, ?, ?, ?)', 
                          ('admin', 'admin@archestate.local', generate_password_hash('admin123'), 'admin'))
        conn.commit()
        conn.close()


# --- DECORADORES (from decorators.py) ---
login_required = decorators.login_required
admin_required = decorators.admin_required
professional_required = decorators.professional_required


# --- LÓGICA DE NEGOCIO (PYTHON) ---


def log_action(action, target):
    """Registra una acción en la tabla de auditoría de la base de datos"""
    conn = None
    try:
        conn = get_db_connection()
        safe_action = utils.safe_text(action)[:100]
        safe_target = utils.safe_text(target)[:200]
        safe_admin = utils.safe_text(session.get('username', 'sistema'))[:50]
        conn.execute('INSERT INTO audit_log (action, target, admin) VALUES (?, ?, ?)',
                     (safe_action, safe_target, safe_admin))
        conn.commit()
    except Exception as e:
        print(f"Error al registrar auditoría: {e}")
    finally:
        if conn:
            conn.close()


def get_budget_stats_from_db():
    """Retorna estadísticas de presupuesto desde la base de datos"""
    conn = None
    try:
        conn = get_db_connection()
        total_leads = conn.execute('SELECT COUNT(*) FROM leads').fetchone()[0]
        leads_by_budget = conn.execute(
            'SELECT budget, COUNT(*) as count FROM leads GROUP BY budget ORDER BY count DESC'
        ).fetchall()
        leads_by_currency = conn.execute(
            'SELECT currency, COUNT(*) as count FROM leads GROUP BY currency'
        ).fetchall()
        return {
            'total_leads': total_leads,
            'by_budget': [{'label': r['budget'], 'value': r['count']} for r in leads_by_budget],
            'by_currency': [{'label': r['currency'], 'value': r['count']} for r in leads_by_currency],
        }
    finally:
        if conn:
            conn.close()

# --- RUTAS DE NAVEGACIÓN (VISTAS) ---

@app.route('/')
def index():
    return render_template('landing.html')


@app.route('/sitemap.xml')
def sitemap():
    """Generate XML sitemap for search engines."""
    public_urls = [
        {'loc': url_for('index', _external=True), 'changefreq': 'daily', 'priority': '1.0'},
    ]
    xml = '<?xml version="1.0" encoding="UTF-8"?>\n'
    xml += '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    for url in public_urls:
        xml += f'  <url>\n    <loc>{url["loc"]}</loc>\n'
        xml += f'    <changefreq>{url["changefreq"]}</changefreq>\n'
        xml += f'    <priority>{url["priority"]}</priority>\n'
        xml += '  </url>\n'
    xml += '</urlset>'
    return xml, 200, {'Content-Type': 'application/xml'}


@app.route('/robots.txt')
def robots():
    """Serve robots.txt for search engine crawlers."""
    content = """User-agent: *
Allow: /
Disallow: /admin/
Disallow: /api/
Disallow: /login
Disallow: /register
Disallow: /usuario
Disallow: /profesional
Sitemap: https://archestate.com/sitemap.xml
"""
    return content, 200, {'Content-Type': 'text/plain'}


@app.route('/usuario')
@login_required
def user_view():
    conn = None
    try:
        conn = get_db_connection()
        user = conn.execute('SELECT role FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    finally:
        if conn:
            conn.close()

    if user and user['role'] == 'professional':
        flash('Acceso denegado. Los profesionales no pueden acceder a esta sección.', 'error')
        return redirect(url_for('index'))

    return render_template('user.html')


@app.route('/profesional')
@professional_required
def professional_view():
    """Muestra el panel de leads (datos se cargan dinámicamente)"""
    conn = None
    try:
        conn = get_db_connection()
        user = conn.execute('SELECT username, doc_path FROM users WHERE id = ?', (session['user_id'],)).fetchone()
        if not user:
            return redirect(url_for('index'))

        professional = conn.execute('SELECT status FROM professionals WHERE name = ?', (user['username'],)).fetchone()
        if not professional or professional['status'] != 'approved':
            return render_template('professional.html', pending=True, doc_path=user['doc_path'])

        return render_template('professional.html', pending=False, doc_path=user['doc_path'])
    finally:
        if conn:
            conn.close()


@app.route('/profesional/lead/<int:lead_id>')
@professional_required
def lead_detail(lead_id):
    conn = None
    try:
        conn = get_db_connection()
        user = conn.execute('SELECT username FROM users WHERE id = ?', (session['user_id'],)).fetchone()
        if not user:
            return redirect(url_for('index'))

        professional = conn.execute('SELECT status FROM professionals WHERE name = ?', (user['username'],)).fetchone()
        if not professional or professional['status'] != 'approved':
            return render_template('professional.html', leads=[], pending=True)

        lead = conn.execute('SELECT * FROM leads WHERE id = ?', (lead_id,)).fetchone()
    finally:
        if conn:
            conn.close()

    if not lead:
        return redirect(url_for('professional_view'))

    lead_dict = dict(lead)
    lead_dict['timestamp'] = convert_to_argentina_time(lead_dict['timestamp'])
    return render_template('lead_detail.html', lead=lead_dict)


@app.route('/admin')
@admin_required
def admin_view():
    """Muestra logs de auditoría (profesionales se cargan dinámicamente)"""
    conn = None
    try:
        conn = get_db_connection()
        audit_logs = conn.execute('SELECT * FROM audit_log ORDER BY timestamp DESC').fetchall()
    finally:
        if conn:
            conn.close()

    audit_log_converted = []
    for log in audit_logs:
        log_dict = dict(log)
        log_dict['timestamp'] = convert_to_argentina_time(log_dict['timestamp'])
        audit_log_converted.append(log_dict)

    return render_template('admin.html',
                           audit_log=audit_log_converted)


# --- RUTAS DE API (LÓGICA DE DATOS) ---


# --- RUTA DE REGISTRO ---
@app.route('/register', methods=['GET', 'POST'])
@rate_limit.check_rate_limit(limit=5, window=60)
def register():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '').strip()
        raw_role = request.form.get('role', 'client')
        license_number = request.form.get('license', '').strip()

        # ✅ VALIDACIÓN DE CAMPOS OBLIGATORIOS
        if not username or len(username) < 3 or len(username) > 30:
            flash('El nombre de usuario debe tener entre 3 y 30 caracteres.', 'error')
            return redirect(url_for('register'))

        if not re.match(r'^[a-zA-Z0-9_]+$', username):
            flash('El usuario solo puede contener letras, números y guión bajo.', 'error')
            return redirect(url_for('register'))

        if not email:
            flash('El email es requerido.', 'error')
            return redirect(url_for('register'))

        is_valid_email_result, email_error = validators.validate_email(email)
        if not is_valid_email_result:
            flash(email_error, 'error')
            return redirect(url_for('register'))
        
        if not password or len(password) < 6:
            flash('La contraseña debe tener al menos 6 caracteres.', 'error')
            return redirect(url_for('register'))

        if not re.search(r'[A-Za-z]', password) or not re.search(r'[0-9]', password):
            flash('La contraseña debe contener al menos una letra y un número.', 'error')
            return redirect(url_for('register'))
        
        # 🛡️ VALIDACIÓN DE SEGURIDAD CRÍTICA (Backend)
        # Detectar intentos de inyectar 'admin' o roles no autorizados
        if raw_role == 'admin':
            print(f"⚠️ ALERTA DE SEGURIDAD: Intento de registro ilegal como admin por {username}")
            flash('Acceso denegado. Solo administradores pueden asignarse ese rol.', 'error')
            return redirect(url_for('register'))
        
        # Solo permitimos roles explícitamente definidos
        if raw_role in ['client', 'professional']:
            role = raw_role
        else:
            role = 'client'
        
        # ✅ VALIDACIÓN: Profesional requiere matrícula
        if role == 'professional' and not license_number:
            flash('El número de matrícula es requerido para profesionales.', 'error')
            return redirect(url_for('register'))

        if role == 'professional' and (len(license_number) < 3 or len(license_number) > 50):
            flash('El número de matrícula debe tener entre 3 y 50 caracteres.', 'error')
            return redirect(url_for('register'))

        if role == 'professional' and not re.match(r'^[a-zA-Z0-9\-]+$', license_number):
            flash('El número de matrícula contiene caracteres no válidos.', 'error')
            return redirect(url_for('register'))

        conn = get_db_connection()
        try:
            # 1. Crear usuario con email separado y rol validado
            cursor = conn.execute('INSERT INTO users (username, email, hash, role) VALUES (?, ?, ?, ?)', 
                                 (username, email, generate_password_hash(password), role))
            
            # 2. Si es profesional, vincular con user_id real
            if role == 'professional':
                new_user_id = cursor.lastrowid
                conn.execute('INSERT INTO professionals (user_id, name, license, specialty, status) VALUES (?, ?, ?, ?, ?)',
                             (new_user_id, username, license_number, 'General', 'pending'))
            
            conn.commit()
            flash('Registro exitoso. Por favor, inicia sesión.', 'success')
            return redirect(url_for('login'))

        except sqlite3.IntegrityError as e:
            flash('El nombre de usuario ya está en uso. Por favor, elige otro.', 'error')
            return redirect(url_for('register'))
        except Exception as e:
            print(f"Error al registrar usuario: {e}")
            flash('Error al registrar. Por favor, intenta de nuevo.', 'error')
            return redirect(url_for('register'))
        finally:
            conn.close()

    return render_template('register.html')


# --- RUTA DE LOGIN ---
@app.route('/login', methods=['GET', 'POST'])
@rate_limit.check_rate_limit(limit=5, window=60)
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        conn = None
        try:
            conn = get_db_connection()
            user = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
        finally:
            if conn:
                conn.close()

        if user and check_password_hash(user['hash'], password):
            if not user['is_active']:
                flash('Tu cuenta ha sido dada de baja. Contactá al administrador para más información.', 'error')
                return redirect(url_for('login'))

            session.clear()
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['email'] = user['email']
            session['role'] = user['role']

            if user['role'] == 'admin':
                return redirect(url_for('admin_view'))
            elif user['role'] == 'professional':
                return redirect(url_for('professional_view'))
            else:
                return redirect(url_for('user_view'))

        flash('Credenciales inválidas. Intente de nuevo.', 'error')
        return redirect(url_for('login'))

    return render_template('login.html')

# --- RUTA DE LOGOUT ---
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))


@app.route('/api/submit', methods=['POST'])
@rate_limit.check_rate_limit(limit=10, window=60)
def submit_lead():
    """
    Envía una solicitud de propiedad.
    Solo usuarios autenticados pueden usar este endpoint.
    """
    data = request.json
    user_id = session.get('user_id')

    if not user_id:
        return jsonify({
            "status": "error",
            "message": "Debes estar registrado para enviar solicitudes."
        }), 401

    conn = None
    try:
        conn = get_db_connection()
        user = conn.execute('SELECT id, username FROM users WHERE id = ?', (user_id,)).fetchone()

        if not user:
            return jsonify({"status": "error", "message": "Sesión no válida"}), 401

        email = session.get('email') or data.get('email', '')
        is_valid, error = validators.validate_email(email)
        if not is_valid:
            return jsonify({"status": "error", "message": error}), 400

        phone = data.get('phone', '')
        if phone:
            is_valid, error = validators.validate_phone(phone)
            if not is_valid:
                return jsonify({"status": "error", "message": error}), 400

        budget = data.get('budget')
        if budget:
            is_valid, error = validators.validate_budget(budget)
            if not is_valid:
                return jsonify({"status": "error", "message": error}), 400

        zone = data.get('zone')
        if zone:
            is_valid, error = validators.validate_zone(zone)
            if not is_valid:
                return jsonify({"status": "error", "message": error}), 400

        # Validar campos requeridos
        lead_type = data.get('type')
        if not lead_type:
            return jsonify({"status": "error", "message": "El tipo de operación es requerido."}), 400
        
        zone = data.get('zone')
        if not zone:
            return jsonify({"status": "error", "message": "La zona es requerida."}), 400
        
        budget = data.get('budget')
        if not budget:
            return jsonify({"status": "error", "message": "El presupuesto es requerido."}), 400
        
        property_type = data.get('property_type', 'departamento')
        VALID_PROPERTY_TYPES = ['departamento', 'casa', 'duplex', 'penthouse', 'local_comercial']
        if property_type not in VALID_PROPERTY_TYPES:
            return jsonify({"status": "error", "message": "Tipo de propiedad no válido."}), 400

        VALID_CURRENCIES = ['ARG', 'USD', 'EUR']
        currency = data.get('currency', 'ARG')
        if currency not in VALID_CURRENCIES:
            return jsonify({"status": "error", "message": "Moneda no válida."}), 400

        VALID_LEAD_TYPES = ['Comprar Propiedad', 'Remodelación Integral', 'Construir desde Cero']
        if lead_type not in VALID_LEAD_TYPES:
            return jsonify({"status": "error", "message": "Tipo de operación no válido."}), 400

        try:
            land_area = int(data.get('land_area') or 0)
            built_area = int(data.get('built_area') or 0)
        except (ValueError, TypeError):
            land_area = 0
            built_area = 0

        if property_type == 'casa' and built_area > land_area:
            return jsonify({"status": "error", "message": "Los metros construidos no pueden ser mayores que los metros de terreno."}), 400

        conn.execute('''
            INSERT INTO leads (
                type, property_type, zone, budget, currency,
                phone, email, floor_block, usable_m2, elevator,
                land_area, built_area, pool, architectural_style,
                bedrooms, bathrooms, total_area, amenities,
                ambientes, parking, orientation, property_condition, property_age
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            data.get('type'),
            property_type,
            zone,
            budget,
            currency,
            data.get('phone'),
            email,
            data.get('floor_block', ''),
            data.get('usable_m2', 0),
            data.get('elevator', ''),
            data.get('land_area', 0),
            data.get('built_area', 0),
            data.get('pool', ''),
            data.get('architectural_style', ''),
            data.get('bedrooms', 0),
            data.get('bathrooms', 0),
            data.get('total_area', 0),
            data.get('amenities', ''),
            data.get('ambientes', 0),
            data.get('parking', ''),
            data.get('orientation', ''),
            data.get('property_condition', ''),
            data.get('property_age', ''),
        ))
        conn.commit()

        return jsonify({
            "status": "success",
            "message": "Solicitud enviada con éxito. Los profesionales se contactarán contigo."
        })

    except Exception as e:
        print(f"Error en BD: {e}")
        return jsonify({"status": "error", "message": "Error al procesar la solicitud."}), 500
    finally:
        if conn:
            conn.close()



@app.route('/api/leads/filter-options')
@professional_required
def get_leads_filter_options():
    """Retorna valores distintos para poblar los filtros dinámicamente."""
    cached = filter_cache.get('filter_options')
    if cached:
        return jsonify(cached)

    conn = None
    try:
        conn = get_db_connection()
        types      = [r[0] for r in conn.execute('SELECT DISTINCT type FROM leads WHERE type IS NOT NULL ORDER BY type').fetchall()]
        prop_types = [r[0] for r in conn.execute('SELECT DISTINCT property_type FROM leads WHERE property_type IS NOT NULL ORDER BY property_type').fetchall()]
        currencies = [r[0] for r in conn.execute('SELECT DISTINCT currency FROM leads WHERE currency IS NOT NULL ORDER BY currency').fetchall()]
        zones      = [r[0] for r in conn.execute('SELECT DISTINCT zone FROM leads WHERE zone IS NOT NULL ORDER BY zone').fetchall()]

        result = {
            'types':          types,
            'property_types': prop_types,
            'currencies':     currencies,
            'zones':          zones,
        }
        filter_cache.set('filter_options', result)
        return jsonify(result)
    finally:
        if conn:
            conn.close()


@app.route('/api/leads/filter-options/invalidate', methods=['POST'])
@admin_required
def invalidate_filter_cache():
    """Invalida la caché de opciones de filtro."""
    filter_cache.invalidate()
    return jsonify({"status": "success", "message": "Caché invalidada"})


@app.route('/api/leads/stats', methods=['GET'])
def budget_stats():
    """Retorna estadísticas de presupuesto en formato JSON"""
    stats = get_budget_stats_from_db()
    return jsonify(stats)


@app.route('/api/leads/export')
@professional_required
def export_leads_csv():
    """Genera y descarga un archivo CSV con todos los leads"""
    conn = None
    leads = []
    try:
        conn = get_db_connection()
        user = conn.execute('SELECT username FROM users WHERE id = ?', (session['user_id'],)).fetchone()
        if not user:
            return "Acceso denegado", 403

        professional = conn.execute('SELECT status FROM professionals WHERE name = ?', (user['username'],)).fetchone()
        if not professional or professional['status'] != 'approved':
            return "Cuenta pendiente de aprobación", 403

        leads = conn.execute('SELECT id, type, zone, budget, currency, timestamp FROM leads ORDER BY timestamp DESC').fetchall()
    finally:
        if conn:
            conn.close()

    def generate():
        data = StringIO()
        writer = csv.writer(data)

        writer.writerow(['ID', 'Tipo Operacion', 'Zona', 'Presupuesto', 'Moneda', 'Fecha Registro (Argentina)'])
        yield data.getvalue()
        data.seek(0)
        data.truncate(0)

        for lead in leads:
            timestamp_argentina = convert_to_argentina_time(lead['timestamp'])
            writer.writerow([lead['id'], lead['type'], lead['zone'], lead['budget'], lead['currency'], timestamp_argentina])
            yield data.getvalue()
            data.seek(0)
            data.truncate(0)

    filename = f"leads_archestate_{datetime.now().strftime('%Y%m%d_%H%M')}.csv"
    return Response(
        generate(),
        mimetype='text/csv',
        headers={
            'Content-Disposition': f'attachment; filename="{filename}"'
        }
    )

@app.route('/api/leads/export/xlsx')
@professional_required
def export_leads_xlsx():
    """Genera y descarga un archivo XLSX con todos los leads"""
    conn = None
    leads = []
    try:
        conn = get_db_connection()
        user = conn.execute('SELECT username FROM users WHERE id = ?', (session['user_id'],)).fetchone()
        if not user:
            return "Acceso denegado", 403

        professional = conn.execute('SELECT status FROM professionals WHERE name = ?', (user['username'],)).fetchone()
        if not professional or professional['status'] != 'approved':
            return "Cuenta pendiente de aprobación", 403

        leads = conn.execute('SELECT id, type, zone, budget, currency, timestamp FROM leads ORDER BY timestamp DESC').fetchall()
    finally:
        if conn:
            conn.close()

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Leads"

    headers = ['ID', 'Tipo Operacion', 'Zona', 'Presupuesto', 'Moneda', 'Fecha Registro (Argentina)']
    for col_num, header in enumerate(headers, 1):
        ws.cell(row=1, column=col_num, value=header)

    for row_num, lead in enumerate(leads, 2):
        timestamp_argentina = convert_to_argentina_time(lead['timestamp'])
        ws.cell(row=row_num, column=1, value=lead['id'])
        ws.cell(row=row_num, column=2, value=lead['type'])
        ws.cell(row=row_num, column=3, value=lead['zone'])
        ws.cell(row=row_num, column=4, value=lead['budget'])
        ws.cell(row=row_num, column=5, value=lead['currency'])
        ws.cell(row=row_num, column=6, value=timestamp_argentina)

    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)

    filename = f"leads_archestate_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
    return send_file(
        buffer,
        as_attachment=True,
        download_name=filename,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )


@app.route('/api/lead/<int:lead_id>/phone')
@rate_limit.check_rate_limit(limit=20, window=60)
@professional_required
def get_lead_phone(lead_id):
    """Entrega el teléfono de un lead específico y audita la consulta."""
    conn = None
    try:
        conn = get_db_connection()
        user = conn.execute('SELECT username FROM users WHERE id = ?', (session['user_id'],)).fetchone()
        if not user:
            return jsonify({"status": "error", "message": "Acceso denegado"}), 403

        professional = conn.execute('SELECT status FROM professionals WHERE name = ?', (user['username'],)).fetchone()
        if not professional or professional['status'] != 'approved':
            return jsonify({"status": "error", "message": "Cuenta pendiente de aprobación"}), 403

        lead = conn.execute('SELECT phone, type FROM leads WHERE id = ?', (lead_id,)).fetchone()

        if lead:
            log_action("Consulta Teléfono", f"Lead ID: {lead_id} ({lead['type']})")
            return jsonify({"status": "success", "phone": lead['phone']})

        return jsonify({"status": "error", "message": "Lead no encontrado"}), 404
    finally:
        if conn:
            conn.close()


@app.route('/api/lead/<int:lead_id>/download')
@professional_required
def download_lead_pdf(lead_id):
    """Genera un PDF con los detalles del lead para descarga."""
    conn = None
    try:
        conn = get_db_connection()
        user = conn.execute('SELECT username FROM users WHERE id = ?', (session['user_id'],)).fetchone()
        if not user:
            return "Acceso denegado", 403

        professional = conn.execute('SELECT status FROM professionals WHERE name = ?', (user['username'],)).fetchone()
        if not professional or professional['status'] != 'approved':
            return "Cuenta pendiente de aprobación", 403

        lead = conn.execute('SELECT * FROM leads WHERE id = ?', (lead_id,)).fetchone()
    finally:
        if conn:
            conn.close()

    if not lead:
        return jsonify({"status": "error", "message": "Lead no encontrado"}), 404

    lead = dict(lead)

    def pdf_safe(value):
        """Convert values to ASCII-only text safe for FPDF"""
        if value is None:
            return ''
        text = str(value)
        replacements = {
            '\u20ac': 'EUR',
            '\u00a3': 'GBP',
            '\u00a5': 'JPY',
            '\u2014': '-',
            '\u2013': '-',
            '\u2022': '-',
            '\u221a': 'sqrt',
            '\u00d7': 'x',
            '\u00f7': '/',
            '\u2122': 'TM',
            '\u00a9': '(c)',
            '\u00ae': '(R)',
            '\u2026': '...',
            '\u00b2': '2',
            '\u00b3': '3',
            '\u00b0': 'deg',
        }
        for old, new in replacements.items():
            text = text.replace(old, new)
        accents = {
            '\u00e1': 'a', '\u00e9': 'e', '\u00ed': 'i', '\u00f3': 'o', '\u00fa': 'u',
            '\u00e0': 'a', '\u00e8': 'e', '\u00ec': 'i', '\u00f2': 'o', '\u00f9': 'u',
            '\u00e4': 'a', '\u00eb': 'e', '\u00ef': 'i', '\u00f6': 'o', '\u00fc': 'u',
            '\u00e3': 'a', '\u00f5': 'o', '\u00f1': 'n',
            '\u00c1': 'A', '\u00c9': 'E', '\u00cd': 'I', '\u00d3': 'O', '\u00da': 'U',
            '\u00c0': 'A', '\u00c8': 'E', '\u00cc': 'I', '\u00d2': 'O', '\u00d9': 'U',
            '\u00c4': 'A', '\u00cb': 'E', '\u00cf': 'I', '\u00d6': 'O', '\u00dc': 'U',
            '\u00c3': 'A', '\u00d5': 'O', '\u00d1': 'N',
            '\u00e7': 'c', '\u00c7': 'C',
            '\u00df': 'ss',
        }
        for old, new in accents.items():
            text = text.replace(old, new)
        return ''.join(c if ord(c) < 128 else '?' for c in text)

    def pdf_val(value, default='-'):
        """Return safe text or default for display"""
        text = pdf_safe(value)
        return text if text else default

    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)

    midnight = (0, 4, 16)
    gold = (115, 90, 58)

    pdf.set_font('Times', 'BI', 20)
    pdf.set_text_color(*midnight)
    pdf.cell(0, 15, 'ArchEstate - Detalle de Lead', ln=True, align='C')
    pdf.ln(5)

    pdf.set_font('Helvetica', '', 10)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 8, f'Lead #{lead["id"]} - Informacion completa enviada por el cliente', ln=True, align='C')
    pdf.ln(10)

    def section_header(title):
        pdf.set_fill_color(*gold)
        pdf.set_text_color(255, 255, 255)
        pdf.set_font('Helvetica', 'B', 12)
        pdf.cell(0, 8, title.upper(), ln=True, fill=True)
        pdf.set_text_color(*midnight)
        pdf.set_font('Helvetica', '', 10)
        pdf.ln(2)

    section_header('Tipo de Operacion')
    pdf.cell(0, 6, pdf_val(lead['type']), ln=True)

    section_header('Zona Geografica')
    pdf.cell(0, 6, pdf_val(lead['zone']), ln=True)

    section_header('Presupuesto')
    budget_symbol = 'USD' if lead['currency'] == 'USD' else 'EUR' if lead['currency'] == 'EUR' else '$'
    pdf.cell(0, 6, f"{budget_symbol} {pdf_val(lead['budget'])}", ln=True)

    section_header('Estilo Arquitectonico')
    pdf.cell(0, 6, pdf_val(lead.get('architectural_style'), 'No especificado'), ln=True)

    section_header('Contacto Directo')
    pdf.cell(0, 6, f"Email: {pdf_val(lead['email'])}", ln=True)
    pdf.cell(0, 6, f"Telefono: {pdf_val(lead['phone'])}", ln=True)

    section_header('Registrado')
    pdf.cell(0, 6, pdf_val(convert_to_argentina_time(lead['timestamp'])), ln=True)
    pdf.ln(5)

    section_header('Especificaciones Tecnicas')

    pdf.set_font('Helvetica', 'B', 10)
    pdf.cell(60, 8, 'Habitaciones:', border=1)
    pdf.cell(0, 8, pdf_val(lead['bedrooms']), ln=True, border=1)

    pdf.cell(60, 8, 'Banios:', border=1)
    pdf.cell(0, 8, pdf_val(lead['bathrooms']), ln=True, border=1)

    prop_type = pdf_safe(lead.get('property_type', '')).lower()
    if prop_type == 'casa':
        pdf.cell(60, 8, 'Metros de Terreno:', border=1)
        pdf.cell(0, 8, f"{pdf_val(lead['land_area'])} m2" if lead.get('land_area') else '-', ln=True, border=1)
    else:
        pdf.cell(60, 8, 'Metros Utiles:', border=1)
        pdf.cell(0, 8, f"{pdf_val(lead['usable_m2'])} m2" if lead.get('usable_m2') else '-', ln=True, border=1)

    pdf.ln(5)

    section_header('Extras y Comodidades')
    amenities = lead.get('amenities', '')
    if amenities and str(amenities).strip():
        for amenity in pdf_safe(amenities).split(','):
            stripped = amenity.strip()
            if stripped:
                pdf.cell(0, 6, f"- {stripped}", ln=True)
    else:
        pdf.cell(0, 6, 'No especificadas', ln=True)

    if prop_type == 'departamento':
        section_header('Detalles del Departamento')
        pdf.cell(0, 6, f"Piso / Bloque: {pdf_val(lead.get('floor_block'), 'No especificado')}", ln=True)
        pdf.cell(0, 6, f"Metros Utiles: {pdf_val(lead.get('usable_m2'), 'No especificado')} m2", ln=True)
        pdf.cell(0, 6, f"Ascensor: {pdf_val(lead.get('elevator'), 'No especificado')}", ln=True)
    else:
        section_header('Detalles de la Propiedad')
        pdf.cell(0, 6, f"Superficie de Terreno: {pdf_val(lead.get('land_area'), 'No especificado')} m2", ln=True)
        pdf.cell(0, 6, f"Superficie Construida: {pdf_val(lead.get('built_area'), 'No especificado')} m2", ln=True)
        pdf.cell(0, 6, f"Piscina: {pdf_val(lead.get('pool'), 'No especificado')}", ln=True)

    # Generar el PDF
    pdf_output = pdf.output(dest='S')
    if isinstance(pdf_output, str):
        pdf_output = pdf_output.encode('latin-1')

    # Crear buffer con los bytes del PDF
    buffer = io.BytesIO(pdf_output)
    buffer.seek(0)
    
    filename = f"lead_{lead['id']}.pdf"
    
    return send_file(
        buffer,
        as_attachment=True,
        download_name=filename,
        mimetype='application/pdf'
    )


# --- NUEVA API: OBTENER LEADS DINÁMICAMENTE ---
@app.route('/api/leads')
@professional_required
def get_leads_api():
    """API para obtener leads dinámicamente con filtros opcionales"""
    conn = None
    try:
        conn = get_db_connection()

        user = conn.execute('SELECT username FROM users WHERE id = ?', (session['user_id'],)).fetchone()
        if not user:
            return jsonify({"status": "error", "message": "Acceso denegado"}), 403

        professional = conn.execute('SELECT status FROM professionals WHERE name = ?', (user['username'],)).fetchone()
        if not professional or professional['status'] != 'approved':
            return jsonify({"status": "error", "message": "Cuenta pendiente de aprobación"}), 403

        search         = request.args.get('search', '').strip()
        type_filter    = request.args.get('type', '').strip()
        prop_type      = request.args.get('property_type', '').strip()
        zone_filter    = request.args.get('zone', '').strip()
        min_budget     = request.args.get('min_budget', '').strip()
        max_budget     = request.args.get('max_budget', '').strip()
        budget_range   = request.args.get('budget_range', '').strip()
        currency_filter = request.args.get('currency', '').strip()
        sort_by        = request.args.get('sort', 'timestamp')
        sort_order     = request.args.get('order', 'desc')

        BUDGET_RANGES = {
            'hasta_200k':    (0,       200000),
            '200k_500k':     (200000,  500000),
            '500k_1m':       (500000,  1000000),
            '1m_2m':         (1000000, 2000000),
            'mas_2m':        (2000000, None),
        }
        if budget_range and budget_range in BUDGET_RANGES:
            rng = BUDGET_RANGES[budget_range]
            min_budget = str(rng[0]) if rng[0] else ''
            max_budget = str(rng[1]) if rng[1] else ''

        query = 'SELECT * FROM leads WHERE 1=1'
        params = []

        if search:
            query += ' AND (zone LIKE ? OR email LIKE ? OR type LIKE ? OR budget LIKE ?)'
            search_param = f'%{search}%'
            params.extend([search_param, search_param, search_param, search_param])

        if type_filter:
            query += ' AND type = ?'
            params.append(type_filter)

        if prop_type:
            query += ' AND property_type = ?'
            params.append(prop_type)

        if zone_filter:
            query += ' AND zone LIKE ?'
            params.append(f'%{zone_filter}%')

        if min_budget:
            try:
                min_val = float(min_budget)
                query += " AND CAST(REPLACE(REPLACE(budget, '.', ''), ',', '') AS REAL) >= ?"
                params.append(min_val)
            except ValueError:
                pass

        if max_budget:
            try:
                max_val = float(max_budget)
                query += " AND CAST(REPLACE(REPLACE(budget, '.', ''), ',', '') AS REAL) <= ?"
                params.append(max_val)
            except ValueError:
                pass

        if currency_filter:
            query += ' AND currency = ?'
            params.append(currency_filter)

        valid_sort_fields = ['id', 'type', 'zone', 'budget', 'timestamp', 'email']
        if sort_by not in valid_sort_fields:
            sort_by = 'timestamp'

        order = 'DESC' if sort_order.lower() == 'desc' else 'ASC'
        if order not in ('ASC', 'DESC'):
            order = 'ASC'
        query += f' ORDER BY {sort_by} {order}, id DESC'

        leads = conn.execute(query, params).fetchall()

        leads_list = []
        for lead in leads:
            lead_dict = dict(lead)
            lead_dict['timestamp'] = convert_to_argentina_time(lead_dict['timestamp'])
            leads_list.append(lead_dict)

        return jsonify({
            "success": True,
            "leads": leads_list,
            "total": len(leads_list)
        })
    except Exception as e:
        print(f"Error en get_leads_api: {e}")
        return jsonify({"status": "error", "message": "Error interno del servidor"}), 500
    finally:
        if conn:
            conn.close()


# --- NUEVA API: OBTENER PROFESIONALES DINÁMICAMENTE ---
@app.route('/api/professionals')
@admin_required
def get_professionals_api():
    """API para obtener profesionales dinámicamente con filtros"""
    conn = None
    try:
        conn = get_db_connection()

        search = request.args.get('search', '').strip()
        status_filter = request.args.get('status', '').strip()
        specialty_filter = request.args.get('specialty', '').strip()
        sort_by = request.args.get('sort', 'id')
        sort_order = request.args.get('order', 'desc')

        query = '''
            SELECT p.*,
                   u.doc_path,
                   u.id   AS user_id,
                   u.is_active
            FROM professionals p
            LEFT JOIN users u ON (
                (p.user_id IS NOT NULL AND p.user_id = u.id)
                OR
                (p.user_id IS NULL AND p.name = u.username)
            )
            WHERE 1=1
        '''
        params = []

        if search:
            query += ' AND (p.name LIKE ? OR p.license LIKE ? OR p.specialty LIKE ?)'
            search_param = f'%{search}%'
            params.extend([search_param, search_param, search_param])

        if status_filter:
            query += ' AND p.status = ?'
            params.append(status_filter)

        if specialty_filter:
            query += ' AND p.specialty LIKE ?'
            params.append(f'%{specialty_filter}%')

        valid_sort_fields = ['id', 'name', 'license', 'specialty', 'status']
        if sort_by not in valid_sort_fields:
            sort_by = 'id'

        order = 'DESC' if sort_order.lower() == 'desc' else 'ASC'
        if order not in ('ASC', 'DESC'):
            order = 'ASC'
        query += f' ORDER BY p.{sort_by} {order}'

        professionals = conn.execute(query, params).fetchall()

        pros_list = []
        for pro in professionals:
            pro_dict = dict(pro)
            pros_list.append(pro_dict)

        return jsonify({
            "success": True,
            "professionals": pros_list,
            "total": len(pros_list)
        })
    except Exception as e:
        print(f"Error en get_professionals_api: {e}")
        return jsonify({"status": "error", "message": "Error interno del servidor"}), 500
    finally:
        if conn:
            conn.close()


@app.route('/api/admin/professional/<int:pro_id>/status', methods=['POST'])
@rate_limit.check_rate_limit(limit=10, window=60)
@admin_required
def update_pro_status(pro_id):
    """Actualiza el estado de un profesional en la BD y registra la acción"""
    data = request.json
    new_status = data.get('status')

    if new_status not in ['approved', 'rejected']:
        return jsonify({"status": "error", "message": "Estado no válido"}), 400

    conn = None
    try:
        conn = get_db_connection()
        pro = conn.execute('SELECT name FROM professionals WHERE id = ?', (pro_id,)).fetchone()

        if pro:
            conn.execute('UPDATE professionals SET status = ? WHERE id = ?', (new_status, pro_id))
            conn.commit()

            action = "Aprobación" if new_status == 'approved' else "Rechazo"
            log_action(action, pro['name'])
            return jsonify({"status": "success", "message": f"Profesional {action.lower()} correctamente"})

        return jsonify({"error": "Profesional no encontrado"}), 404
    finally:
        if conn:
            conn.close()


@app.route('/api/admin/stats')
@login_required
def admin_stats():
    """Retorna estadísticas agregadas para el dashboard del admin"""
    conn = None
    try:
        conn = get_db_connection()

        # Total de leads
        total_leads = conn.execute('SELECT COUNT(*) FROM leads').fetchone()[0]

        # Leads por tipo de operación
        leads_by_type = conn.execute(
            'SELECT type, COUNT(*) as count FROM leads GROUP BY type ORDER BY count DESC'
        ).fetchall()

        # Leads por zona (top 5)
        leads_by_zone = conn.execute(
            'SELECT zone, COUNT(*) as count FROM leads GROUP BY zone ORDER BY count DESC LIMIT 5'
        ).fetchall()

        # Leads por presupuesto
        leads_by_budget = conn.execute(
            'SELECT budget, COUNT(*) as count FROM leads GROUP BY budget ORDER BY count DESC'
        ).fetchall()

        # Leads por mes (últimos 6 meses)
        leads_by_month = conn.execute('''
            SELECT strftime('%Y-%m', timestamp) as month, COUNT(*) as count
            FROM leads
            GROUP BY month
            ORDER BY month DESC
            LIMIT 6
        ''').fetchall()

        # Estado de profesionales
        pros_stats = conn.execute(
            'SELECT status, COUNT(*) as count FROM professionals GROUP BY status'
        ).fetchall()

        # Total de usuarios por rol
        users_by_role = conn.execute(
            'SELECT role, COUNT(*) as count FROM users GROUP BY role'
        ).fetchall()

        # Acciones del log de auditoría
        audit_actions = conn.execute(
            'SELECT action, COUNT(*) as count FROM audit_log GROUP BY action ORDER BY count DESC'
        ).fetchall()

        return jsonify({
            'total_leads': total_leads,
            'leads_by_type': [{'label': r['type'], 'value': r['count']} for r in leads_by_type],
            'leads_by_zone': [{'label': r['zone'], 'value': r['count']} for r in leads_by_zone],
            'leads_by_budget': [{'label': r['budget'], 'value': r['count']} for r in leads_by_budget],
            'leads_by_month': [{'label': r['month'], 'value': r['count']} for r in reversed(leads_by_month)],
            'pros_stats': [{'label': r['status'], 'value': r['count']} for r in pros_stats],
            'users_by_role': [{'label': r['role'], 'value': r['count']} for r in users_by_role],
            'audit_actions': [{'label': r['action'], 'value': r['count']} for r in audit_actions],
        })
    except Exception as e:
        print(f"Error en admin_stats: {e}")
        return jsonify({"error": "Error interno"}), 500
    finally:
        if conn:
            conn.close()

# --- ESTADO DEL DOCUMENTO DEL PROFESIONAL ---
@app.route('/api/professional/doc-status', methods=['GET'])
@login_required
def get_doc_status():
    """Retorna el estado del documento del profesional autenticado."""
    conn = None
    try:
        conn = get_db_connection()
        user = conn.execute('SELECT doc_path FROM users WHERE id = ?', (session['user_id'],)).fetchone()

        if not user:
            return jsonify({"error": "Usuario no encontrado"}), 404

        doc_path = user['doc_path']
        has_doc  = bool(doc_path)

        # Verificar que el archivo físico exista
        if has_doc:
            full_path = os.path.join(app.config['UPLOAD_FOLDER'], doc_path)
            has_doc   = os.path.exists(full_path)

        return jsonify({
            "has_doc":   has_doc,
            "filename":  doc_path if has_doc else None,
            # Nombre legible: eliminar el prefijo "user_ID_"
            "display_name": re.sub(r'^user_\d+_', '', doc_path) if has_doc and doc_path else None,
        })
    except Exception as e:
        print(f"Error en get_doc_status: {e}")
        return jsonify({"error": "Error interno"}), 500
    finally:
        if conn:
            conn.close()


# --- RUTA PARA QUE EL PROFESIONAL SUBA SU DOC ---
MAX_UPLOAD_BYTES = 10 * 1024 * 1024  # 10 MB

@app.route('/api/professional/upload', methods=['POST'])
@rate_limit.check_rate_limit(limit=5, window=60)
@professional_required
def upload_professional_doc():
    if 'document' not in request.files:
        return jsonify({"error": "No se incluyó ningún archivo en la solicitud."}), 400

    file = request.files['document']
    if not file or file.filename == '':
        return jsonify({"error": "No se seleccionó ningún archivo."}), 400

    if not allowed_file(file.filename):
        return jsonify({
            "error": "Tipo de archivo no permitido. Usá PDF, JPG o PNG."
        }), 415

    # Validar MIME type real (magic bytes)
    mime_valid, detected_ext, mime_error = utils.validate_mime_type(file, file.filename)
    if not mime_valid:
        return jsonify({"error": mime_error}), 415

    # Validar tamaño (leer en memoria para chequear)
    file.seek(0, 2)          # ir al final
    size = file.tell()
    file.seek(0)             # volver al inicio
    if size > config.MAX_UPLOAD_SIZE:
        return jsonify({"error": "El archivo supera el límite de 10 MB."}), 413

    # Nombre seguro con prefijo de usuario
    original_name = secure_filename(file.filename)
    filename      = f"user_{session['user_id']}_{original_name}"
    upload_dir    = app.config['UPLOAD_FOLDER']

    os.makedirs(upload_dir, exist_ok=True)

    # Eliminar documento anterior si existe
    conn = None
    try:
        conn = get_db_connection()
        prev_user = conn.execute('SELECT doc_path FROM users WHERE id = ?', (session['user_id'],)).fetchone()
        if prev_user and prev_user['doc_path']:
            prev_path = os.path.join(upload_dir, prev_user['doc_path'])
            if os.path.exists(prev_path):
                try:
                    os.remove(prev_path)
                except Exception:
                    pass  # No bloquear el flujo si falla el borrado

        file.save(os.path.join(upload_dir, filename))

        conn.execute('UPDATE users SET doc_path = ? WHERE id = ?', (filename, session['user_id']))
        conn.commit()
    finally:
        if conn:
            conn.close()

    log_action("Subida de Documento", f"Usuario ID: {session['user_id']}")

    return jsonify({
        "status":       "success",
        "message":      "Documento subido correctamente.",
        "filename":     filename,
        "display_name": original_name,
    })

# --- RUTA PARA QUE EL ADMIN DESCARGUE EL DOC ---
@app.route('/admin/download_doc/<int:user_id>')
@admin_required 
def download_professional_doc(user_id):
    conn = None
    try:
        conn = get_db_connection()
        user = conn.execute('SELECT doc_path FROM users WHERE id = ?', (user_id,)).fetchone()

        if not user or not user['doc_path']:
            return "El profesional no ha subido ningún documento aún.", 404

        # Usamos la ruta configurada arriba
        directory = app.config['UPLOAD_FOLDER']
        filename = user['doc_path']

        # Verificamos si el archivo físico realmente existe en el disco
        if not os.path.exists(os.path.join(directory, filename)):
            return f"Error: El archivo {filename} no existe en el servidor.", 404

        # as_attachment=True fuerza la descarga en lugar de abrirlo en el navegador
        return send_from_directory(directory, filename, as_attachment=True)

    except Exception as e:
        return f"Error interno: {str(e)}", 500
    finally:
        if conn:
            conn.close()


# --- RUTA PARA QUE EL PROFESIONAL DESCARGUE SU PROPIO DOC ---
@app.route('/profesional/download_doc')
@professional_required
def download_own_doc():
    conn = None
    try:
        conn = get_db_connection()
        user = conn.execute('SELECT doc_path FROM users WHERE id = ?', (session['user_id'],)).fetchone()

        if not user or not user['doc_path']:
            flash('No has subido ningún documento aún.', 'error')
            return redirect(url_for('professional_view'))

        # Usamos la ruta configurada arriba
        directory = app.config['UPLOAD_FOLDER']
        filename = user['doc_path']

        # Verificamos si el archivo físico realmente existe en el disco
        if not os.path.exists(os.path.join(directory, filename)):
            flash(f'Error: El archivo {filename} no existe en el servidor.', 'error')
            return redirect(url_for('professional_view'))

        # as_attachment=True fuerza la descarga en lugar de abrirlo en el navegador
        return send_from_directory(directory, filename, as_attachment=True)

    except Exception as e:
        flash(f'Error interno: {str(e)}', 'error')
        return redirect(url_for('professional_view'))
    finally:
        if conn:
            conn.close()

# --- GESTIÓN DE USUARIOS (ADMIN) ---

@app.route('/admin/usuarios')
@admin_required
def user_management_view():
    """Vista de gestión de usuarios para el administrador."""
    return render_template('user_management.html')


@app.route('/api/admin/users', methods=['GET'])
@admin_required
def get_all_users():
    """Retorna todos los usuarios registrados (sin exponer el hash)."""
    search      = request.args.get('search', '').strip()
    role_filter = request.args.get('role', '').strip()
    active_filter = request.args.get('active', '').strip()  # 'all' | '1' | '0'

    conn = None
    try:
        conn = get_db_connection()
        query = 'SELECT id, username, email, phone, role, is_active FROM users WHERE 1=1'
        params = []

        if search:
            query += ' AND (username LIKE ? OR email LIKE ?)'
            params += [f'%{search}%', f'%{search}%']

        if role_filter:
            query += ' AND role = ?'
            params.append(role_filter)

        if active_filter in ('0', '1'):
            query += ' AND is_active = ?'
            params.append(int(active_filter))

        query += ' ORDER BY is_active DESC, id ASC'   # activos primero
        users = conn.execute(query, params).fetchall()

        return jsonify({
            'success': True,
            'users': [dict(u) for u in users],
            'total': len(users)
        })
    except Exception as e:
        print(f"Error en get_all_users: {e}")
        return jsonify({"error": "Error interno"}), 500
    finally:
        if conn:
            conn.close()


@app.route('/api/admin/user/<int:user_id>/reset-password', methods=['POST'])
@rate_limit.check_rate_limit(limit=5, window=60)
@admin_required
def admin_reset_password(user_id):
    """Resetea la contraseña de un usuario. Solo accesible por administradores."""
    data = request.json
    new_password = (data.get('password') or '').strip()

    if not new_password or len(new_password) < 6:
        return jsonify({"error": "La contraseña debe tener al menos 6 caracteres."}), 400

    conn = None
    try:
        conn = get_db_connection()
        user = conn.execute('SELECT username, role FROM users WHERE id = ?', (user_id,)).fetchone()

        if not user:
            return jsonify({"error": "Usuario no encontrado."}), 404

        # Seguridad: no permitir resetear la contraseña de otro admin
        if user['role'] == 'admin' and user_id != session.get('user_id'):
            return jsonify({"error": "No se puede resetear la contraseña de otro administrador."}), 403

        conn.execute('UPDATE users SET hash = ? WHERE id = ?',
                     (generate_password_hash(new_password), user_id))
        conn.commit()
    finally:
        if conn:
            conn.close()

    log_action("Reset de Contraseña", f"Usuario: {user['username']} (ID: {user_id})")

    return jsonify({
        "status": "success",
        "message": f"Contraseña de '{user['username']}' actualizada correctamente."
    })
    
    
@app.route('/api/admin/user/<int:user_id>/set-active', methods=['POST'])
@rate_limit.check_rate_limit(limit=10, window=60)
@admin_required
def admin_set_user_active(user_id):
    """Da de baja o reactiva una cuenta de usuario. Solo admins. No aplica a otros admins."""
    data      = request.json
    new_state = data.get('is_active')  # True → reactivar, False → dar de baja

    if new_state not in (True, False):
        return jsonify({"error": "Estado inválido."}), 400

    conn = None
    try:
        conn = get_db_connection()
        user = conn.execute('SELECT username, role FROM users WHERE id = ?', (user_id,)).fetchone()

        if not user:
            return jsonify({"error": "Usuario no encontrado."}), 404

        # Protección: no se puede dar de baja a otro administrador
        if user['role'] == 'admin':
            return jsonify({"error": "No se puede dar de baja a un administrador."}), 403

        # Protección: un admin no se da de baja a sí mismo
        if user_id == session.get('user_id'):
            return jsonify({"error": "No podés darte de baja a vos mismo."}), 403

        conn.execute('UPDATE users SET is_active = ? WHERE id = ?', (1 if new_state else 0, user_id))
        conn.commit()
    finally:
        if conn:
            conn.close()

    action  = "Reactivación de Cuenta" if new_state else "Baja de Cuenta"
    message = f"Usuario '{user['username']}' {'reactivado' if new_state else 'dado de baja'} correctamente."
    log_action(action, f"Usuario: {user['username']} (ID: {user_id})")

    return jsonify({"status": "success", "message": message, "is_active": new_state})


@app.route('/api/user/update-phone', methods=['POST'])
@rate_limit.check_rate_limit(limit=10, window=60)
def update_user_phone():
    """Actualiza el teléfono del usuario logueado."""
    if 'user_id' not in session:
        return jsonify({"error": "No autorizado"}), 401

    data = request.json
    phone = (data.get('phone') or '').strip()

    if not phone:
        return jsonify({"error": "El teléfono no puede estar vacío."}), 400

    is_valid, error = validators.validate_phone(phone)
    if not is_valid:
        return jsonify({"error": error}), 400

    conn = None
    try:
        conn = get_db_connection()
        conn.execute('UPDATE users SET phone = ? WHERE id = ?', (phone, session['user_id']))
        conn.commit()
        return jsonify({"status": "success", "message": "Teléfono actualizado correctamente.", "phone": phone})
    except Exception as e:
        print(f"Error en update_user_phone: {e}")
        return jsonify({"error": "Error al actualizar el teléfono."}), 500
    finally:
        if conn:
            conn.close()


# Inicializar la base de datos al arrancar
init_db()


if __name__ == '__main__':
    app.run(debug=True)



  # { "workspaceRoot": "file:///vsls:/", "fileUri": "file:///vsls:/app.py" }