import logging

logger = logging.getLogger(__name__)


def create_tables(cursor):
    """CREATE TABLE + CREATE INDEX (idempotentes)."""
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS organizations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            slug TEXT NOT NULL UNIQUE,
            description TEXT DEFAULT '',
            is_active INTEGER NOT NULL DEFAULT 1,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')


    cursor.execute('''
        CREATE TABLE IF NOT EXISTS org_members (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            org_id INTEGER NOT NULL REFERENCES organizations(id),
            user_id INTEGER NOT NULL REFERENCES users(id),
            role TEXT NOT NULL DEFAULT 'member',
            joined_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(org_id, user_id)
        )
    ''')




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


    cursor.execute('''
        CREATE TABLE IF NOT EXISTS professional_coverage (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id),
            coverage_type TEXT NOT NULL CHECK (coverage_type IN ('zone', 'specialty')),
            value TEXT NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, coverage_type, value)
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
        CREATE TABLE IF NOT EXISTS lead_stages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            professional_id INTEGER NOT NULL,
            lead_id INTEGER NOT NULL,
            stage TEXT NOT NULL DEFAULT 'new',
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(professional_id, lead_id),
            FOREIGN KEY (professional_id) REFERENCES users(id),
            FOREIGN KEY (lead_id) REFERENCES leads(id)
        )
    ''')


    cursor.execute('''
        CREATE TABLE IF NOT EXISTS lead_stage_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            professional_id INTEGER NOT NULL,
            lead_id INTEGER NOT NULL,
            from_stage TEXT DEFAULT NULL,
            to_stage TEXT NOT NULL,
            changed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (professional_id) REFERENCES users(id),
            FOREIGN KEY (lead_id) REFERENCES leads(id)
        )
    ''')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_lead_stage_history_lead ON lead_stage_history(lead_id)')


    # Etiquetas/colores/orden de las etapas del pipeline (las claves de etapa
    # siguen siendo fijas en models.PIPELINE_STAGES).
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS pipeline_stage_settings (
            stage TEXT PRIMARY KEY,
            label_es TEXT NOT NULL,
            label_en TEXT NOT NULL,
            color TEXT NOT NULL DEFAULT '#735A3A',
            sort_order INTEGER NOT NULL DEFAULT 0
        )
    ''')


    # SLA de primer contacto (plan SLA Fase 0). PK = lead_id → idempotente:
    # la primera señal (reveal / link WA / move a contacted) gana y las demás
    # se ignoran. business_hours_elapsed ya viene calculado (lun–vie 09–18).
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS lead_first_contact (
            lead_id INTEGER PRIMARY KEY REFERENCES leads(id),
            professional_id INTEGER DEFAULT NULL REFERENCES users(id),
            contact_at DATETIME NOT NULL,
            source TEXT NOT NULL,
            business_hours_elapsed REAL NOT NULL DEFAULT 0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_lead_first_contact_at ON lead_first_contact(contact_at)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_lead_first_contact_pro ON lead_first_contact(professional_id)')


    cursor.execute('''
        CREATE TABLE IF NOT EXISTS calendar_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            professional_id INTEGER NOT NULL,
            lead_id INTEGER DEFAULT NULL,
            title TEXT NOT NULL,
            description TEXT DEFAULT '',
            event_date TEXT NOT NULL,
            start_time TEXT DEFAULT '',
            end_time TEXT DEFAULT '',
            event_type TEXT NOT NULL DEFAULT 'visit',
            location TEXT DEFAULT '',
            color TEXT DEFAULT 'gold',
            all_day INTEGER NOT NULL DEFAULT 0,
            completed INTEGER NOT NULL DEFAULT 0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
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

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS email_verification_tokens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            token TEXT NOT NULL UNIQUE,
            email TEXT NOT NULL DEFAULT '',
            expires_at DATETIME NOT NULL,
            used INTEGER NOT NULL DEFAULT 0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    cursor.execute('CREATE INDEX IF NOT EXISTS idx_email_verification_user ON email_verification_tokens(user_id, used)')







































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

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS idempotency_keys (
            key TEXT PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES users(id),
            lead_id INTEGER REFERENCES leads(id),
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Índices únicos idx_lead_reports_pending_once / idx_notif_lead_created_once
    # NO se crean acá: los crea db_migrations.apply_migrations() DESPUÉS de
    # limpiar los duplicados históricos. create_tables corre antes que
    # apply_migrations (app_setup.init_db), así que crearlos acá haría fallar
    # el arranque en un DB con duplicados, y el dedup nunca llegaría a correr.


