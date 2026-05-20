import sqlite3
import os
from werkzeug.security import generate_password_hash

import config


def get_db_path():
    return os.path.join(os.path.dirname(__file__), 'database.db')


def init_db():
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            email TEXT NOT NULL DEFAULT '',
            hash TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'client',
            doc_path TEXT DEFAULT '',
            is_active INTEGER NOT NULL DEFAULT 1,
            phone TEXT NOT NULL DEFAULT ''
        )
    ''')

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
            architectural_style TEXT DEFAULT '',
            bedrooms INTEGER DEFAULT 0,
            bathrooms INTEGER DEFAULT 0,
            total_area INTEGER DEFAULT 0,
            amenities TEXT DEFAULT '',
            ambientes INTEGER DEFAULT 0,
            parking TEXT DEFAULT '',
            orientation TEXT DEFAULT '',
            property_condition TEXT DEFAULT '',
            property_age TEXT DEFAULT '',
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')

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

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_profiles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL UNIQUE REFERENCES users(id),
            first_name TEXT DEFAULT '',
            last_name TEXT DEFAULT '',
            bio TEXT DEFAULT '',
            title TEXT DEFAULT '',
            avatar_path TEXT DEFAULT '',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            action TEXT NOT NULL,
            target TEXT NOT NULL,
            admin TEXT NOT NULL
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS professional_profiles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL UNIQUE REFERENCES users(id),
            photo_path TEXT DEFAULT '',
            bio_pro TEXT DEFAULT '',
            experience_years INTEGER DEFAULT 0,
            services_offered TEXT DEFAULT '[]',
            portfolio TEXT DEFAULT '[]',
            availability TEXT DEFAULT '{}',
            social_links TEXT DEFAULT '{}',
            fee_range_min REAL DEFAULT 0,
            fee_range_max REAL DEFAULT 0,
            professional_address TEXT DEFAULT '',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_preferences (
            user_id INTEGER PRIMARY KEY REFERENCES users(id),
            theme TEXT NOT NULL DEFAULT 'light',
            language TEXT NOT NULL DEFAULT 'es',
            email_notifications INTEGER NOT NULL DEFAULT 1,
            sms_notifications INTEGER NOT NULL DEFAULT 1,
            lead_alerts INTEGER NOT NULL DEFAULT 1,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_login_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id),
            ip_address TEXT DEFAULT '',
            user_agent TEXT DEFAULT '',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            last_active DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Migraciones en tablas existentes
    cursor.execute('PRAGMA table_info(user_profiles)')
    existing = [r[1] for r in cursor.fetchall()]
    if 'avatar_path' not in existing:
        cursor.execute("ALTER TABLE user_profiles ADD COLUMN avatar_path TEXT DEFAULT ''")

    cursor.execute('PRAGMA table_info(professionals)')
    existing = [r[1] for r in cursor.fetchall()]
    if 'license_verified' not in existing:
        cursor.execute("ALTER TABLE professionals ADD COLUMN license_verified INTEGER NOT NULL DEFAULT 0")

    cursor.execute('PRAGMA table_info(audit_log)')
    existing = [r[1] for r in cursor.fetchall()]
    if 'user_id' not in existing:
        cursor.execute("ALTER TABLE audit_log ADD COLUMN user_id INTEGER REFERENCES users(id)")

    cursor.execute('SELECT COUNT(*) FROM users')
    if cursor.fetchone()[0] == 0:
        cursor.execute(
            'INSERT INTO users (username, email, hash, role) VALUES (?, ?, ?, ?)',
            ('admin', 'admin@archestate.local', generate_password_hash('admin123'), 'admin')
        )

    conn.commit()
    conn.close()

    # Crear directorios de uploads si no existen
    os.makedirs(config.AVATAR_FOLDER, exist_ok=True)
    os.makedirs(os.path.join('static', 'uploads', 'portfolio'), exist_ok=True)

    print(f"Base de datos inicializada en: {db_path}")


if __name__ == '__main__':
    init_db()