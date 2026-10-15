import logging

from .base import get_db_connection

logger = logging.getLogger(__name__)


CALENDAR_EVENT_TYPES = ['visit', 'call', 'followup', 'meeting', 'other']


CALENDAR_EVENT_COLORS = {
    'visit': 'gold',
    'call': 'emerald',
    'followup': 'blue',
    'meeting': 'violet',
    'other': 'midnight',
}



def get_calendar_events(professional_id, start_date=None, end_date=None):
    '''Eventos del profesional en un rango de fechas (YYYY-MM-DD). Sin rango: todos.'''
    conn = get_db_connection()
    try:
        query = 'SELECT * FROM calendar_events WHERE professional_id = ?'
        params = [professional_id]
        if start_date:
            query += ' AND event_date >= ?'
            params.append(start_date)
        if end_date:
            query += ' AND event_date <= ?'
            params.append(end_date)
        query += ' ORDER BY event_date, start_time, id'
        return [dict(r) for r in conn.execute(query, params).fetchall()]
    finally:
        conn.close()



def get_calendar_event(professional_id, event_id):
    '''Un evento solo si pertenece al profesional.'''
    conn = get_db_connection()
    try:
        row = conn.execute(
            'SELECT * FROM calendar_events WHERE id = ? AND professional_id = ?',
            (event_id, professional_id)
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()



def create_calendar_event(professional_id, title, event_date, event_type='visit', **kwargs):
    '''Crea un evento. lead_id se valida (debe existir) solo si se pasa.'''
    if event_type not in CALENDAR_EVENT_TYPES:
        return None
    lead_id = kwargs.get('lead_id')
    conn = get_db_connection()
    try:
        if lead_id is not None:
            lead = conn.execute('SELECT id FROM leads WHERE id = ?', (lead_id,)).fetchone()
            if not lead:
                return None
        cursor = conn.execute(
            '''INSERT INTO calendar_events
               (professional_id, lead_id, title, description, event_date, start_time,
                end_time, event_type, location, color, all_day, completed)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)''',
            (professional_id, lead_id, title, kwargs.get('description', ''),
             event_date, kwargs.get('start_time', ''), kwargs.get('end_time', ''),
             event_type, kwargs.get('location', ''),
             kwargs.get('color') or CALENDAR_EVENT_COLORS[event_type],
             1 if kwargs.get('all_day') else 0)
        )
        conn.commit()
        return cursor.lastrowid
    except Exception:
        logger.exception('create_calendar_event failed for pro=%s', professional_id)
        conn.rollback()
        return None
    finally:
        conn.close()



def update_calendar_event(professional_id, event_id, data):
    '''Actualiza campos permitidos de un evento propio. Devuelve True/False.'''
    allowed = {'title', 'description', 'event_date', 'start_time', 'end_time',
               'event_type', 'location', 'color', 'all_day', 'lead_id'}
    filtered = {k: v for k, v in data.items() if k in allowed}
    if not filtered:
        return False
    if 'event_type' in filtered and filtered['event_type'] not in CALENDAR_EVENT_TYPES:
        return False
    conn = get_db_connection()
    try:
        existing = conn.execute(
            'SELECT id FROM calendar_events WHERE id = ? AND professional_id = ?',
            (event_id, professional_id)
        ).fetchone()
        if not existing:
            return False
        if 'lead_id' in filtered and filtered['lead_id'] is not None:
            lead = conn.execute('SELECT id FROM leads WHERE id = ?', (filtered['lead_id'],)).fetchone()
            if not lead:
                return False
        if 'all_day' in filtered:
            filtered['all_day'] = 1 if filtered['all_day'] else 0
        if 'event_type' in filtered:
            filtered['color'] = CALENDAR_EVENT_COLORS[filtered['event_type']]
        from datetime import datetime as _dt
        filtered['updated_at'] = _dt.now().strftime('%Y-%m-%d %H:%M:%S')
        set_clause = ', '.join(f'{k} = ?' for k in filtered.keys())
        values = list(filtered.values()) + [event_id, professional_id]
        conn.execute(
            f'UPDATE calendar_events SET {set_clause} WHERE id = ? AND professional_id = ?',
            values
        )
        conn.commit()
        return True
    except Exception:
        logger.exception('update_calendar_event failed for event=%s', event_id)
        conn.rollback()
        return False
    finally:
        conn.close()



def delete_calendar_event(professional_id, event_id):
    conn = get_db_connection()
    try:
        cur = conn.execute(
            'DELETE FROM calendar_events WHERE id = ? AND professional_id = ?',
            (event_id, professional_id)
        )
        conn.commit()
        return cur.rowcount > 0
    except Exception:
        logger.exception('delete_calendar_event failed for event=%s', event_id)
        conn.rollback()
        return False
    finally:
        conn.close()



def complete_calendar_event(professional_id, event_id, completed=True):
    conn = get_db_connection()
    try:
        from datetime import datetime as _dt
        now = _dt.now().strftime('%Y-%m-%d %H:%M:%S')
        cur = conn.execute(
            'UPDATE calendar_events SET completed = ?, updated_at = ? WHERE id = ? AND professional_id = ?',
            (1 if completed else 0, now, event_id, professional_id)
        )
        conn.commit()
        return cur.rowcount > 0
    except Exception:
        logger.exception('complete_calendar_event failed for event=%s', event_id)
        conn.rollback()
        return False
    finally:
        conn.close()



def get_upcoming_events(professional_id, days=7, limit=20):
    '''Próximos eventos no completados desde hoy.'''
    from datetime import date as _date, timedelta as _td
    today = _date.today().isoformat()
    end = (_date.today() + _td(days=days)).isoformat()
    conn = get_db_connection()
    try:
        rows = conn.execute(
            '''SELECT * FROM calendar_events
               WHERE professional_id = ? AND completed = 0 AND event_date >= ? AND event_date <= ?
               ORDER BY event_date, start_time, id LIMIT ?''',
            (professional_id, today, end, limit)
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()



