import sqlite3
import os

def init_db():
    # Definir la ruta de la base de datos
    db_path = os.path.join(os.path.dirname(__file__), 'database.db')
    
    # Conectar (creará el archivo si no existe)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Crear la tabla de usuarios
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            hash TEXT NOT NULL
        )
    ''')

    # Crear la tabla de leads
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

    # Crear la tabla de profesionales
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS professionals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            license TEXT NOT NULL UNIQUE,
            specialty TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending'
        )
    ''')

    # Crear la tabla de auditoría
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            action TEXT NOT NULL,
            target TEXT NOT NULL,
            admin TEXT NOT NULL
        )
    ''')
    
    conn.commit()
    conn.close()
    print(f"Base de datos y tablas creadas exitosamente en: {db_path}")

if __name__ == '__main__':
    init_db()
