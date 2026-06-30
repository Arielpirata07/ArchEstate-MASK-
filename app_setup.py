import os
import threading
import time

from werkzeug.security import generate_password_hash

import config
import models
import utils


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


def _clean_lead_test_data(cursor):
    """Limpia datos de prueba sin sentido en la tabla leads."""
    import utils

    fixes = [
        (1, '150000 - 400000', 'USD', ''),
        (2, '200000 - 500000', 'USD', ''),
        (3, '100000 - 350000', 'USD', 'Córdoba'),
        (9, '100000 - 400000', 'USD', ''),
    ]
    for lid, budget, currency, zone in fixes:
        parts = []
        params = []
        if budget:
            parts.append('budget = ?')
            params.append(budget)
        if currency:
            parts.append('currency = ?')
            params.append(currency)
        if zone:
            parts.append('zone = ?')
            params.append(zone)
        if parts:
            params.append(lid)
            cursor.execute(f'UPDATE leads SET {", ".join(parts)} WHERE id = ?', params)

    # Clean up random test text
    cursor.execute("UPDATE leads SET additional_features = '' WHERE additional_features = 'fafa'")

    # Recalcular phone_format_valid para leads con teléfono
    pending = cursor.execute(
        'SELECT id, phone FROM leads WHERE phone IS NOT NULL AND phone != "" AND phone_format_valid = 0'
    ).fetchall()
    for row in pending:
        e164 = utils.normalize_phone_to_e164(row['phone'])
        if e164:
            cursor.execute('UPDATE leads SET phone_format_valid = 1 WHERE id = ?', (row['id'],))

    if fixes or pending:
        print(f'[init_db] Cleaned test data: {len(fixes)} leads budget/zone, {len(pending)} phone_format_valid')



def get_budget_stats_from_db():
    conn = None
    try:
        conn = models.get_db_connection()
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


def init_db(app):
    with app.app_context():
        conn = models.get_db_connection()
        cursor = conn.cursor()

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

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS schema_version (
                version INTEGER PRIMARY KEY,
                applied_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
        ''')
        row = cursor.execute('SELECT MAX(version) FROM schema_version').fetchone()
        current_ver = row[0] if row and row[0] else 0
        if current_ver < 1:
            cursor.execute('INSERT INTO schema_version (version) VALUES (1)')

        cursor.execute('PRAGMA table_info(users)')
        user_columns = [row[1] for row in cursor.fetchall()]
        if 'email' not in user_columns:
            cursor.execute("ALTER TABLE users ADD COLUMN email TEXT NOT NULL DEFAULT ''")
        if 'phone' not in user_columns:
            cursor.execute("ALTER TABLE users ADD COLUMN phone TEXT NOT NULL DEFAULT ''")
        if 'phone_format_valid' not in user_columns:
            cursor.execute("ALTER TABLE users ADD COLUMN phone_format_valid INTEGER DEFAULT 0")
        if 'is_active' not in user_columns:
            cursor.execute("ALTER TABLE users ADD COLUMN is_active INTEGER NOT NULL DEFAULT 1")
        if 'phone_verified' not in user_columns:
            cursor.execute("ALTER TABLE users ADD COLUMN phone_verified INTEGER DEFAULT 0")
        if 'verification_code' not in user_columns:
            cursor.execute("ALTER TABLE users ADD COLUMN verification_code TEXT DEFAULT ''")
        if 'verification_expires' not in user_columns:
            cursor.execute("ALTER TABLE users ADD COLUMN verification_expires DATETIME")
        if 'phone_e164' not in user_columns:
            cursor.execute("ALTER TABLE users ADD COLUMN phone_e164 TEXT DEFAULT ''")
        if 'phone_number_type' not in user_columns:
            cursor.execute("ALTER TABLE users ADD COLUMN phone_number_type TEXT DEFAULT ''")
        if 'failed_attempts' not in user_columns:
            cursor.execute("ALTER TABLE users ADD COLUMN failed_attempts INTEGER DEFAULT 0")
        if 'verification_channel' not in user_columns:
            cursor.execute("ALTER TABLE users ADD COLUMN verification_channel TEXT DEFAULT ''")

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

        if 'province' not in existing_columns:
            cursor.execute("ALTER TABLE leads ADD COLUMN province TEXT DEFAULT ''")

        if 'phone_format_valid' not in existing_columns:
            cursor.execute("ALTER TABLE leads ADD COLUMN phone_format_valid INTEGER DEFAULT 0")

        if 'community_pool' not in existing_columns:
            cursor.execute("ALTER TABLE leads ADD COLUMN community_pool TEXT DEFAULT ''")

        if 'additional_features' not in existing_columns:
            cursor.execute("ALTER TABLE leads ADD COLUMN additional_features TEXT DEFAULT ''")

        cursor.execute('PRAGMA table_info(leads)')
        lead_columns = [row[1] for row in cursor.fetchall()]
        if 'user_id' not in lead_columns:
            cursor.execute('ALTER TABLE leads ADD COLUMN user_id INTEGER DEFAULT NULL')
            cursor.execute('''
                UPDATE leads SET user_id = (
                    SELECT u.id FROM users u WHERE u.email = leads.email
                ) WHERE user_id IS NULL AND leads.email IN (SELECT email FROM users)
            ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_profiles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL UNIQUE REFERENCES users(id),
                first_name TEXT DEFAULT '',
                last_name TEXT DEFAULT '',
                bio TEXT DEFAULT '',
                title TEXT DEFAULT '',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS lead_versions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                lead_id INTEGER NOT NULL REFERENCES leads(id),
                version INTEGER NOT NULL,
                data_snapshot TEXT NOT NULL,
                created_by INTEGER REFERENCES users(id),
                change_summary TEXT DEFAULT '',
                edited_at DATETIME DEFAULT CURRENT_TIMESTAMP
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

        cursor.execute('PRAGMA table_info(professionals)')
        pro_columns = [row[1] for row in cursor.fetchall()]
        if 'user_id' not in pro_columns:
            cursor.execute('ALTER TABLE professionals ADD COLUMN user_id INTEGER DEFAULT NULL')
            cursor.execute('''
                UPDATE professionals SET user_id = (
                    SELECT u.id FROM users u WHERE u.username = professionals.name
                ) WHERE user_id IS NULL
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
            CREATE TABLE IF NOT EXISTS lead_tracking (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                professional_id INTEGER NOT NULL,
                lead_id INTEGER NOT NULL,
                seen INTEGER NOT NULL DEFAULT 0,
                contacted INTEGER NOT NULL DEFAULT 0,
                seen_at DATETIME DEFAULT NULL,
                contacted_at DATETIME DEFAULT NULL,
                UNIQUE(professional_id, lead_id),
                FOREIGN KEY (professional_id) REFERENCES users(id),
                FOREIGN KEY (lead_id) REFERENCES leads(id)
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS lead_reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                lead_id INTEGER NOT NULL,
                reported_by INTEGER NOT NULL,
                reason TEXT NOT NULL DEFAULT 'telefono_inexistente',
                notes TEXT DEFAULT '',
                status TEXT NOT NULL DEFAULT 'pending',
                reviewed_by TEXT DEFAULT NULL,
                reviewed_at DATETIME DEFAULT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (lead_id) REFERENCES leads(id),
                FOREIGN KEY (reported_by) REFERENCES users(id)
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

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS consent_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL REFERENCES users(id),
                channel TEXT NOT NULL,
                ip TEXT DEFAULT '',
                user_agent TEXT DEFAULT '',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER REFERENCES users(id),
                lead_id INTEGER REFERENCES leads(id),
                event TEXT NOT NULL,
                props_json TEXT DEFAULT '',
                ip TEXT DEFAULT '',
                ts DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS remember_tokens (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                selector TEXT NOT NULL UNIQUE,
                validator_hash TEXT NOT NULL,
                expires_at DATETIME NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                ip_address TEXT DEFAULT '',
                user_agent TEXT DEFAULT '',
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        ''')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_remember_tokens_selector ON remember_tokens(selector)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_remember_tokens_expires ON remember_tokens(expires_at)')

        cursor.execute('PRAGMA table_info(user_preferences)')
        up_prefs_cols = [r[1] for r in cursor.fetchall()]
        if 'preferred_channel' not in up_prefs_cols:
            cursor.execute("ALTER TABLE user_preferences ADD COLUMN preferred_channel TEXT NOT NULL DEFAULT 'auto'")

        cursor.execute('''
            SELECT id, phone FROM users
            WHERE (phone_e164 IS NULL OR phone_e164 = '')
              AND phone IS NOT NULL AND phone != ''
        ''')
        pending = cursor.fetchall()
        for row in pending:
            e164 = utils.normalize_phone_to_e164(row['phone'])
            ntype = utils.classify_phone_type(e164) if e164 else ''
            cursor.execute(
                'UPDATE users SET phone_e164 = ?, phone_number_type = ?, phone_format_valid = ? WHERE id = ?',
                (e164, ntype, 1 if e164 else 0, row['id'])
            )
        if pending:
            print(f"[init_db] Backfill phone_e164 para {len(pending)} usuarios")

        cursor.execute('PRAGMA table_info(user_profiles)')
        up_cols = [r[1] for r in cursor.fetchall()]
        if 'avatar_path' not in up_cols:
            cursor.execute("ALTER TABLE user_profiles ADD COLUMN avatar_path TEXT DEFAULT ''")

        cursor.execute('PRAGMA table_info(professionals)')
        pro_cols = [r[1] for r in cursor.fetchall()]
        if 'license_verified' not in pro_cols:
            cursor.execute("ALTER TABLE professionals ADD COLUMN license_verified INTEGER NOT NULL DEFAULT 0")
        if 'province' not in pro_cols:
            cursor.execute("ALTER TABLE professionals ADD COLUMN province TEXT DEFAULT ''")
        if 'zone' not in pro_cols:
            cursor.execute("ALTER TABLE professionals ADD COLUMN zone TEXT DEFAULT ''")

        cursor.execute('PRAGMA table_info(audit_log)')
        al_cols = [r[1] for r in cursor.fetchall()]
        if 'user_id' not in al_cols:
            cursor.execute("ALTER TABLE audit_log ADD COLUMN user_id INTEGER REFERENCES users(id)")

        os.makedirs(config.AVATAR_FOLDER, exist_ok=True)
        os.makedirs(os.path.join('static', 'uploads', 'portfolio'), exist_ok=True)
        os.makedirs(config.UPLOAD_FOLDER, exist_ok=True)

        cursor.execute('CREATE INDEX IF NOT EXISTS idx_leads_user_id ON leads(user_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_leads_timestamp ON leads(timestamp)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_leads_zone ON leads(zone)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_leads_type ON leads(type)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_professionals_user_id ON professionals(user_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_professionals_name ON professionals(name)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_professionals_status ON professionals(status)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_lead_tracking_professional ON lead_tracking(professional_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_lead_tracking_lead ON lead_tracking(lead_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_lead_reports_status ON lead_reports(status)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_audit_log_user ON audit_log(user_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_login_history_user ON user_login_history(user_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_events_user ON events(user_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_events_lead ON events(lead_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_events_event ON events(event)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_events_ts ON events(ts)')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS form_options (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT NOT NULL,
                value TEXT NOT NULL,
                label TEXT NOT NULL,
                icon TEXT DEFAULT '',
                sort_order INTEGER DEFAULT 0,
                is_active INTEGER NOT NULL DEFAULT 1,
                UNIQUE(category, value)
            )
        ''')

        FORM_OPTIONS_SEED = [
            ('property_type', 'departamento', 'Departamento', 'building', 1),
            ('property_type', 'casa', 'Casa', 'home', 2),
            ('property_type', 'duplex', 'Duplex', 'layers', 3),
            ('property_type', 'penthouse', 'Penthouse', 'crown', 4),
            ('property_type', 'local_comercial', 'Local Comercial', 'store', 5),
            ('operation_type', 'Comprar Propiedad', 'Comprar Propiedad', 'shopping-cart', 1),
            ('operation_type', 'Remodelacion Integral', 'Remodelacion Integral', 'wrench', 2),
            ('operation_type', 'Construir desde Cero', 'Construir desde Cero', 'hammer', 3),
            ('currency', 'ARG', 'Pesos Argentinos', 'dollar-sign', 1),
            ('currency', 'USD', 'Dolares', 'dollar-sign', 2),
            ('currency', 'EUR', 'Euros', 'euro', 3),
            ('parking', '', 'Sin preferencia', '', 1),
            ('parking', 'sin_cochera', 'Sin cochera', 'x-circle', 2),
            ('parking', 'simple_cubierta', 'Cochera simple cubierta', 'car', 3),
            ('parking', 'doble_cubierta', 'Cochera doble cubierta', 'car', 4),
            ('parking', 'descubierta', 'Descubierta', 'car', 5),
            ('parking', 'garage', 'Garage cerrado', 'lock', 6),
            ('orientation', '', 'Indiferente', '', 1),
            ('orientation', 'Norte', 'Norte', 'arrow-up', 2),
            ('orientation', 'Sur', 'Sur', 'arrow-down', 3),
            ('orientation', 'Este', 'Este', 'arrow-right', 4),
            ('orientation', 'Oeste', 'Oeste', 'arrow-left', 5),
            ('orientation', 'Noreste', 'Noreste', 'arrow-up-right', 6),
            ('orientation', 'Noroeste', 'Noroeste', 'arrow-up-left', 7),
            ('orientation', 'Sureste', 'Sureste', 'arrow-down-right', 8),
            ('orientation', 'Suroeste', 'Suroeste', 'arrow-down-left', 9),
            ('condition', '', 'Sin preferencia', '', 1),
            ('condition', 'A estrenar', 'A estrenar', 'sparkles', 2),
            ('condition', 'Usado', 'Usado', 'home', 3),
            ('condition', 'A reciclar', 'A reciclar', 'wrench', 4),
            ('condition', 'En construccion', 'En construccion', 'hard-hat', 5),
            ('age', '', 'Indiferente', '', 1),
            ('age', 'Hasta 5 años', 'Hasta 5 años', 'clock', 2),
            ('age', '5 a 15 años', '5 a 15 años', 'clock', 3),
            ('age', '15 a 30 años', '15 a 30 años', 'clock', 4),
            ('age', 'Más de 30 años', 'Más de 30 años', 'clock', 5),
            ('budget_range', 'hasta_200k', 'Hasta $200k', 'dollar-sign', 1),
            ('budget_range', '200k_500k', '$200k - $500k', 'dollar-sign', 2),
            ('budget_range', '500k_1m', '$500k - $1M', 'dollar-sign', 3),
            ('budget_range', '1m_2m', '$1M - $2M', 'dollar-sign', 4),
            ('budget_range', 'mas_2m', 'Mas de $2M', 'dollar-sign', 5),
            ('province', 'Buenos Aires', 'Buenos Aires', '', 1),
            ('province', 'CABA', 'CABA', '', 2),
            ('province', 'Catamarca', 'Catamarca', '', 3),
            ('province', 'Chaco', 'Chaco', '', 4),
            ('province', 'Chubut', 'Chubut', '', 5),
            ('province', 'Cordoba', 'Cordoba', '', 6),
            ('province', 'Corrientes', 'Corrientes', '', 7),
            ('province', 'Entre Rios', 'Entre Rios', '', 8),
            ('province', 'Formosa', 'Formosa', '', 9),
            ('province', 'Jujuy', 'Jujuy', '', 10),
            ('province', 'La Pampa', 'La Pampa', '', 11),
            ('province', 'La Rioja', 'La Rioja', '', 12),
            ('province', 'Mendoza', 'Mendoza', '', 13),
            ('province', 'Misiones', 'Misiones', '', 14),
            ('province', 'Neuquen', 'Neuquen', '', 15),
            ('province', 'Rio Negro', 'Rio Negro', '', 16),
            ('province', 'Salta', 'Salta', '', 17),
            ('province', 'San Juan', 'San Juan', '', 18),
            ('province', 'San Luis', 'San Luis', '', 19),
            ('province', 'Santa Cruz', 'Santa Cruz', '', 20),
            ('province', 'Santa Fe', 'Santa Fe', '', 21),
            ('province', 'Santiago del Estero', 'Santiago del Estero', '', 22),
            ('province', 'Tierra del Fuego', 'Tierra del Fuego', '', 23),
            ('province', 'Tucuman', 'Tucuman', '', 24),
            ('architectural_style', 'Moderno', 'Moderno', '', 1),
            ('architectural_style', 'Classico', 'Classico', '', 2),
            ('architectural_style', 'Minimalista', 'Minimalista', '', 3),
            ('architectural_style', 'Industrial', 'Industrial', '', 4),
            ('architectural_style', 'Rustico', 'Rustico', '', 5),
            ('architectural_style', 'Contemporaneo', 'Contemporaneo', '', 6),
            ('architectural_style', 'Vanguardista', 'Vanguardista', '', 7),
            ('architectural_style', 'Tradicional', 'Tradicional', '', 8),
            ('architectural_style', 'Mediterraneo', 'Mediterraneo', '', 9),
            ('architectural_style', 'Nordico', 'Nordico', '', 10),
            ('architectural_style', 'Colonial', 'Colonial', '', 11),
            ('architectural_style', 'Art Deco', 'Art Deco', '', 12),
            ('architectural_style', 'Bauhaus', 'Bauhaus', '', 13),
            ('architectural_style', 'Organico', 'Organico', '', 14),
            ('architectural_style', 'High-Tech', 'High-Tech', '', 15),
            ('architectural_style', 'Neoclasic', 'Neoclasic', '', 16),
            ('architectural_style', 'Gotico', 'Gotico', '', 17),
            ('architectural_style', 'Barroco', 'Barroco', '', 18),
            ('architectural_style', 'Renacentista', 'Renacentista', '', 19),
            ('architectural_style', 'Otro', 'Otro', '', 20),
            ('amenities', 'SUM', 'SUM', '', 1),
            ('amenities', 'Terraza', 'Terraza', '', 2),
            ('amenities', 'Quincho', 'Quincho', '', 3),
            ('amenities', 'Jardin', 'Jardin', '', 4),
            ('amenities', 'Pileta cubierta', 'Pileta cubierta', '', 5),
            ('amenities', 'Barrio privado', 'Barrio privado', '', 6),
            ('amenities', 'Seguridad 24h', 'Seguridad 24h', '', 7),
            ('amenities', 'Club house', 'Club house', '', 8),
            ('amenities', 'Canchas deportivas', 'Canchas deportivas', '', 9),
            ('amenities', 'Lagunas artificiales', 'Lagunas artificiales', '', 10),
            ('amenities', 'Terraza panoramica', 'Terraza panoramica', '', 11),
            ('amenities', 'Jacuzzi', 'Jacuzzi', '', 12),
            ('amenities', 'Vista 360', 'Vista 360', '', 13),
            ('amenities', 'Vitrina', 'Vitrina', '', 14),
            ('amenities', 'Deposito', 'Deposito', '', 15),
            ('amenities', 'Bano comercial', 'Bano comercial', '', 16),
            ('amenities', 'Aire acondicionado', 'Aire acondicionado', '', 17),
            ('amenities', 'Piscina Infinity', 'Piscina Infinity', '', 18),
            ('amenities', 'Bodega', 'Bodega', '', 19),
            ('amenities', 'Gimnasio Privado', 'Gimnasio Privado', '', 20),
            ('amenities', 'Domotica Avanzada', 'Domotica Avanzada', '', 21),
            ('amenities', 'Helipad', 'Helipad', '', 22),
        ]

        for cat, val, lbl, icon, order in FORM_OPTIONS_SEED:
            cursor.execute(
                'INSERT OR IGNORE INTO form_options (category, value, label, icon, sort_order) VALUES (?, ?, ?, ?, ?)',
                (cat, val, lbl, icon, order)
            )

        _clean_lead_test_data(cursor)

        cursor.execute('SELECT COUNT(*) FROM users')
        if cursor.fetchone()[0] == 0:
            is_prod = os.environ.get('FLASK_DEBUG', '0') != '1' and not os.environ.get('PYTEST_CURRENT_TEST')
            if is_prod:
                import secrets
                admin_password = secrets.token_urlsafe(12)
                print(f'[STARTUP] Admin user created. Password: {admin_password}')
            else:
                admin_password = 'admin123'
            cursor.execute('INSERT INTO users (username, email, hash, role) VALUES (?, ?, ?, ?)',
                          ('admin', 'admin@archestate.local', generate_password_hash(admin_password), 'admin'))
        conn.commit()
        conn.close()
