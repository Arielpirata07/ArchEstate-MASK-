import sqlite3
import os
import csv
from io import StringIO
from datetime import datetime
import re
from functools import wraps
from flask import Flask, render_template, jsonify, request, session, redirect, url_for, Response

app = Flask(__name__)
app.secret_key = os.urandom(24) # Clave secreta para sesiones
DATABASE = os.path.join(os.path.dirname(__file__), 'database.db')

def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def login_required(f):
    """
    Decorador para proteger rutas que requieren autenticación.
    Si el usuario no está en la sesión, redirige al login.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

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
                hash TEXT NOT NULL
            )
        ''')
        
        # Tabla de Leads
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS leads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                type TEXT NOT NULL,
                zone TEXT NOT NULL,
                budget TEXT NOT NULL,
                phone TEXT NOT NULL,
                email TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Tabla de Profesionales
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS professionals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                license TEXT NOT NULL UNIQUE,
                specialty TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending'
            )
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
        
        # Insertar datos de prueba si las tablas están vacías
        cursor.execute('SELECT COUNT(*) FROM leads')
        if cursor.fetchone()[0] == 0:
            sample_leads = [
                ("Construcción Villa", "Marbella, Málaga", "€1.2M - €1.5M", "+34 612 345 678", "cliente1@ejemplo.com"),
                ("Compra Penthouse", "Barcelona, Eixample", "€850k - €1M", "+34 699 887 766", "cliente2@ejemplo.com"),
                ("Remodelación Mansión", "Madrid, La Moraleja", "€500k+", "+34 655 443 322", "cliente3@ejemplo.com")
            ]
            cursor.executemany('INSERT INTO leads (type, zone, budget, phone, email) VALUES (?, ?, ?, ?, ?)', sample_leads)

        cursor.execute('SELECT COUNT(*) FROM professionals')
        if cursor.fetchone()[0] == 0:
            sample_pros = [
                ("Arq. Carlos Méndez", "COAM-12948", "Arquitectura Residencial", "approved"),
                ("Inmobiliaria Prime S.L.", "API-4402", "Lujo & Off-market", "approved"),
                ("Estudio Loft Design", "COAM-5521", "Interiorismo", "pending")
            ]
            cursor.executemany('INSERT INTO professionals (name, license, specialty, status) VALUES (?, ?, ?, ?)', sample_pros)
        
        conn.commit()
        conn.close()

# Inicializar la base de datos al arrancar
init_db()

# --- LÓGICA DE NEGOCIO (PYTHON) ---

def is_valid_email(email):
    """Lógica de validación de email en el servidor (más segura que JS)"""
    pattern = r'^[^\s@]+@[^\s@]+\.[^\s@]+$'
    return re.match(pattern, email) is not None

def log_action(action, target):
    """Registra una acción en la tabla de auditoría de la base de datos"""
    try:
        conn = get_db_connection()
        conn.execute('INSERT INTO audit_log (action, target, admin) VALUES (?, ?, ?)',
                     (action, target, session.get('username', 'sistema')))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error al registrar auditoría: {e}")

# --- RUTAS DE NAVEGACIÓN (VISTAS) ---

@app.route('/')
def index():
    return render_template('landing.html')

@app.route('/usuario')
def user_view():
    return render_template('user.html')

@app.route('/profesional')
@login_required
def professional_view():
    """Muestra los leads disponibles desde la base de datos"""
    conn = get_db_connection()
    leads = conn.execute('SELECT id, type, zone, budget FROM leads ORDER BY timestamp DESC').fetchall()
    conn.close()
    
    # Convertir a lista de diccionarios para Jinja2
    leads_list = [dict(lead) for lead in leads]
    return render_template('professional.html', leads=leads_list)

@app.route('/admin')
@login_required
def admin_view():
    """Muestra profesionales y logs desde la base de datos"""
    conn = get_db_connection()
    professionals = conn.execute('SELECT * FROM professionals').fetchall()
    audit_logs = conn.execute('SELECT * FROM audit_log ORDER BY timestamp DESC').fetchall()
    conn.close()
    
    return render_template('admin.html', 
                           professionals=[dict(p) for p in professionals], 
                           audit_log=[dict(a) for a in audit_logs])

# --- RUTAS DE API (LÓGICA DE DATOS) ---

@app.route('/login')
def login():
    """Ruta de login (Simulación para el MVP)"""
    # Para pruebas, permitimos loguearse automáticamente
    session['user_id'] = 1
    session['username'] = 'admin'
    return redirect(url_for('professional_view'))

@app.route('/api/submit', methods=['POST'])
def submit_lead():
    """Procesa y guarda la solicitud del usuario en la base de datos"""
    data = request.json
    email = data.get('email', '')
    lead_type = data.get('type', '')
    zone = data.get('zone', '')
    budget = data.get('budget', '')
    phone = data.get('phone', '')

    if not is_valid_email(email):
        return jsonify({"status": "error", "message": "Email inválido"}), 400

    conn = get_db_connection()
    conn.execute('INSERT INTO leads (type, zone, budget, phone, email) VALUES (?, ?, ?, ?, ?)',
                 (lead_type, zone, budget, phone, email))
    conn.commit()
    conn.close()

    return jsonify({"status": "success", "message": "Solicitud guardada correctamente"})

@app.route('/api/leads/export')
@login_required
def export_leads_csv():
    """Genera y descarga un archivo CSV con todos los leads"""
    conn = get_db_connection()
    leads = conn.execute('SELECT id, type, zone, budget, timestamp FROM leads ORDER BY timestamp DESC').fetchall()
    conn.close()

    def generate():
        data = StringIO()
        writer = csv.writer(data)
        
        # Escribir cabecera
        writer.writerow(['ID', 'Tipo Operacion', 'Zona', 'Presupuesto', 'Fecha Registro'])
        yield data.getvalue()
        data.seek(0)
        data.truncate(0)

        # Escribir filas
        for lead in leads:
            writer.writerow([lead['id'], lead['type'], lead['zone'], lead['budget'], lead['timestamp']])
            yield data.getvalue()
            data.seek(0)
            data.truncate(0)

    response = Response(generate(), mimetype='text/csv')
    response.headers.set("Content-Disposition", "attachment", filename=f"leads_archestate_{datetime.now().strftime('%Y%m%d_%H%M')}.csv")
    return response

@app.route('/api/lead/<int:lead_id>/phone')
@login_required
def get_lead_phone(lead_id):
    """
    Entrega el teléfono de un lead específico y audita la consulta.
    """
    conn = get_db_connection()
    lead = conn.execute('SELECT phone, type FROM leads WHERE id = ?', (lead_id,)).fetchone()
    
    if lead:
        # Auditar la consulta
        log_action("Consulta Teléfono", f"Lead ID: {lead_id} ({lead['type']})")
        conn.close()
        return jsonify({"phone": lead['phone']})
    
    conn.close()
    return jsonify({"error": "Lead no encontrado"}), 404

@app.route('/api/lead/<int:lead_id>/contact')
@login_required
def get_lead_contact(lead_id):
    """
    Entrega la información de contacto completa (teléfono y email) de un lead
    específico y registra la consulta en el log de auditoría.
    Sprint 1 - Historia: Ingresar a un pedido para obtener datos de contacto.
    """
    conn = get_db_connection()
    lead = conn.execute('SELECT phone, email, type FROM leads WHERE id = ?', (lead_id,)).fetchone()
    
    if lead:
        log_action("Solicitud de Contacto", f"Lead ID: {lead_id} ({lead['type']})")
        conn.close()
        return jsonify({
            "phone": lead['phone'],
            "email": lead['email']
        })
    
    conn.close()
    return jsonify({"error": "Lead no encontrado"}), 404

@app.route('/api/admin/professional/<int:pro_id>/status', methods=['POST'])
@login_required
def update_pro_status(pro_id):
    """Actualiza el estado de un profesional en la BD y registra la acción"""
    data = request.json
    new_status = data.get('status')
    
    if new_status not in ['approved', 'rejected']:
        return jsonify({"error": "Estado no válido"}), 400
        
    conn = get_db_connection()
    pro = conn.execute('SELECT name FROM professionals WHERE id = ?', (pro_id,)).fetchone()
    
    if pro:
        conn.execute('UPDATE professionals SET status = ? WHERE id = ?', (new_status, pro_id))
        conn.commit()
        
        action = "Aprobación" if new_status == 'approved' else "Rechazo"
        log_action(action, pro['name'])
        conn.close()
        return jsonify({"status": "success", "message": f"Profesional {action.lower()} correctamente"})
        
    conn.close()
    return jsonify({"error": "Profesional no encontrado"}), 404

if __name__ == '__main__':
    app.run(debug=True, port=3000)
