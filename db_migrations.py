import logging
import utils

logger = logging.getLogger(__name__)


def _backfill_first_contact(cursor):
    """Backfill de lead_first_contact desde fuentes existentes (idempotente).

    Por cada lead sin fila en lead_first_contact, registra la primera senal
    disponible entre lead_tracking.contacted_at y events (phone_revealed /
    wa_link_generated). INSERT OR IGNORE: no toca leads ya presentes ni los
    que no tienen ninguna senal (quedan 'unassigned' y no sesgan el KPI).
    """
    from services.sla import business_hours_between, _parse_ts, _created_local, _to_server_local

    cursor.execute('SELECT id, timestamp FROM leads')
    leads = cursor.fetchall()
    for lead in leads:
        lead_id = lead['id'] if isinstance(lead, dict) else lead[0]
        created = _created_local(lead['timestamp'] if isinstance(lead, dict) else lead[1])

        best_at = None
        best_source = None

        row = cursor.execute(
            'SELECT professional_id, contacted_at FROM lead_tracking '
            'WHERE lead_id = ? AND contacted_at IS NOT NULL '
            'ORDER BY contacted_at ASC LIMIT 1', (lead_id,)
        ).fetchone()
        if row:
            # Convención de storage en UTC desde v0.48.5 (tracking.py escribía
            # ART y models/pipeline.py hora local; ahora ambos escriben UTC).
            # Filas anteriores a esa fecha: en servidores UTC (producción) la
            # conversión es identidad y el dato histórico no cambia; en hosts
            # con offset se asume UTC (mejor esfuerzo, la zona de escritura
            # original no queda registrada).
            at = _to_server_local(_parse_ts(row['contacted_at'] if isinstance(row, dict) else row[1]))
            if at:
                best_at, best_source = at, 'stage'

        for evt, src in (('phone_revealed', 'reveal'), ('wa_link_generated', 'wa_link')):
            row = cursor.execute(
                'SELECT user_id, ts FROM events '
                'WHERE lead_id = ? AND event = ? AND ts IS NOT NULL '
                'ORDER BY ts ASC LIMIT 1', (lead_id, evt)
            ).fetchone()
            if row:
                # events.ts es UTC (CURRENT_TIMESTAMP), igual que leads.timestamp.
                at = _to_server_local(_parse_ts(row[1] if not isinstance(row, dict) else row['ts']))
                if at and (best_at is None or at < best_at):
                    best_at, best_source = at, src

        if best_at is None:
            continue

        professional_id = None
        row = cursor.execute(
            'SELECT professional_id FROM lead_tracking WHERE lead_id = ? '
            'ORDER BY (contacted_at IS NULL), contacted_at ASC LIMIT 1', (lead_id,)
        ).fetchone()
        if row:
            professional_id = row['professional_id'] if isinstance(row, dict) else row[0]

        elapsed = business_hours_between(created, best_at) if created else 0.0
        cursor.execute(
            'INSERT OR IGNORE INTO lead_first_contact '
            '(lead_id, professional_id, contact_at, source, business_hours_elapsed) '
            'VALUES (?, ?, ?, ?, ?)',
            (lead_id, professional_id, best_at.strftime('%Y-%m-%d %H:%M:%S'),
             best_source, round(elapsed, 4))
        )


def _dedupe_and_unique_indexes(cursor):
    """Índices únicos (v8) con dedup defensivo de datos legados.

    Si hay duplicados que no se pueden resolver sin decisiones de negocio
    (p. ej. dos usuarios con el mismo email), se omite el índice y se loguea
    para limpieza manual: nunca se borran usuarios.
    """
    # lead_versions: (lead_id, version) único. Conservar la fila más antigua.
    cursor.execute('''
        DELETE FROM lead_versions
        WHERE id NOT IN (
            SELECT MIN(id) FROM lead_versions GROUP BY lead_id, version
        )
    ''')
    cursor.execute(
        'CREATE UNIQUE INDEX IF NOT EXISTS idx_lead_versions_lead_version '
        'ON lead_versions(lead_id, version)'
    )

    # professionals.user_id: un profesional por usuario (parcial, legacy NULL).
    dup_pro = cursor.execute('''
        SELECT COUNT(*) FROM (
            SELECT user_id FROM professionals
            WHERE user_id IS NOT NULL
            GROUP BY user_id HAVING COUNT(*) > 1
        )
    ''').fetchone()[0]
    if dup_pro == 0:
        cursor.execute(
            'CREATE UNIQUE INDEX IF NOT EXISTS idx_professionals_user_unique '
            'ON professionals(user_id) WHERE user_id IS NOT NULL'
        )
    else:
        logger.warning(
            'No se crea índice único professionals.user_id: %s usuarios con duplicados',
            dup_pro
        )

    # users.email: único solo para emails no vacíos (los vacíos son legados).
    dup_email = cursor.execute('''
        SELECT COUNT(*) FROM (
            SELECT LOWER(TRIM(email)) FROM users
            WHERE email IS NOT NULL AND TRIM(email) != ''
            GROUP BY LOWER(TRIM(email)) HAVING COUNT(*) > 1
        )
    ''').fetchone()[0]
    if dup_email == 0:
        cursor.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_users_email_unique "
            "ON users(LOWER(email)) WHERE email IS NOT NULL AND TRIM(email) != ''"
        )
    else:
        logger.warning(
            'No se crea índice único users.email: %s emails duplicados',
            dup_email
        )


def apply_migrations(cursor):
    """Versiones, ALTERs, backfills (idempotentes)."""
    row = cursor.execute('SELECT MAX(version) FROM schema_version').fetchone()

    current_ver = row[0] if row and row[0] else 0

    if current_ver < 1:
        cursor.execute('INSERT OR IGNORE INTO schema_version (version) VALUES (1)')

    if current_ver < 2:
        cursor.execute('INSERT OR IGNORE INTO schema_version (version) VALUES (2)')

    if current_ver < 3:
        cursor.execute('INSERT OR IGNORE INTO schema_version (version) VALUES (3)')

    if current_ver < 4:
        cursor.execute('INSERT OR IGNORE INTO schema_version (version) VALUES (4)')

    if current_ver < 5:
        cursor.execute('INSERT OR IGNORE INTO schema_version (version) VALUES (5)')

    if current_ver < 6:
        cursor.execute('INSERT OR IGNORE INTO schema_version (version) VALUES (6)')

    if current_ver < 7:
        # Fase 0 SLA: backfill del primer contacto (solo una vez)
        _backfill_first_contact(cursor)
        cursor.execute('INSERT OR IGNORE INTO schema_version (version) VALUES (7)')


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

    if 'email_verified' not in user_columns:
        cursor.execute("ALTER TABLE users ADD COLUMN email_verified INTEGER NOT NULL DEFAULT 0")
        # Cuentas preexistentes con email se consideran verificadas para no bloquearlas.
        cursor.execute("UPDATE users SET email_verified = 1 WHERE email IS NOT NULL AND email != ''")

    cursor.execute('PRAGMA table_info(email_verification_tokens)')
    token_columns = [row[1] for row in cursor.fetchall()]
    if token_columns and 'email' not in token_columns:
        cursor.execute("ALTER TABLE email_verification_tokens ADD COLUMN email TEXT NOT NULL DEFAULT ''")

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


    if 'org_id' not in existing_columns:
        cursor.execute("ALTER TABLE leads ADD COLUMN org_id INTEGER DEFAULT NULL REFERENCES organizations(id)")

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


    cursor.execute('PRAGMA table_info(professionals)')

    pro_columns = [row[1] for row in cursor.fetchall()]

    if 'user_id' not in pro_columns:
        cursor.execute('ALTER TABLE professionals ADD COLUMN user_id INTEGER DEFAULT NULL')
        cursor.execute('''
            UPDATE professionals SET user_id = (
                SELECT u.id FROM users u WHERE u.username = professionals.name
            ) WHERE user_id IS NULL
        ''')


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


    cursor.execute('PRAGMA table_info(notifications)')

    notif_cols = [r[1] for r in cursor.fetchall()]
    if 'actor_id' not in notif_cols:
        cursor.execute("ALTER TABLE notifications ADD COLUMN actor_id INTEGER REFERENCES users(id)")
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_notifications_actor ON notifications(actor_id)')

    if current_ver < 6:
        cursor.execute("UPDATE notifications SET type = 'lead' WHERE type = 'lead'")
        cursor.execute("UPDATE notifications SET type = 'lead_assigned' WHERE title LIKE '%asignado%' AND type = 'lead'")
        cursor.execute("UPDATE notifications SET type = 'lead_new' WHERE title LIKE '%nuevo lead%' AND type = 'lead'")
        cursor.execute("UPDATE notifications SET type = 'lead_status' WHERE (title LIKE '%visto%' OR title LIKE '%contactado%') AND type = 'lead'")


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

    if 'org_id' not in pro_cols:
        cursor.execute("ALTER TABLE professionals ADD COLUMN org_id INTEGER DEFAULT NULL REFERENCES organizations(id)")

    cursor.execute('PRAGMA table_info(audit_log)')

    al_cols = [r[1] for r in cursor.fetchall()]

    if 'user_id' not in al_cols:
        cursor.execute("ALTER TABLE audit_log ADD COLUMN user_id INTEGER REFERENCES users(id)")


    cursor.execute('''
        INSERT OR IGNORE INTO org_members (org_id, user_id, role)
        SELECT p.org_id, p.user_id, 'member' FROM professionals p
        WHERE p.org_id IS NOT NULL
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS idempotency_keys (
            key TEXT PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES users(id),
            lead_id INTEGER REFERENCES leads(id),
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Backstops de concurrencia (toleran datos preexistentes duplicados):
    # - un solo reporte 'pending' por profesional y lead
    # - una sola notificación de creación por profesional y lead
    # Limpieza previa: sin esto el índice único fallaría en DBs con
    # duplicados históricos (doble-clicks anteriores a este fix).
    cursor.execute('''
        UPDATE lead_reports SET status = 'dismissed', reviewed_by = 'migration-dedup'
        WHERE status = 'pending' AND id NOT IN (
            SELECT MIN(id) FROM lead_reports WHERE status = 'pending'
            GROUP BY lead_id, reported_by
        )
    ''')
    # Alineado con idx_notif_lead_created_once (user_id, lead_id): un par con
    # ambos tipos (lead_new + lead_assigned) también violaría el índice.
    cursor.execute('''
        DELETE FROM notifications WHERE id NOT IN (
            SELECT MIN(id) FROM notifications
            WHERE type IN ('lead_new', 'lead_assigned')
            GROUP BY user_id, lead_id
        ) AND type IN ('lead_new', 'lead_assigned')
    ''')
    cursor.execute('''
        CREATE UNIQUE INDEX IF NOT EXISTS idx_lead_reports_pending_once
        ON lead_reports(lead_id, reported_by) WHERE status = 'pending'
    ''')
    cursor.execute('''
        CREATE UNIQUE INDEX IF NOT EXISTS idx_notif_lead_created_once
        ON notifications(user_id, lead_id) WHERE type IN ('lead_new', 'lead_assigned')
    ''')

    # Índices al final: algunos referencian columnas creadas por migraciones.
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_org_members_org ON org_members(org_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_org_members_user ON org_members(user_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_leads_org ON leads(org_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_pro_coverage_user ON professional_coverage(user_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_remember_tokens_selector ON remember_tokens(selector)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_remember_tokens_expires ON remember_tokens(expires_at)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_notifications_user ON notifications(user_id, is_read)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_notifications_created ON notifications(created_at)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_password_reset_token ON password_reset_tokens(token)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_password_reset_expires ON password_reset_tokens(expires_at)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_professionals_org ON professionals(org_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_leads_user_id ON leads(user_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_leads_timestamp ON leads(timestamp)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_leads_zone ON leads(zone)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_leads_type ON leads(type)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_leads_assigned ON leads(assigned_to)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_leads_property_type ON leads(property_type)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_lead_reports_lead_reported ON lead_reports(lead_id, reported_by)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_notifications_user_created ON notifications(user_id, created_at)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_professionals_user_id ON professionals(user_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_professionals_name ON professionals(name)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_professionals_status ON professionals(status)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_lead_tracking_professional ON lead_tracking(professional_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_lead_tracking_lead ON lead_tracking(lead_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_lead_stages_pro ON lead_stages(professional_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_lead_stages_lead ON lead_stages(lead_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_lead_stages_stage ON lead_stages(professional_id, stage)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_stage_history_pro ON lead_stage_history(professional_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_stage_history_lead ON lead_stage_history(lead_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_cal_events_pro ON calendar_events(professional_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_cal_events_date ON calendar_events(professional_id, event_date)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_cal_events_type ON calendar_events(professional_id, event_type)')
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
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_leads_email ON leads(email)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_cal_events_lead ON calendar_events(lead_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_notifications_lead ON notifications(lead_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_remember_tokens_user ON remember_tokens(user_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_consent_log_user ON consent_log(user_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_lead_versions_creator ON lead_versions(created_by)')

    if current_ver < 8:
        _dedupe_and_unique_indexes(cursor)
        cursor.execute('INSERT OR IGNORE INTO schema_version (version) VALUES (8)')

