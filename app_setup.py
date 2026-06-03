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

        cursor.execute('PRAGMA table_info(audit_log)')
        al_cols = [r[1] for r in cursor.fetchall()]
        if 'user_id' not in al_cols:
            cursor.execute("ALTER TABLE audit_log ADD COLUMN user_id INTEGER REFERENCES users(id)")

        os.makedirs(config.AVATAR_FOLDER, exist_ok=True)
        os.makedirs(os.path.join('static', 'uploads', 'portfolio'), exist_ok=True)

        cursor.execute('CREATE INDEX IF NOT EXISTS idx_leads_user_id ON leads(user_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_leads_timestamp ON leads(timestamp)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_leads_zone ON leads(zone)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_leads_type ON leads(type)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_professionals_user_id ON professionals(user_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_professionals_name ON professionals(name)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_professionals_status ON professionals(status)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_lead_tracking_professional ON lead_tracking(professional_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_lead_reports_status ON lead_reports(status)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_audit_log_user ON audit_log(user_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_login_history_user ON user_login_history(user_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_events_user ON events(user_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_events_lead ON events(lead_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_events_event ON events(event)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_events_ts ON events(ts)')

        cursor.execute('SELECT COUNT(*) FROM users')
        if cursor.fetchone()[0] == 0:
            cursor.execute('INSERT INTO users (username, email, hash, role) VALUES (?, ?, ?, ?)',
                          ('admin', 'admin@archestate.local', generate_password_hash('admin123'), 'admin'))
        conn.commit()
        conn.close()
