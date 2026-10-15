import logging

from .base import SimpleTTLCache, _form_options_cache, get_db_connection

logger = logging.getLogger(__name__)


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



