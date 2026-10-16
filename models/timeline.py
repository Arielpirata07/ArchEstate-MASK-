import logging

from .base import get_db_connection

logger = logging.getLogger(__name__)


def get_lead_timeline(lead_id):
    '''Agrega la historia de un lead desde todas las fuentes en eventos crudos.

    Retorna lista de dicts {ts, kind, actor_id, actor_name, data} ordenada
    por ts descendente. Sin i18n: el formateo con t() lo hace la capa de ruta.
    Fuentes: creación, pipeline, tracking, versiones, telemetría y reportes.
    '''
    conn = get_db_connection()
    try:
        lead = conn.execute(
            'SELECT id, timestamp, user_id FROM leads WHERE id = ?', (lead_id,)
        ).fetchone()
        if not lead:
            return []

        events = []
        actor_ids = set()

        events.append({
            'ts': lead['timestamp'] or '', 'kind': 'created',
            'actor_id': lead['user_id'], 'data': {},
        })
        if lead['user_id']:
            actor_ids.add(lead['user_id'])

        for row in conn.execute(
            'SELECT professional_id, from_stage, to_stage, changed_at'
            ' FROM lead_stage_history WHERE lead_id = ? ORDER BY id',
            (lead_id,)
        ).fetchall():
            events.append({
                'ts': row['changed_at'] or '', 'kind': 'stage',
                'actor_id': row['professional_id'],
                'data': {'from': row['from_stage'] or 'new', 'to': row['to_stage']},
            })
            actor_ids.add(row['professional_id'])

        for row in conn.execute(
            'SELECT professional_id, seen, contacted, seen_at, contacted_at'
            ' FROM lead_tracking WHERE lead_id = ?',
            (lead_id,)
        ).fetchall():
            if row['seen']:
                events.append({
                    'ts': row['seen_at'] or '', 'kind': 'seen',
                    'actor_id': row['professional_id'], 'data': {},
                })
            if row['contacted']:
                events.append({
                    'ts': row['contacted_at'] or '', 'kind': 'contacted',
                    'actor_id': row['professional_id'], 'data': {},
                })
            actor_ids.add(row['professional_id'])

        for row in conn.execute(
            'SELECT version, created_by, change_summary, edited_at'
            ' FROM lead_versions WHERE lead_id = ? ORDER BY version',
            (lead_id,)
        ).fetchall():
            events.append({
                'ts': row['edited_at'] or '', 'kind': 'edit',
                'actor_id': row['created_by'],
                'data': {'version': row['version'], 'summary': row['change_summary'] or ''},
            })
            if row['created_by']:
                actor_ids.add(row['created_by'])

        for row in conn.execute(
            'SELECT user_id, event, ts FROM events WHERE lead_id = ? ORDER BY id',
            (lead_id,)
        ).fetchall():
            events.append({
                'ts': row['ts'] or '', 'kind': 'telemetry',
                'actor_id': row['user_id'],
                'data': {'event': row['event']},
            })
            if row['user_id']:
                actor_ids.add(row['user_id'])

        for row in conn.execute(
            'SELECT reported_by, reason, status, created_at'
            ' FROM lead_reports WHERE lead_id = ? ORDER BY id',
            (lead_id,)
        ).fetchall():
            events.append({
                'ts': row['created_at'] or '', 'kind': 'report',
                'actor_id': row['reported_by'],
                'data': {'reason': row['reason'], 'status': row['status']},
            })
            actor_ids.add(row['reported_by'])

        names = {}
        if actor_ids:
            placeholders = ','.join(['?'] * len(actor_ids))
            for row in conn.execute(
                f'SELECT id, username FROM users WHERE id IN ({placeholders})',
                list(actor_ids)
            ).fetchall():
                names[row['id']] = row['username']

        for ev in events:
            ev['actor_name'] = names.get(ev['actor_id'], '')

        events.sort(key=lambda e: e['ts'] or '', reverse=True)
        return events
    finally:
        conn.close()
