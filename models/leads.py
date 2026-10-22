import logging

from .base import get_db_connection

logger = logging.getLogger(__name__)


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



def get_user_leads(user_id, limit=200, offset=0):
    try:
        limit = max(1, min(int(limit), 500))
    except (TypeError, ValueError):
        limit = 200
    try:
        offset = max(0, int(offset))
    except (TypeError, ValueError):
        offset = 0
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
            LIMIT ? OFFSET ?
        ''', (user_id, limit, offset)).fetchall()
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



def update_lead_versioned(lead_id, data, user_id, snapshot, summary=''):
    '''Actualiza un lead y registra su versión en UNA sola transacción.

    Evita que la versión persista si el UPDATE falla (y viceversa).
    '''
    filtered = {k: v for k, v in data.items() if k in ALLOWED_LEAD_UPDATE_FIELDS}
    if not filtered:
        return False
    conn = get_db_connection()
    try:
        row = conn.execute(
            'SELECT COALESCE(MAX(version), 0) as max_ver FROM lead_versions WHERE lead_id = ?',
            (lead_id,)
        ).fetchone()
        max_ver = row['max_ver'] if row else 0
        conn.execute(
            'INSERT INTO lead_versions (lead_id, version, data_snapshot, created_by, change_summary) VALUES (?, ?, ?, ?, ?)',
            (lead_id, max_ver + 1, snapshot, user_id, summary)
        )
        set_clause = ', '.join(f'{k} = ?' for k in filtered.keys())
        values = list(filtered.values()) + [lead_id]
        conn.execute(f'UPDATE leads SET {set_clause} WHERE id = ?', values)
        conn.commit()
        return True
    except Exception:
        logger.exception('update_lead_versioned failed for lead_id=%s', lead_id)
        conn.rollback()
        return False
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

