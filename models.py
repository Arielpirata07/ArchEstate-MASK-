import logging
import threading
import time

import config
import utils

logger = logging.getLogger(__name__)


class SimpleTTLCache:
    """Thread-safe in-memory cache with per-key TTL."""

    def __init__(self, ttl_seconds=60):
        self._cache = {}
        self._timestamps = {}
        self._ttl = ttl_seconds
        self._lock = threading.Lock()

    def get(self, key):
        with self._lock:
            if key in self._cache:
                if time.time() - self._timestamps[key] < self._ttl:
                    return self._cache[key]
                del self._cache[key]
                del self._timestamps[key]
        return None

    def set(self, key, value):
        with self._lock:
            self._cache[key] = value
            self._timestamps[key] = time.time()

    def invalidate(self, key):
        with self._lock:
            self._cache.pop(key, None)
            self._timestamps.pop(key, None)

    def invalidate_prefix(self, prefix):
        with self._lock:
            keys_to_del = [k for k in self._cache if k.startswith(prefix)]
            for k in keys_to_del:
                del self._cache[k]
                del self._timestamps[k]


_prefs_cache = SimpleTTLCache(ttl_seconds=60)
_form_options_cache = SimpleTTLCache(ttl_seconds=60)

logger = logging.getLogger(__name__)


class DatabaseError(Exception):
    pass


def get_db_connection():
    from services.database import get_db_connection as _get_db
    try:
        return _get_db()
    except Exception:
        logger.exception('Error al conectar a la base de datos')
        raise DatabaseError('No se pudo conectar a la base de datos')


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
        leads = conn.execute('''
            SELECT l.*,
                   COALESCE(lt.seen_count, 0) AS seen_count,
                   COALESCE(lt.contacted_count, 0) AS contacted_count,
                   lt.contact_names
            FROM leads l
            LEFT JOIN (
                SELECT lead_id,
                       SUM(seen) AS seen_count,
                       SUM(contacted) AS contacted_count,
                       GROUP_CONCAT(
                           CASE WHEN contacted = 1
                           THEN p.name || ' (' || p.specialty || ')' END,
                           ', '
                       ) AS contact_names
                FROM lead_tracking lt2
                LEFT JOIN professionals p ON p.user_id = lt2.professional_id
                GROUP BY lead_id
            ) lt ON l.id = lt.lead_id
            WHERE l.user_id = ?
            ORDER BY l.timestamp DESC
        ''', (user_id,)).fetchall()
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
    filtered = {k: v for k, v in data.items() if k in ALLOWED_LEAD_UPDATE_FIELDS}
    if not filtered:
        return False
    conn = get_db_connection()
    try:
        set_clause = ', '.join(f'{k} = ?' for k in filtered.keys())
        values = list(filtered.values()) + [lead_id]
        conn.execute(f'UPDATE leads SET {set_clause} WHERE id = ?', values)
        conn.commit()
        return True
    except Exception:
        logger.exception('update_lead failed for lead_id=%s', lead_id)
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
ALLOWED_LEAD_UPDATE_FIELDS = {
    'zone', 'province', 'budget', 'currency',
    'floor_block', 'usable_m2', 'elevator',
    'land_area', 'built_area', 'pool',
    'architectural_style', 'bedrooms', 'bathrooms',
    'total_area', 'amenities', 'ambientes',
    'parking', 'orientation', 'property_condition',
    'property_age', 'community_pool', 'additional_features',
    'phone_format_valid',
}
ALLOWED_PROFESSIONAL_FIELDS = {'specialty', 'title', 'province', 'zone', 'country'}
ALLOWED_PROFESSIONAL_PROFILE_FIELDS = {
    'bio_pro', 'experience_years', 'services_offered',
    'portfolio', 'availability', 'social_links',
    'fee_range_min', 'fee_range_max', 'professional_address',
    'photo_path',
}
ALLOWED_PREFERENCES_FIELDS = {
    'theme', 'language', 'email_notifications', 'sms_notifications',
    'lead_alerts', 'preferred_channel', 'whatsapp_notifications',
    'notification_filters', 'budget_min', 'budget_max',
}


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
        logger.exception('update_user_profile failed for user_id=%s', user_id)
        return False
    finally:
        conn.close()


def update_user_phone_only(user_id, phone):
    """
    Actualiza el teléfono de un usuario con normalización E.164 y
    invalidación condicional de OTP si el número cambió.
    Retorna dict con el resultado de la operación.
    """
    conn = get_db_connection()
    try:
        current = conn.execute(
            'SELECT phone, phone_verified FROM users WHERE id = ?', (user_id,)
        ).fetchone()

        old_phone = current['phone'] if current else ''
        e164 = utils.normalize_phone_to_e164(phone)
        ntype = utils.classify_phone_type(e164) if e164 else ''
        old_e164 = utils.normalize_phone_to_e164(old_phone) if old_phone else ''
        invalidate_otp = bool(e164) and (old_e164 != e164)

        if invalidate_otp:
            conn.execute(
                'UPDATE users SET phone = ?, phone_e164 = ?, phone_number_type = ?, '
                'phone_format_valid = 1, phone_verified = 0, verification_code = \'\', '
                'verification_expires = NULL WHERE id = ?',
                (phone, e164, ntype, user_id)
            )
        else:
            conn.execute(
                'UPDATE users SET phone = ?, phone_e164 = ?, phone_number_type = ? WHERE id = ?',
                (phone, e164, ntype, user_id)
            )
        conn.commit()

        return {
            'success': True,
            'phone': phone,
            'phone_e164': e164,
            'invalidate_otp': invalidate_otp,
            'phone_verified': 0 if invalidate_otp else (current['phone_verified'] if current else 0),
        }
    except Exception:
        logger.exception('update_user_phone_only failed for user_id=%s', user_id)
        return {'success': False}
    finally:
        conn.close()


def update_user_credentials(user_id, email, phone):
    if phone:
        phone_result = update_user_phone_only(user_id, phone)
        if not phone_result['success']:
            return False

    conn = get_db_connection()
    try:
        conn.execute('UPDATE users SET email = ? WHERE id = ?', (email, user_id))
        conn.commit()
        return True
    except Exception:
        return False
    finally:
        conn.close()


def update_professional_profile(user_id, data):
    filtered = {k: v for k, v in data.items() if k in ALLOWED_PROFESSIONAL_FIELDS}
    if not filtered:
        return False
    conn = get_db_connection()
    try:
        set_clause = ', '.join(f'{k} = ?' for k in filtered.keys())
        values = list(filtered.values()) + [user_id]
        conn.execute(f'UPDATE professionals SET {set_clause} WHERE user_id = ?', values)
        conn.commit()
        return True
    except Exception:
        logger.exception('update_professional_profile failed for user_id=%s', user_id)
        return False
    finally:
        conn.close()


def get_user_preferences(user_id):
    cache_key = f'prefs:{user_id}'
    cached = _prefs_cache.get(cache_key)
    if cached is not None:
        return cached
    conn = get_db_connection()
    try:
        prefs = conn.execute(
            'SELECT * FROM user_preferences WHERE user_id = ?', (user_id,)
        ).fetchone()
        if prefs:
            result = dict(prefs)
        else:
            result = {
                'user_id': user_id,
                'theme': 'light',
                'language': 'es',
                'email_notifications': 1,
                'sms_notifications': 1,
                'lead_alerts': 1,
                'preferred_channel': 'auto',
                'whatsapp_notifications': 1,
                'budget_min': 0,
                'budget_max': 0,
            }
        _prefs_cache.set(cache_key, result)
        return result
    finally:
        conn.close()


def get_user_preferences_batch(user_ids):
    if not user_ids:
        return {}
    conn = get_db_connection()
    try:
        placeholders = ','.join('?' for _ in user_ids)
        rows = conn.execute(
            f'SELECT * FROM user_preferences WHERE user_id IN ({placeholders})',
            user_ids
        ).fetchall()
        prefs_map = {r['user_id']: dict(r) for r in rows}
        defaults = {
            'theme': 'light', 'language': 'es',
            'email_notifications': 1, 'sms_notifications': 1,
            'lead_alerts': 1, 'preferred_channel': 'auto',
            'whatsapp_notifications': 1, 'budget_min': 0, 'budget_max': 0,
        }
        result = {}
        for uid in user_ids:
            if uid in prefs_map:
                result[uid] = prefs_map[uid]
            else:
                result[uid] = dict({'user_id': uid}, **defaults)
        return result
    finally:
        conn.close()


def update_user_preferences(user_id, data):
    filtered = {k: v for k, v in data.items() if k in ALLOWED_PREFERENCES_FIELDS}
    if not filtered:
        return False
    conn = get_db_connection()
    try:
        existing = conn.execute(
            'SELECT user_id FROM user_preferences WHERE user_id = ?', (user_id,)
        ).fetchone()
        if existing:
            set_clause = ', '.join(f'{k} = ?' for k in filtered.keys())
            values = list(filtered.values()) + [user_id]
            conn.execute(f'UPDATE user_preferences SET {set_clause}, updated_at = CURRENT_TIMESTAMP WHERE user_id = ?', values)
        else:
            filtered['user_id'] = user_id
            columns = ', '.join(filtered.keys())
            placeholders = ', '.join('?' for _ in filtered)
            conn.execute(f'INSERT INTO user_preferences ({columns}) VALUES ({placeholders})', list(filtered.values()))
        conn.commit()
        _prefs_cache.invalidate(f'prefs:{user_id}')
        return True
    except Exception:
        logger.exception('update_user_preferences failed for user_id=%s', user_id)
        return False
    finally:
        conn.close()


def get_professional_full_profile(user_id):
    conn = get_db_connection()
    try:
        row = conn.execute(
            'SELECT p.id as prof_id, p.name, p.license, p.specialty, p.status, p.license_verified, '
            'p.province, p.zone, p.country, '
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
    filtered = {k: v for k, v in data.items() if k in ALLOWED_PROFESSIONAL_PROFILE_FIELDS}
    if not filtered:
        return False
    conn = get_db_connection()
    try:
        existing = conn.execute(
            'SELECT id FROM professional_profiles WHERE user_id = ?', (user_id,)
        ).fetchone()
        if existing:
            set_clause = ', '.join(f'{k} = ?' for k in filtered.keys())
            values = list(filtered.values()) + [user_id]
            conn.execute(f'UPDATE professional_profiles SET {set_clause}, updated_at = CURRENT_TIMESTAMP WHERE user_id = ?', values)
        else:
            filtered['user_id'] = user_id
            columns = ', '.join(filtered.keys())
            placeholders = ', '.join('?' for _ in filtered)
            conn.execute(f'INSERT INTO professional_profiles ({columns}) VALUES ({placeholders})', list(filtered.values()))
        conn.commit()
        return True
    except Exception:
        logger.exception('create_or_update_professional_profile failed for user_id=%s', user_id)
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
        logger.exception('_ensure_user_profile failed for user_id=%s', user_id)
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
        cursor = conn.execute(
            'DELETE FROM user_login_history WHERE id = ? AND user_id = ?',
            (entry_id, user_id)
        )
        conn.commit()
        return cursor.rowcount > 0
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
    'province', 'architectural_style', 'amenities', 'country'
]


def get_form_options(category=None, active_only=True):
    cache_key = f'form_options:{category}:{active_only}'
    cached = _form_options_cache.get(cache_key)
    if cached is not None:
        return cached
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
        result = [dict(r) for r in rows]
        _form_options_cache.set(cache_key, result)
        return result
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
            _form_options_cache.invalidate_prefix('form_options:')
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
            _form_options_cache.invalidate_prefix('form_options:')
            return True
        except Exception:
            conn.rollback()
            raise
    finally:
        conn.close()


def get_user_notifications(user_id: int, limit: int = 20, unread_only: bool = False) -> list:
    conn = get_db_connection()
    try:
        query = '''
            SELECT n.*, actor.username AS actor_username
            FROM notifications n
            LEFT JOIN users actor ON n.actor_id = actor.id
            WHERE n.user_id = ?
        '''
        params = [user_id]
        if unread_only:
            query += ' AND n.is_read = 0'
        query += ' ORDER BY n.created_at DESC LIMIT ?'
        params.append(limit)
        rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_unread_notification_count(user_id: int) -> int:
    conn = get_db_connection()
    try:
        row = conn.execute(
            'SELECT COUNT(*) as cnt FROM notifications WHERE user_id = ? AND is_read = 0',
            (user_id,)
        ).fetchone()
        return row['cnt'] if row else 0
    finally:
        conn.close()


def mark_notification_read(notification_id: int, user_id: int) -> bool:
    conn = get_db_connection()
    try:
        cursor = conn.execute(
            'UPDATE notifications SET is_read = 1 WHERE id = ? AND user_id = ?',
            (notification_id, user_id)
        )
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()


def mark_all_notifications_read(user_id: int) -> bool:
    conn = get_db_connection()
    try:
        conn.execute(
            'UPDATE notifications SET is_read = 1 WHERE user_id = ? AND is_read = 0',
            (user_id,)
        )
        conn.commit()
        return True
    finally:
        conn.close()


def delete_notification(notification_id: int, user_id: int) -> bool:
    conn = get_db_connection()
    try:
        cursor = conn.execute(
            'DELETE FROM notifications WHERE id = ? AND user_id = ?',
            (notification_id, user_id)
        )
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()


def delete_read_notifications(user_id: int) -> int:
    conn = get_db_connection()
    try:
        cursor = conn.execute(
            'DELETE FROM notifications WHERE user_id = ? AND is_read = 1',
            (user_id,)
        )
        conn.commit()
        return cursor.rowcount
    finally:
        conn.close()


def get_all_user_notifications(user_id: int, page: int = 1, per_page: int = 20) -> dict:
    conn = get_db_connection()
    try:
        count_row = conn.execute(
            'SELECT COUNT(*) as cnt FROM notifications WHERE user_id = ?',
            (user_id,)
        ).fetchone()
        total = count_row['cnt'] if count_row else 0
        pages = max(1, -(-total // per_page))
        offset = (page - 1) * per_page
        rows = conn.execute('''
            SELECT n.*, actor.username AS actor_username
            FROM notifications n
            LEFT JOIN users actor ON n.actor_id = actor.id
            WHERE n.user_id = ?
            ORDER BY n.created_at DESC
            LIMIT ? OFFSET ?
        ''', (user_id, per_page, offset)).fetchall()
        return {'items': [dict(r) for r in rows], 'total': total, 'page': page, 'pages': pages}
    finally:
        conn.close()


def get_notifications_sent_by(actor_id: int, page: int = 1, per_page: int = 20, search: str = '') -> dict:
    conn = get_db_connection()
    try:
        params = [actor_id]
        search_clause = ''
        if search:
            search_clause = ' AND u.username LIKE ?'
            params.append(f'%{search}%')
        count_row = conn.execute(
            'SELECT COUNT(*) as cnt FROM notifications n JOIN users u ON n.user_id = u.id WHERE n.actor_id = ?' + search_clause,
            params
        ).fetchone()
        total = count_row['cnt'] if count_row else 0
        pages = max(1, -(-total // per_page))
        offset = (page - 1) * per_page
        query_params = params + [per_page, offset]
        rows = conn.execute('''
            SELECT n.*, u.username AS recipient_username
            FROM notifications n
            JOIN users u ON n.user_id = u.id
            WHERE n.actor_id = ?''' + search_clause + '''
            ORDER BY n.created_at DESC
            LIMIT ? OFFSET ?
        ''', query_params).fetchall()
        return {'items': [dict(r) for r in rows], 'total': total, 'page': page, 'pages': pages}
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
        _form_options_cache.invalidate_prefix('form_options:')
        return True
    finally:
        conn.close()


_phone_area_codes_cache = SimpleTTLCache(ttl_seconds=60)


def get_phone_area_codes(country_code=None, active_only=True):
    cache_key = f'phone_area_codes:{country_code}:{active_only}'
    cached = _phone_area_codes_cache.get(cache_key)
    if cached is not None:
        return cached
    conn = get_db_connection()
    try:
        if country_code:
            if active_only:
                rows = conn.execute(
                    'SELECT * FROM phone_area_codes WHERE country_code = ? AND is_active = 1 ORDER BY sort_order, code',
                    (country_code,)
                ).fetchall()
            else:
                rows = conn.execute(
                    'SELECT * FROM phone_area_codes WHERE country_code = ? ORDER BY sort_order, code',
                    (country_code,)
                ).fetchall()
        else:
            if active_only:
                rows = conn.execute(
                    'SELECT * FROM phone_area_codes WHERE is_active = 1 ORDER BY country_code, sort_order, code'
                ).fetchall()
            else:
                rows = conn.execute(
                    'SELECT * FROM phone_area_codes ORDER BY country_code, sort_order, code'
                ).fetchall()
        result = [dict(r) for r in rows]
        _phone_area_codes_cache.set(cache_key, result)
        return result
    finally:
        conn.close()


def get_phone_area_codes_by_country(country_code, active_only=True):
    codes = get_phone_area_codes(country_code=country_code, active_only=active_only)
    return [c['code'] for c in codes]


def get_phone_area_code_by_id(area_id):
    conn = get_db_connection()
    try:
        row = conn.execute('SELECT * FROM phone_area_codes WHERE id = ?', (area_id,)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def get_phone_area_code_by_code_country(code, country_code):
    conn = get_db_connection()
    try:
        row = conn.execute(
            'SELECT * FROM phone_area_codes WHERE code = ? AND country_code = ?', (code, country_code)
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def create_phone_area_code(data):
    conn = get_db_connection()
    try:
        sort_order = data.get('sort_order', 0)
        conn.execute(
            'UPDATE phone_area_codes SET sort_order = sort_order + 1 WHERE country_code = ? AND sort_order >= ?',
            (data.get('country_code', '+54'), sort_order)
        )
        try:
            cursor = conn.execute(
                'INSERT INTO phone_area_codes (code, city, province, country, country_code, sort_order, is_active) VALUES (?, ?, ?, ?, ?, ?, ?)',
                (data['code'], data['city'], data.get('province', ''),
                 data.get('country', 'Argentina'), data.get('country_code', '+54'),
                 sort_order, data.get('is_active', 1))
            )
            conn.commit()
            _phone_area_codes_cache.invalidate_prefix('phone_area_codes:')
            return cursor.lastrowid
        except Exception:
            conn.rollback()
            raise
    finally:
        conn.close()


def update_phone_area_code(area_id, data):
    conn = get_db_connection()
    try:
        existing = conn.execute('SELECT country_code, sort_order FROM phone_area_codes WHERE id = ?', (area_id,)).fetchone()
        if not existing:
            return False
        allowed = {'code', 'city', 'province', 'country', 'country_code', 'sort_order', 'is_active'}
        filtered = {k: v for k, v in data.items() if k in allowed}
        if not filtered:
            return False
        if 'sort_order' in filtered and filtered['sort_order'] != existing['sort_order']:
            new_order = filtered['sort_order']
            old_order = existing['sort_order']
            cc = existing['country_code']
            if new_order > old_order:
                conn.execute(
                    'UPDATE phone_area_codes SET sort_order = sort_order - 1 WHERE country_code = ? AND sort_order > ? AND sort_order <= ?',
                    (cc, old_order, new_order)
                )
            else:
                conn.execute(
                    'UPDATE phone_area_codes SET sort_order = sort_order + 1 WHERE country_code = ? AND sort_order >= ? AND sort_order < ?',
                    (cc, new_order, old_order)
                )
        try:
            set_clause = ', '.join(f'{k} = ?' for k in filtered.keys())
            values = list(filtered.values()) + [area_id]
            conn.execute(f'UPDATE phone_area_codes SET {set_clause} WHERE id = ?', values)
            conn.commit()
            _phone_area_codes_cache.invalidate_prefix('phone_area_codes:')
            return True
        except Exception:
            conn.rollback()
            raise
    finally:
        conn.close()


def delete_phone_area_code(area_id):
    conn = get_db_connection()
    try:
        row = conn.execute('SELECT country_code, sort_order FROM phone_area_codes WHERE id = ?', (area_id,)).fetchone()
        if not row:
            return False
        conn.execute('DELETE FROM phone_area_codes WHERE id = ?', (area_id,))
        conn.execute(
            'UPDATE phone_area_codes SET sort_order = sort_order - 1 WHERE country_code = ? AND sort_order > ?',
            (row['country_code'], row['sort_order'])
        )
        conn.commit()
        _phone_area_codes_cache.invalidate_prefix('phone_area_codes:')
        return True
    finally:
        conn.close()


def get_user_by_email(email):
    conn = get_db_connection()
    try:
        user = conn.execute('SELECT id, username, email, hash, role, is_active FROM users WHERE email = ?', (email,)).fetchone()
        return dict(user) if user else None
    finally:
        conn.close()


def create_password_reset_token(user_id, token, expires_at):
    conn = get_db_connection()
    try:
        conn.execute(
            'INSERT INTO password_reset_tokens (user_id, token, expires_at) VALUES (?, ?, ?)',
            (user_id, token, expires_at)
        )
        conn.commit()
        return True
    except Exception:
        logger.exception('Error al crear token de recuperación')
        return False
    finally:
        conn.close()


def validate_password_reset_token(token):
    conn = get_db_connection()
    try:
        row = conn.execute(
            'SELECT id, user_id, expires_at, used FROM password_reset_tokens WHERE token = ?',
            (token,)
        ).fetchone()
        if not row:
            return None
        if row['used']:
            return None
        from datetime import datetime
        expires = datetime.fromisoformat(row['expires_at'])
        if datetime.utcnow() > expires:
            return None
        return row['user_id']
    finally:
        conn.close()


def mark_password_reset_token_used(token):
    conn = get_db_connection()
    try:
        conn.execute('UPDATE password_reset_tokens SET used = 1 WHERE token = ?', (token,))
        conn.commit()
    finally:
        conn.close()


def update_user_password(user_id, new_hash):
    conn = get_db_connection()
    try:
        conn.execute('UPDATE users SET hash = ? WHERE id = ?', (new_hash, user_id))
        conn.commit()
    finally:
        conn.close()