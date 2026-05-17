import sqlite3
import os
from werkzeug.security import generate_password_hash


def get_db_path():
    return os.path.join(os.path.dirname(__file__), 'database.db')


def init_db():
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys = ON')
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
        CREATE TABLE IF NOT EXISTS audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            action TEXT NOT NULL,
            target TEXT NOT NULL,
            admin TEXT NOT NULL
        )
    ''')

    # Indices para optimizar consultas frecuentes
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_leads_type ON leads(type)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_leads_timestamp ON leads(timestamp)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_role ON users(role)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_professionals_status ON professionals(status)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_professionals_user_id ON professionals(user_id)')

    cursor.execute('SELECT COUNT(*) FROM users')
    if cursor.fetchone()[0] == 0:
        cursor.execute(
            'INSERT INTO users (username, email, hash, role) VALUES (?, ?, ?, ?)',
            ('admin', 'admin@archestate.local', generate_password_hash('admin123'), 'admin')
        )

    conn.commit()
    conn.close()
    print(f"Base de datos inicializada en: {db_path}")


if __name__ == '__main__':
    init_db()
