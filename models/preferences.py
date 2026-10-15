import logging

from .base import _prefs_cache, get_db_connection

logger = logging.getLogger(__name__)


ALLOWED_PREFERENCES_FIELDS = {
    'theme', 'language', 'email_notifications', 'sms_notifications',
    'lead_alerts', 'preferred_channel', 'whatsapp_notifications',
    'notification_filters', 'budget_min', 'budget_max',
}



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



