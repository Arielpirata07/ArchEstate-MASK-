import sqlite3

import config
import utils


def get_db_connection():
    conn = sqlite3.connect(config.DATABASE)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA journal_mode=WAL')
    conn.execute('PRAGMA busy_timeout=5000')
    return conn


def get_user_by_id(user_id):
    conn = get_db_connection()
    try:
        user = conn.execute('SELECT id, username, email, phone, hash, role, doc_path, is_active, phone_verified FROM users WHERE id = ?', (user_id,)).fetchone()
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
            'SELECT u.id, u.username, u.email, u.phone, u.role, u.is_active, u.phone_verified, '
            'u.verification_channel, '
            'up.first_name, up.last_name, up.bio, up.title, up.avatar_path, '
            'up.created_at, up.updated_at '
            'FROM users u LEFT JOIN user_profiles up ON u.id = up.user_id WHERE u.id = ?',
            (user_id,)
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


ALLOWED_PROFILE_FIELDS = {'first_name', 'last_name', 'bio', 'title', 'avatar_path'}


def update_user_profile(user_id, data):
    conn = get_db_connection()
    try:
        filtered = {k: v for k, v in data.items() if k in ALLOWED_PROFILE_FIELDS}
        if not filtered:
            return False

        existing = conn.execute('SELECT id FROM user_profiles WHERE user_id = ?', (user_id,)).fetchone()
        if existing:
            set_clause = ', '.join(f'{k} = ?' for k in filtered.keys())
            values = list(filtered.values()) + [user_id]
            conn.execute(f'UPDATE user_profiles SET {set_clause}, updated_at = CURRENT_TIMESTAMP WHERE user_id = ?', values)
        else:
            filtered['user_id'] = user_id
            columns = ', '.join(filtered.keys())
            placeholders = ', '.join('?' for _ in filtered)
            values = list(filtered.values())
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
        current = conn.execute('SELECT phone, phone_e164, phone_verified FROM users WHERE id = ?',
                               (user_id,)).fetchone()

        if phone and current:
            old_phone = current['phone'] or ''
            e164 = utils.normalize_phone_to_e164(phone)
            ntype = utils.classify_phone_type(e164) if e164 else ''
            old_e164 = utils.normalize_phone_to_e164(old_phone) if old_phone else ''
            phone_changed = bool(e164) and (old_e164 != e164)

            if phone_changed:
                conn.execute(
                    'UPDATE users SET email = ?, phone = ?, phone_e164 = ?, phone_number_type = ?, '
                    'phone_format_valid = 1, phone_verified = 0, verification_code = \'\', verification_expires = NULL '
                    'WHERE id = ?',
                    (email, phone, e164, ntype, user_id)
                )
            else:
                conn.execute(
                    'UPDATE users SET email = ?, phone = ?, phone_e164 = ?, phone_number_type = ?, '
                    'phone_format_valid = 1 WHERE id = ?',
                    (email, phone, e164, ntype, user_id)
                )
        else:
            conn.execute(
                'UPDATE users SET email = ?, phone = ?, phone_e164 = \'\', phone_number_type = \'\', '
                'phone_format_valid = 0, phone_verified = 0 WHERE id = ?',
                (email, phone, user_id)
            )

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


def get_user_preferences(user_id):
    conn = get_db_connection()
    try:
        prefs = conn.execute(
            'SELECT * FROM user_preferences WHERE user_id = ?', (user_id,)
        ).fetchone()
        if prefs:
            return dict(prefs)
        return {
            'user_id': user_id,
            'theme': 'light',
            'language': 'es',
            'email_notifications': 1,
            'sms_notifications': 1,
            'lead_alerts': 1,
            'preferred_channel': 'auto',
        }
    finally:
        conn.close()


def update_user_preferences(user_id, data):
    conn = get_db_connection()
    try:
        existing = conn.execute(
            'SELECT user_id FROM user_preferences WHERE user_id = ?', (user_id,)
        ).fetchone()
        if existing:
            set_clause = ', '.join(f'{k} = ?' for k in data.keys())
            values = list(data.values()) + [user_id]
            conn.execute(f'UPDATE user_preferences SET {set_clause}, updated_at = CURRENT_TIMESTAMP WHERE user_id = ?', values)
        else:
            data['user_id'] = user_id
            columns = ', '.join(data.keys())
            placeholders = ', '.join('?' for _ in data)
            conn.execute(f'INSERT INTO user_preferences ({columns}) VALUES ({placeholders})', list(data.values()))
        conn.commit()
        return True
    except Exception:
        return False
    finally:
        conn.close()


def get_professional_full_profile(user_id):
    conn = get_db_connection()
    try:
        row = conn.execute(
            'SELECT p.id as prof_id, p.name, p.license, p.specialty, p.status, p.license_verified, '
            'pp.id as pro_profile_id, pp.photo_path, pp.bio_pro, pp.experience_years, '
            'pp.services_offered, pp.portfolio, pp.availability, pp.social_links, '
            'pp.fee_range_min, pp.fee_range_max, pp.professional_address, '
            'pp.created_at, pp.updated_at '
            'FROM professionals p '
            'LEFT JOIN professional_profiles pp ON p.user_id = pp.user_id '
            'WHERE p.user_id = ?',
            (user_id,)
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def create_or_update_professional_profile(user_id, data):
    conn = get_db_connection()
    try:
        existing = conn.execute(
            'SELECT id FROM professional_profiles WHERE user_id = ?', (user_id,)
        ).fetchone()
        if existing:
            set_clause = ', '.join(f'{k} = ?' for k in data.keys())
            values = list(data.values()) + [user_id]
            conn.execute(f'UPDATE professional_profiles SET {set_clause}, updated_at = CURRENT_TIMESTAMP WHERE user_id = ?', values)
        else:
            data['user_id'] = user_id
            columns = ', '.join(data.keys())
            placeholders = ', '.join('?' for _ in data)
            conn.execute(f'INSERT INTO professional_profiles ({columns}) VALUES ({placeholders})', list(data.values()))
        conn.commit()
        return True
    except Exception:
        return False
    finally:
        conn.close()


def _ensure_user_profile(user_id):
    conn = get_db_connection()
    try:
        existing = conn.execute('SELECT id FROM user_profiles WHERE user_id = ?', (user_id,)).fetchone()
        if not existing:
            conn.execute('INSERT INTO user_profiles (user_id) VALUES (?)', (user_id,))
            conn.commit()
    except Exception:
        pass
    finally:
        conn.close()


def get_user_avatar_path(user_id):
    conn = get_db_connection()
    try:
        row = conn.execute('SELECT avatar_path FROM user_profiles WHERE user_id = ?', (user_id,)).fetchone()
        return row['avatar_path'] if row and row['avatar_path'] else None
    finally:
        conn.close()


def update_user_avatar(user_id, path):
    _ensure_user_profile(user_id)
    conn = get_db_connection()
    try:
        conn.execute('UPDATE user_profiles SET avatar_path = ? WHERE user_id = ?', (path, user_id))
        conn.commit()
        return True
    except Exception:
        return False
    finally:
        conn.close()


def get_professional_photo_path(user_id):
    conn = get_db_connection()
    try:
        row = conn.execute('SELECT photo_path FROM professional_profiles WHERE user_id = ?', (user_id,)).fetchone()
        return row['photo_path'] if row and row['photo_path'] else None
    finally:
        conn.close()


def delete_user_avatar(user_id):
    conn = get_db_connection()
    try:
        conn.execute("UPDATE user_profiles SET avatar_path = '' WHERE user_id = ?", (user_id,))
        conn.commit()
        return True
    except Exception:
        return False
    finally:
        conn.close()


def get_user_login_history(user_id, limit=20):
    conn = get_db_connection()
    try:
        rows = conn.execute(
            'SELECT * FROM user_login_history WHERE user_id = ? ORDER BY last_active DESC LIMIT ?',
            (user_id, limit)
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def delete_login_history_entry(entry_id, user_id):
    conn = get_db_connection()
    try:
        conn.execute(
            'DELETE FROM user_login_history WHERE id = ? AND user_id = ?',
            (entry_id, user_id)
        )
        conn.commit()
        return conn.total_changes > 0
    finally:
        conn.close()


def get_user_activity(user_id, limit=50):
    conn = get_db_connection()
    try:
        rows = conn.execute(
            'SELECT * FROM audit_log WHERE user_id = ? ORDER BY timestamp DESC LIMIT ?',
            (user_id, limit)
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_professional_by_license(license_number):
    conn = get_db_connection()
    try:
        pro = conn.execute(
            'SELECT * FROM professionals WHERE license = ?', (license_number,)
        ).fetchone()
        return dict(pro) if pro else None
    finally:
        conn.close()


FORM_OPTION_CATEGORIES = [
    'property_type', 'operation_type', 'currency', 'parking',
    'orientation', 'condition', 'age', 'budget_range',
    'province', 'architectural_style', 'amenities'
]


def get_form_options(category=None, active_only=True):
    conn = get_db_connection()
    try:
        if category:
            if active_only:
                rows = conn.execute(
                    'SELECT * FROM form_options WHERE category = ? AND is_active = 1 ORDER BY sort_order, label',
                    (category,)
                ).fetchall()
            else:
                rows = conn.execute(
                    'SELECT * FROM form_options WHERE category = ? ORDER BY sort_order, label',
                    (category,)
                ).fetchall()
        else:
            if active_only:
                rows = conn.execute(
                    'SELECT * FROM form_options WHERE is_active = 1 ORDER BY category, sort_order, label'
                ).fetchall()
            else:
                rows = conn.execute(
                    'SELECT * FROM form_options ORDER BY category, sort_order, label'
                ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_form_options_by_category(category, active_only=True):
    opts = get_form_options(category, active_only)
    return [o['value'] for o in opts]


def get_form_option_by_id(option_id):
    conn = get_db_connection()
    try:
        row = conn.execute('SELECT * FROM form_options WHERE id = ?', (option_id,)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def get_form_option_by_id_value(category, value):
    conn = get_db_connection()
    try:
        row = conn.execute(
            'SELECT * FROM form_options WHERE category = ? AND value = ?', (category, value)
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def _shift_sort_order(conn, category, from_order):
    conn.execute(
        'UPDATE form_options SET sort_order = sort_order + 1 WHERE category = ? AND sort_order >= ?',
        (category, from_order)
    )


def create_form_option(data):
    conn = get_db_connection()
    try:
        sort_order = data.get('sort_order', 0)
        _shift_sort_order(conn, data['category'], sort_order)
        try:
            cursor = conn.execute(
                'INSERT INTO form_options (category, value, label, icon, sort_order, is_active) VALUES (?, ?, ?, ?, ?, ?)',
                (data['category'], data['value'], data['label'],
                 data.get('icon', ''), sort_order, data.get('is_active', 1))
            )
            conn.commit()
            return cursor.lastrowid
        except Exception:
            conn.rollback()
            raise
    finally:
        conn.close()


def update_form_option(option_id, data):
    conn = get_db_connection()
    try:
        existing = conn.execute('SELECT category, sort_order FROM form_options WHERE id = ?', (option_id,)).fetchone()
        if not existing:
            return False
        allowed = {'value', 'label', 'icon', 'sort_order', 'is_active'}
        filtered = {k: v for k, v in data.items() if k in allowed}
        if not filtered:
            return False
        if 'sort_order' in filtered and filtered['sort_order'] != existing['sort_order']:
            new_order = filtered['sort_order']
            old_order = existing['sort_order']
            category = existing['category']
            if new_order > old_order:
                conn.execute(
                    'UPDATE form_options SET sort_order = sort_order - 1 WHERE category = ? AND sort_order > ? AND sort_order <= ?',
                    (category, old_order, new_order)
                )
            else:
                conn.execute(
                    'UPDATE form_options SET sort_order = sort_order + 1 WHERE category = ? AND sort_order >= ? AND sort_order < ?',
                    (category, new_order, old_order)
                )
        try:
            set_clause = ', '.join(f'{k} = ?' for k in filtered.keys())
            values = list(filtered.values()) + [option_id]
            conn.execute(f'UPDATE form_options SET {set_clause} WHERE id = ?', values)
            conn.commit()
            return True
        except Exception:
            conn.rollback()
            raise
    finally:
        conn.close()


def delete_form_option(option_id):
    conn = get_db_connection()
    try:
        row = conn.execute('SELECT category, sort_order FROM form_options WHERE id = ?', (option_id,)).fetchone()
        if not row:
            return False
        conn.execute('DELETE FROM form_options WHERE id = ?', (option_id,))
        conn.execute(
            'UPDATE form_options SET sort_order = sort_order - 1 WHERE category = ? AND sort_order > ?',
            (row['category'], row['sort_order'])
        )
        conn.commit()
        return True
    finally:
        conn.close()