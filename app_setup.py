import logging
import os
import threading
import time

from werkzeug.security import generate_password_hash

import config
import models
import utils

logger = logging.getLogger(__name__)


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
        logger.info('[init_db] Cleaned test data: %d leads budget/zone, %d phone_format_valid', len(fixes), len(pending))



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
        if current_ver < 2:
            cursor.execute('INSERT INTO schema_version (version) VALUES (2)')
        if current_ver < 3:
            cursor.execute('INSERT INTO schema_version (version) VALUES (3)')
        if current_ver < 4:
            cursor.execute('INSERT INTO schema_version (version) VALUES (4)')
        if current_ver < 5:
            cursor.execute('INSERT INTO schema_version (version) VALUES (5)')

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

        if 'assigned_to' not in existing_columns:
            cursor.execute("ALTER TABLE leads ADD COLUMN assigned_to INTEGER DEFAULT NULL REFERENCES users(id)")

        cursor.execute('PRAGMA table_info(leads)')
        lead_columns = [row[1] for row in cursor.fetchall()]
        if 'user_id' not in lead_columns:
            cursor.execute('ALTER TABLE leads ADD COLUMN user_id INTEGER DEFAULT NULL')
            cursor.execute('''
                UPDATE leads SET user_id = (
                    SELECT u.id FROM users u WHERE u.email = leads.email
                ) WHERE user_id IS NULL AND leads.email IN (SELECT email FROM users)
            ''')

        if 'country' not in lead_columns:
            cursor.execute("ALTER TABLE leads ADD COLUMN country TEXT DEFAULT ''")

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
        if 'notification_filters' not in up_prefs_cols:
            cursor.execute("ALTER TABLE user_preferences ADD COLUMN notification_filters TEXT DEFAULT ''")
        if 'budget_min' not in up_prefs_cols:
            cursor.execute("ALTER TABLE user_preferences ADD COLUMN budget_min REAL DEFAULT 0")
        if 'budget_max' not in up_prefs_cols:
            cursor.execute("ALTER TABLE user_preferences ADD COLUMN budget_max REAL DEFAULT 0")
        if 'whatsapp_notifications' not in up_prefs_cols:
            cursor.execute("ALTER TABLE user_preferences ADD COLUMN whatsapp_notifications INTEGER NOT NULL DEFAULT 1")

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL REFERENCES users(id),
                lead_id INTEGER REFERENCES leads(id),
                type TEXT NOT NULL DEFAULT 'lead',
                title TEXT NOT NULL,
                body TEXT DEFAULT '',
                is_read INTEGER NOT NULL DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_notifications_user ON notifications(user_id, is_read)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_notifications_created ON notifications(created_at)')

        cursor.execute('PRAGMA table_info(notifications)')
        notif_cols = [r[1] for r in cursor.fetchall()]
        if 'actor_id' not in notif_cols:
            cursor.execute("ALTER TABLE notifications ADD COLUMN actor_id INTEGER REFERENCES users(id)")
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_notifications_actor ON notifications(actor_id)')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS password_reset_tokens (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                token TEXT NOT NULL UNIQUE,
                expires_at DATETIME NOT NULL,
                used INTEGER NOT NULL DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_password_reset_token ON password_reset_tokens(token)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_password_reset_expires ON password_reset_tokens(expires_at)')

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
            logger.info('[init_db] Backfill phone_e164 para %d usuarios', len(pending))

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
        if 'country' not in pro_cols:
            cursor.execute("ALTER TABLE professionals ADD COLUMN country TEXT DEFAULT ''")

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
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_phone_e164 ON users(phone_e164)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_lead_versions_lead_id ON lead_versions(lead_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_leads_province_zone ON leads(province, zone)')

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
            ('operation_type', 'Remodelación Integral', 'Remodelación Integral', 'wrench', 2),
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
            ('condition', 'En construcción', 'En construcción', 'hard-hat', 5),
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
            ('country', 'Argentina', 'Argentina', 'globe', 1),
            ('country', 'Uruguay', 'Uruguay', 'globe', 2),
            ('country', 'Chile', 'Chile', 'globe', 3),
            ('country', 'Brasil', 'Brasil', 'globe', 4),
            ('country', 'Paraguay', 'Paraguay', 'globe', 5),
            ('country', 'Bolivia', 'Bolivia', 'globe', 6),
            ('country', 'Colombia', 'Colombia', 'globe', 7),
            ('country', 'Mexico', 'Mexico', 'globe', 8),
            ('country', 'España', 'España', 'globe', 9),
            ('country', 'Estados Unidos', 'Estados Unidos', 'globe', 10),
            ('country', 'Portugal', 'Portugal', 'globe', 11),
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

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS phone_area_codes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT NOT NULL,
                city TEXT NOT NULL,
                province TEXT NOT NULL DEFAULT '',
                country TEXT NOT NULL DEFAULT 'Argentina',
                country_code TEXT NOT NULL DEFAULT '+54',
                sort_order INTEGER DEFAULT 0,
                is_active INTEGER NOT NULL DEFAULT 1,
                UNIQUE(code, country_code)
            )
        ''')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_phone_area_country ON phone_area_codes(country_code)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_phone_area_code ON phone_area_codes(code)')

        PHONE_AREA_CODES_SEED = [
            ('11', 'Buenos Aires / CABA', 'CABA', 'Argentina', '+54', 1),
            ('220', 'San Nicolás', 'Buenos Aires', 'Argentina', '+54', 2),
            ('221', 'La Plata', 'Buenos Aires', 'Argentina', '+54', 3),
            ('223', 'Mar del Plata', 'Buenos Aires', 'Argentina', '+54', 4),
            ('236', 'Junín', 'Buenos Aires', 'Argentina', '+54', 5),
            ('237', 'Olavarría', 'Buenos Aires', 'Argentina', '+54', 6),
            ('239', 'Tandil', 'Buenos Aires', 'Argentina', '+54', 7),
            ('249', 'Necochea', 'Buenos Aires', 'Argentina', '+54', 8),
            ('261', 'Mendoza', 'Mendoza', 'Argentina', '+54', 9),
            ('2622', 'San Rafael', 'Mendoza', 'Argentina', '+54', 10),
            ('264', 'San Juan', 'San Juan', 'Argentina', '+54', 11),
            ('2652', 'Tupungato', 'Mendoza', 'Argentina', '+54', 12),
            ('2653', 'Tunuyán', 'Mendoza', 'Argentina', '+54', 13),
            ('2655', 'Malargüe', 'Mendoza', 'Argentina', '+54', 14),
            ('2656', 'La Paz', 'Mendoza', 'Argentina', '+54', 15),
            ('266', 'San Luis', 'San Luis', 'Argentina', '+54', 16),
            ('280', 'San Miguel de Tucumán', 'Tucumán', 'Argentina', '+54', 17),
            ('2811', 'Concepción', 'Tucumán', 'Argentina', '+54', 18),
            ('2814', 'Monteros', 'Tucumán', 'Argentina', '+54', 19),
            ('291', 'Bahía Blanca', 'Buenos Aires', 'Argentina', '+54', 20),
            ('294', 'Santiago del Estero', 'Santiago del Estero', 'Argentina', '+54', 21),
            ('298', 'San Carlos de Bariloche', 'Río Negro', 'Argentina', '+54', 22),
            ('299', 'Neuquén', 'Neuquén', 'Argentina', '+54', 23),
            ('341', 'Rosario', 'Santa Fe', 'Argentina', '+54', 24),
            ('342', 'Santa Fe', 'Santa Fe', 'Argentina', '+54', 25),
            ('343', 'Paraná', 'Entre Ríos', 'Argentina', '+54', 26),
            ('345', 'Concepción del Uruguay', 'Entre Ríos', 'Argentina', '+54', 27),
            ('346', 'San Luis', 'San Luis', 'Argentina', '+54', 28),
            ('348', 'Venado Tuerto', 'Santa Fe', 'Argentina', '+54', 29),
            ('351', 'Córdoba', 'Córdoba', 'Argentina', '+54', 30),
            ('353', 'Villa María', 'Córdoba', 'Argentina', '+54', 31),
            ('358', 'Río Cuarto', 'Córdoba', 'Argentina', '+54', 32),
            ('362', 'Resistencia', 'Chaco', 'Argentina', '+54', 33),
            ('364', 'Formosa', 'Formosa', 'Argentina', '+54', 34),
            ('370', 'Posadas', 'Misiones', 'Argentina', '+54', 35),
            ('375', 'Goya', 'Corrientes', 'Argentina', '+54', 36),
            ('376', 'Eldorado', 'Misiones', 'Argentina', '+54', 37),
            ('377', 'Puerto Iguazú', 'Misiones', 'Argentina', '+54', 38),
            ('378', 'Oberá', 'Misiones', 'Argentina', '+54', 39),
            ('379', 'Corrientes', 'Corrientes', 'Argentina', '+54', 40),
            ('381', 'Santiago del Estero', 'Santiago del Estero', 'Argentina', '+54', 41),
            ('383', 'San Fernando del Valle de Catamarca', 'Catamarca', 'Argentina', '+54', 42),
            ('385', 'La Rioja', 'La Rioja', 'Argentina', '+54', 43),
            ('387', 'San Salvador de Jujuy', 'Jujuy', 'Argentina', '+54', 44),
            ('388', 'Salta', 'Salta', 'Argentina', '+54', 45),
            ('3541', 'Villa Carlos Paz', 'Córdoba', 'Argentina', '+54', 46),
            ('3543', 'Cosquín', 'Córdoba', 'Argentina', '+54', 47),
            ('3544', 'Alta Gracia', 'Córdoba', 'Argentina', '+54', 48),
            ('3546', 'Mina Clavero', 'Córdoba', 'Argentina', '+54', 49),
            ('3547', 'Cruz del Eje', 'Córdoba', 'Argentina', '+54', 50),
            ('3563', 'Rafaela', 'Santa Fe', 'Argentina', '+54', 51),
            ('3564', 'Reconquista', 'Santa Fe', 'Argentina', '+54', 52),
            ('3571', 'Casilda', 'Santa Fe', 'Argentina', '+54', 53),
            ('3825', 'Añatuya', 'Santiago del Estero', 'Argentina', '+54', 54),
            ('3832', 'Fiambalá', 'Catamarca', 'Argentina', '+54', 55),
            ('3833', 'Andalgalá', 'Catamarca', 'Argentina', '+54', 56),
            ('3844', 'Chilecito', 'La Rioja', 'Argentina', '+54', 57),
            ('3855', 'Chacabuco', 'Buenos Aires', 'Argentina', '+54', 58),
            ('3861', 'Orán', 'Salta', 'Argentina', '+54', 59),
            ('3862', 'Tartagal', 'Salta', 'Argentina', '+54', 60),
            ('3865', 'Cafayate', 'Salta', 'Argentina', '+54', 61),
            ('3873', 'Humahuaca', 'Jujuy', 'Argentina', '+54', 62),
            ('3876', 'Tilcara', 'Jujuy', 'Argentina', '+54', 63),
            ('2901', 'Viedma', 'Río Negro', 'Argentina', '+54', 64),
            ('2920', 'Choele Choel', 'Río Negro', 'Argentina', '+54', 65),
            ('2925', 'Cipolletti', 'Río Negro', 'Argentina', '+54', 66),
            ('2926', 'General Roca', 'Río Negro', 'Argentina', '+54', 67),
            ('3751', 'Curuzú Cuatiá', 'Corrientes', 'Argentina', '+54', 68),
            ('3752', 'Paso de los Libres', 'Corrientes', 'Argentina', '+54', 69),
            ('3753', 'Monte Caseros', 'Corrientes', 'Argentina', '+54', 70),
            ('2', 'Montevideo', 'Montevideo', 'Uruguay', '+598', 1),
            ('42', 'Punta del Este', 'Maldonado', 'Uruguay', '+598', 2),
            ('44', 'Colonia del Sacramento', 'Colonia', 'Uruguay', '+598', 3),
            ('55', 'Salto', 'Salto', 'Uruguay', '+598', 4),
            ('473', 'Rivera', 'Rivera', 'Uruguay', '+598', 5),
            ('99', 'Artigas', 'Artigas', 'Uruguay', '+598', 6),
            ('2', 'Santiago', 'Metropolitana de Santiago', 'Chile', '+56', 1),
            ('32', 'Valparaíso', 'Valparaíso', 'Chile', '+56', 2),
            ('33', 'Viña del Mar', 'Valparaíso', 'Chile', '+56', 3),
            ('41', 'Concepción', 'Biobío', 'Chile', '+56', 4),
            ('45', 'Antofagasta', 'Antofagasta', 'Chile', '+56', 5),
            ('51', 'La Serena', 'Coquimbo', 'Chile', '+56', 6),
            ('61', 'Temuco', 'Araucanía', 'Chile', '+56', 7),
            ('63', 'Osorno', 'Los Lagos', 'Chile', '+56', 8),
            ('65', 'Puerto Montt', 'Los Lagos', 'Chile', '+56', 9),
            ('67', 'Punta Arenas', 'Magallanes', 'Chile', '+56', 10),
            ('9', 'Valdivia', 'Los Ríos', 'Chile', '+56', 11),
            ('11', 'São Paulo', 'São Paulo', 'Brasil', '+55', 1),
            ('21', 'Rio de Janeiro', 'Rio de Janeiro', 'Brasil', '+55', 2),
            ('31', 'Belo Horizonte', 'Minas Gerais', 'Brasil', '+55', 3),
            ('41', 'Curitiba', 'Paraná', 'Brasil', '+55', 4),
            ('51', 'Porto Alegre', 'Rio Grande do Sul', 'Brasil', '+55', 5),
            ('61', 'Brasília', 'Distrito Federal', 'Brasil', '+55', 6),
            ('71', 'Salvador', 'Bahía', 'Brasil', '+55', 7),
            ('81', 'Recife', 'Pernambuco', 'Brasil', '+55', 8),
            ('85', 'Fortaleza', 'Ceará', 'Brasil', '+55', 9),
            ('21', 'Asunción', 'Central', 'Paraguay', '+595', 1),
            ('61', 'Ciudad del Este', 'Alto Paraná', 'Paraguay', '+595', 2),
            ('71', 'Encarnación', 'Itapúa', 'Paraguay', '+595', 3),
            ('2', 'La Paz', 'La Paz', 'Bolivia', '+591', 1),
            ('3', 'Santa Cruz', 'Santa Cruz', 'Bolivia', '+591', 2),
            ('4', 'Cochabamba', 'Cochabamba', 'Bolivia', '+591', 3),
            ('1', 'Bogotá', 'Cundinamarca', 'Colombia', '+57', 1),
            ('2', 'Medellín', 'Antioquia', 'Colombia', '+57', 2),
            ('3', 'Cali', 'Valle del Cauca', 'Colombia', '+57', 3),
            ('4', 'Barranquilla', 'Atlántico', 'Colombia', '+57', 4),
            ('55', 'Ciudad de México', 'CDMX', 'México', '+52', 1),
            ('33', 'Guadalajara', 'Jalisco', 'México', '+52', 2),
            ('81', 'Monterrey', 'Nuevo León', 'México', '+52', 3),
            ('646', 'Tijuana', 'Baja California', 'México', '+52', 4),
            ('91', 'Madrid', 'Madrid', 'España', '+34', 1),
            ('93', 'Barcelona', 'Cataluña', 'España', '+34', 2),
            ('95', 'Sevilla', 'Andalucía', 'España', '+34', 3),
            ('96', 'Valencia', 'Valencia', 'España', '+34', 4),
            ('94', 'Bilbao', 'País Vasco', 'España', '+34', 5),
            ('201', 'New Jersey', 'NJ', 'Estados Unidos', '+1', 1),
            ('212', 'New York', 'NY', 'Estados Unidos', '+1', 2),
            ('310', 'Los Angeles', 'CA', 'Estados Unidos', '+1', 3),
            ('305', 'Miami', 'FL', 'Estados Unidos', '+1', 4),
            ('415', 'San Francisco', 'CA', 'Estados Unidos', '+1', 5),
            ('713', 'Houston', 'TX', 'Estados Unidos', '+1', 6),
        ]

        for code, city, province, country, cc, order in PHONE_AREA_CODES_SEED:
            cursor.execute(
                'INSERT OR IGNORE INTO phone_area_codes (code, city, province, country, country_code, sort_order) VALUES (?, ?, ?, ?, ?, ?)',
                (code, city, province, country, cc, order)
            )

        _clean_lead_test_data(cursor)

        cursor.execute('SELECT COUNT(*) FROM users')
        if cursor.fetchone()[0] == 0:
            is_prod = os.environ.get('FLASK_DEBUG', '0') != '1' and not os.environ.get('PYTEST_CURRENT_TEST')
            if is_prod:
                import secrets
                admin_password = secrets.token_urlsafe(12)
                logger.info('Admin user created (password stored in env)')
            else:
                admin_password = 'admin123'
            cursor.execute('INSERT INTO users (username, email, hash, role) VALUES (?, ?, ?, ?)',
                          ('admin', 'admin@archestate.local', generate_password_hash(admin_password), 'admin'))
        conn.commit()
        conn.close()
