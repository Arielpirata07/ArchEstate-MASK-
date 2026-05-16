import sqlite3

import config


def get_db_connection():
    conn = sqlite3.connect(config.DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def get_user_by_id(user_id):
    conn = get_db_connection()
    try:
        user = conn.execute('SELECT id, username, email, hash, role, doc_path, is_active FROM users WHERE id = ?', (user_id,)).fetchone()
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