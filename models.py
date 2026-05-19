import sqlite3

import config


def get_db_connection():
    conn = sqlite3.connect(config.DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def get_user_by_id(user_id):
    conn = get_db_connection()
    try:
        user = conn.execute('SELECT id, username, email, phone, hash, role, doc_path, is_active FROM users WHERE id = ?', (user_id,)).fetchone()
        return dict(user) if user else None
    finally:
        conn.close()


def get_user_by_username(username):
    conn = get_db_connection()
    try:
        user = conn.execute('SELECT id, username, email, hash, role, doc_path, is_active FROM users WHERE username = ?', (username,)).fetchone()
        return dict(user) if user else None
    finally:
        conn.close()


def get_leads(filters=None):
    conn = get_db_connection()
    try:
        query = 'SELECT * FROM leads WHERE 1=1'
        params = []

        if filters:
            if filters.get('type'):
                query += ' AND type = ?'
                params.append(filters['type'])
            if filters.get('property_type'):
                query += ' AND property_type = ?'
                params.append(filters['property_type'])
            if filters.get('zone'):
                query += ' AND zone LIKE ?'
                params.append(f'%{filters["zone"]}%')
            if filters.get('currency'):
                query += ' AND currency = ?'
                params.append(filters['currency'])

        query += ' ORDER BY timestamp DESC'
        leads = conn.execute(query, params).fetchall()
        return [dict(lead) for lead in leads]
    finally:
        conn.close()


def get_lead_by_id(lead_id):
    conn = get_db_connection()
    try:
        lead = conn.execute('SELECT * FROM leads WHERE id = ?', (lead_id,)).fetchone()
        return dict(lead) if lead else None
    finally:
        conn.close()


def create_lead(data):
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO leads (type, property_type, zone, budget, currency, phone, email, floor_block, usable_m2, elevator, land_area, built_area, pool)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            data.get('type'),
            data.get('property_type', 'departamento'),
            data.get('zone'),
            data.get('budget'),
            data.get('currency', 'ARG'),
            data.get('phone'),
            data.get('email'),
            data.get('floor_block', ''),
            data.get('usable_m2', 0),
            data.get('elevator', ''),
            data.get('land_area', 0),
            data.get('built_area', 0),
            data.get('pool', '')
        ))
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def get_audit_logs(limit=100):
    conn = get_db_connection()
    try:
        logs = conn.execute('SELECT * FROM audit_log ORDER BY timestamp DESC LIMIT ?', (limit,)).fetchall()
        return [dict(log) for log in logs]
    finally:
        conn.close()


def get_professional_by_user_id(user_id):
    conn = get_db_connection()
    try:
        pro = conn.execute('SELECT * FROM professionals WHERE user_id = ?', (user_id,)).fetchone()
        return dict(pro) if pro else None
    finally:
        conn.close()


def get_professional_by_name(name):
    conn = get_db_connection()
    try:
        pro = conn.execute('SELECT * FROM professionals WHERE name = ?', (name,)).fetchone()
        return dict(pro) if pro else None
    finally:
        conn.close()


def get_user_leads(user_id):
    conn = get_db_connection()
    try:
        leads = conn.execute(
            'SELECT * FROM leads WHERE user_id = ? ORDER BY timestamp DESC',
            (user_id,)
        ).fetchall()
        return [dict(l) for l in leads]
    finally:
        conn.close()


def get_lead_by_id_and_user(lead_id, user_id):
    conn = get_db_connection()
    try:
        lead = conn.execute(
            'SELECT * FROM leads WHERE id = ? AND user_id = ?',
            (lead_id, user_id)
        ).fetchone()
        return dict(lead) if lead else None
    finally:
        conn.close()


def update_lead(lead_id, data):
    conn = get_db_connection()
    try:
        set_clause = ', '.join(f'{k} = ?' for k in data.keys())
        values = list(data.values()) + [lead_id]
        conn.execute(f'UPDATE leads SET {set_clause} WHERE id = ?', values)
        conn.commit()
        return True
    except Exception:
        return False
    finally:
        conn.close()


def get_lead_max_version(lead_id):
    conn = get_db_connection()
    try:
        row = conn.execute(
            'SELECT COALESCE(MAX(version), 0) as max_ver FROM lead_versions WHERE lead_id = ?',
            (lead_id,)
        ).fetchone()
        return row['max_ver'] if row else 0
    finally:
        conn.close()


def create_lead_version(lead_id, version, snapshot, user_id, summary):
    conn = get_db_connection()
    try:
        cursor = conn.execute(
            'INSERT INTO lead_versions (lead_id, version, data_snapshot, created_by, change_summary) VALUES (?, ?, ?, ?, ?)',
            (lead_id, version, snapshot, user_id, summary)
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def get_lead_versions(lead_id):
    conn = get_db_connection()
    try:
        versions = conn.execute(
            'SELECT * FROM lead_versions WHERE lead_id = ? ORDER BY version DESC',
            (lead_id,)
        ).fetchall()
        return [dict(v) for v in versions]
    finally:
        conn.close()


def get_user_profile(user_id):
    conn = get_db_connection()
    try:
        row = conn.execute(
            'SELECT u.id, u.username, u.email, u.phone, u.role, u.is_active, '
            'up.first_name, up.last_name, up.bio, up.title, up.created_at, up.updated_at '
            'FROM users u LEFT JOIN user_profiles up ON u.id = up.user_id WHERE u.id = ?',
            (user_id,)
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def update_user_profile(user_id, data):
    conn = get_db_connection()
    try:
        existing = conn.execute('SELECT id FROM user_profiles WHERE user_id = ?', (user_id,)).fetchone()
        if existing:
            set_clause = ', '.join(f'{k} = ?' for k in data.keys())
            values = list(data.values()) + [user_id]
            conn.execute(f'UPDATE user_profiles SET {set_clause}, updated_at = CURRENT_TIMESTAMP WHERE user_id = ?', values)
        else:
            data['user_id'] = user_id
            columns = ', '.join(data.keys())
            placeholders = ', '.join('?' for _ in data)
            values = list(data.values())
            conn.execute(f'INSERT INTO user_profiles ({columns}) VALUES ({placeholders})', values)
        conn.commit()
        return True
    except Exception:
        return False
    finally:
        conn.close()


def update_user_credentials(user_id, email, phone):
    conn = get_db_connection()
    try:
        conn.execute('UPDATE users SET email = ?, phone = ? WHERE id = ?', (email, phone, user_id))
        conn.commit()
        return True
    except Exception:
        return False
    finally:
        conn.close()


def update_professional_profile(user_id, data):
    conn = get_db_connection()
    try:
        set_clause = ', '.join(f'{k} = ?' for k in data.keys())
        values = list(data.values()) + [user_id]
        conn.execute(f'UPDATE professionals SET {set_clause} WHERE user_id = ?', values)
        conn.commit()
        return True
    except Exception:
        return False
    finally:
        conn.close()