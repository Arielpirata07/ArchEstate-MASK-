import logging

from flask import jsonify, session
from markupsafe import escape

import models
from decorators import professional_required
from i18n import t, get_language
from utils import convert_to_argentina_time

logger = logging.getLogger(__name__)

from routes.professional import professional_bp
from routes.professional.helpers import _get_approved_professional


# Telemetría conocida → key i18n; lo desconocido se muestra tal cual (escaped).
_TELEMETRY_LABELS = {
    'wa_link_generated': 'timeline.event_wa',
    'wa_button_clicked': 'timeline.event_wa_click',
    'phone_revealed': 'timeline.event_phone',
    'sms_button_clicked': 'timeline.event_sms',
    'otp_sent': 'timeline.event_otp',
    'otp_verified': 'timeline.event_verified',
}


def build_timeline(lead_id, lang):
    """Agrega + formatea la historia de un lead para mostrar.

    Retorna (entries, error_response): entries es lista de
    {ts, kind, actor, label, detail} con strings ya escapados/traducidos.
    """
    raw = models.get_lead_timeline(lead_id)
    entries = []
    for ev in raw:
        kind = ev['kind']
        actor = ev.get('actor_name') or t('timeline.unknown_actor', lang)
        data = ev.get('data') or {}
        if kind == 'created':
            label, detail = t('timeline.created', lang), ''
        elif kind == 'stage':
            label = t('timeline.stage_move', lang, **{
                'from': escape(data.get('from', '')),
                'to': escape(data.get('to', '')),
            })
            detail = ''
        elif kind == 'seen':
            label, detail = t('timeline.seen', lang), ''
        elif kind == 'contacted':
            label, detail = t('timeline.contacted', lang), ''
        elif kind == 'edit':
            label = t('timeline.edit', lang, version=data.get('version', ''))
            detail = escape(data.get('summary', ''))
        elif kind == 'telemetry':
            key = _TELEMETRY_LABELS.get(data.get('event', ''), '')
            label = t(key, lang) if key else escape(data.get('event', ''))
            detail = ''
        elif kind == 'report':
            label = t('timeline.report', lang, status=escape(data.get('status', '')))
            detail = escape(data.get('reason', ''))
        else:
            label, detail = escape(kind), ''
        entries.append({
            'ts': convert_to_argentina_time(ev.get('ts') or ''),
            'kind': kind,
            'actor': escape(actor),
            'label': label,
            'detail': detail,
        })
    return entries


@professional_bp.route('/api/leads/<int:lead_id>/timeline')
@professional_required
def lead_timeline_api(lead_id):
    lang = get_language()
    conn = None
    try:
        conn = models.get_db_connection()
        _, error = _get_approved_professional(conn, session['user_id'], lang)
        if error:
            return error
        if not conn.execute('SELECT id FROM leads WHERE id = ?', (lead_id,)).fetchone():
            return jsonify({'success': False, 'error': t('prof.lead_not_found', lang)}), 404
        return jsonify({'success': True, 'lead_id': lead_id, 'timeline': build_timeline(lead_id, lang)})
    except Exception:
        logger.exception('Error en lead_timeline_api')
        return jsonify({'success': False, 'error': t('prof.internal_error_short', lang)}), 500
    finally:
        if conn:
            conn.close()
