# noodle --uses-> services (whatsapp,sms)
# noodle --queries-> database (sql,leads)
"""
Blueprint para endpoints relacionados con leads: revelación server-side de
contacto WhatsApp/SMS, telemetría de eventos, y reporte de teléfonos inválidos.
"""

import logging
import urllib.parse

logger = logging.getLogger(__name__)

from flask import Blueprint, redirect, request, session, jsonify, current_app

import rate_limit
import utils
from decorators import professional_required
from i18n import t, get_language
from models import get_db_connection


lead_bp = Blueprint('lead', __name__, url_prefix='/api/lead')


_WA_PER_HOUR = 60
_REVEAL_PER_HOUR = 60
_RATE_WINDOW = 3600


def _check_rate(key, limit, window=_RATE_WINDOW):
    return rate_limit.check_rate(key, limit, window)


@lead_bp.route('/<int:lead_id>/r/whatsapp')
@professional_required
def redirect_whatsapp(lead_id):
    """
    Redirección server-side a wa.me. Genera el link con el E.164 y el mensaje
    personalizado, registra en audit_log (con hash, no número completo) y emite
    302. Rate-limit: 60/h por profesional, 60/h por IP.
    """
    user_id = session.get('user_id')
    lang = get_language()
    if not _check_rate(f'wa:{user_id}', _WA_PER_HOUR):
        utils.log_event(user_id=user_id, lead_id=lead_id, event='wa_rate_limited')
        return jsonify({"success": False, "error": t('lead.wa_rate_limited', lang)}), 429
    ip = request.headers.get('X-Forwarded-For', request.remote_addr or '').split(',')[0].strip()
    if not _check_rate(f'wa:ip:{ip}', _WA_PER_HOUR):
        utils.log_event(user_id=user_id, lead_id=lead_id, event='wa_rate_limited', props={'by': 'ip'})
        return jsonify({"success": False, "error": t('lead.wa_rate_limited_short', lang)}), 429

    conn = None
    try:
        conn = get_db_connection()
        user = conn.execute('SELECT username FROM users WHERE id = ?', (user_id,)).fetchone()
        if not user:
            return jsonify({"success": False, "error": t('lead.access_denied', lang)}), 403

        pro_status = conn.execute(
            'SELECT status FROM professionals WHERE name = ?', (user['username'],)
        ).fetchone()
        if not pro_status or pro_status['status'] != 'approved':
            return jsonify({"success": False, "error": t('lead.account_pending', lang)}), 403

        lead = conn.execute(
            'SELECT id, phone, type, zone, property_type FROM leads WHERE id = ?',
            (lead_id,)
        ).fetchone()
        if not lead:
            return jsonify({"success": False, "error": t('lead.not_found', lang)}), 404

        phone_e164 = utils.normalize_phone_to_e164(lead['phone'] or '')
        if not phone_e164:
            utils.log_event(user_id=user_id, lead_id=lead_id, event='wa_invalid_number',
                            props={'reason': 'no_e164'}, conn=conn)
            return jsonify({"success": False, "error": t('lead.wa_invalid_phone', lang)}), 422

        if not utils.is_whatsapp_capable(phone_e164):
            utils.log_event(user_id=user_id, lead_id=lead_id, event='wa_fallback_sms',
                            props={'reason': 'not_mobile'}, conn=conn)
            return jsonify({"success": False, "error": t('lead.wa_not_mobile', lang)}), 422

        wa_url = utils.build_whatsapp_url(
            phone_e164,
            pro_name=user['username'],
            operation=lead['type'],
            zone=lead['zone'],
            lead_id=lead_id,
        )
        if not wa_url:
            return jsonify({"success": False, "error": t('lead.wa_build_error', lang)}), 422

        try:
            u = urllib.parse.urlparse(wa_url)
            q = urllib.parse.parse_qs(u.query)
            q['utm_source'] = ['archestate']
            q['utm_medium'] = ['lead']
            q['utm_campaign'] = [f'lead_{lead_id}']
            new_q = urllib.parse.urlencode({k: v[0] for k, v in q.items()}, quote_via=urllib.parse.quote_plus)
            wa_url = f"{u.scheme}://{u.netloc}{u.path}?{new_q}"
        except Exception:
            logger.debug('UTM enrich falló, se usa URL base')

        utils.log_action(
            "WhatsApp link generated",
            f"lead_id={lead_id} phone_hash={utils.hash_phone_digits(phone_e164)}",
            session,
            conn=conn
        )
        utils.log_event(
            user_id=user_id, lead_id=lead_id, event='wa_link_generated',
            props={'phone_hash': utils.hash_phone_digits(phone_e164), 'channel': 'whatsapp'},
            ip=ip,
            conn=conn
        )
        try:
            from services.sla import record_first_contact
            record_first_contact(lead_id, user_id, 'wa_link')
        except Exception:
            logger.warning('record_first_contact (wa_link) fallo para lead=%s', lead_id)

        return redirect(wa_url, code=302)
    finally:
        if conn:
            conn.close()


@lead_bp.route('/<int:lead_id>/phone', methods=['GET'])
@professional_required
def reveal_phone(lead_id):
    """
    Devuelve el teléfono (en formato E.164) al profesional, con fines de fallback
    o copy-paste manual. Audita la consulta con hash.
    """
    user_id = session.get('user_id')
    lang = get_language()
    if not _check_rate(f'reveal:{user_id}', _REVEAL_PER_HOUR):
        return jsonify({"success": False, "error": t('lead.reveal_rate_limited', lang)}), 429

    conn = None
    try:
        conn = get_db_connection()
        user = conn.execute('SELECT username FROM users WHERE id = ?', (user_id,)).fetchone()
        if not user:
            return jsonify({"success": False, "error": t('lead.access_denied', lang)}), 403

        pro_status = conn.execute(
            'SELECT status FROM professionals WHERE name = ?', (user['username'],)
        ).fetchone()
        if not pro_status or pro_status['status'] != 'approved':
            return jsonify({"success": False, "error": t('lead.account_pending', lang)}), 403

        lead = conn.execute('SELECT phone, type FROM leads WHERE id = ?', (lead_id,)).fetchone()
        if not lead:
            return jsonify({"success": False, "error": t('lead.not_found', lang)}), 404

        phone_to_return = lead['phone'] or ''
        utils.log_action(
            "Consulta Telefono",
            f"Lead ID: {lead_id} ({lead['type']}) phone_hash={utils.hash_phone_digits(phone_to_return or '')}",
            session,
            conn=conn
        )
        utils.log_event(
            user_id=user_id, lead_id=lead_id, event='phone_revealed',
            props={'phone_hash': utils.hash_phone_digits(phone_to_return or '')},
            conn=conn
        )
        try:
            from services.sla import record_first_contact
            record_first_contact(lead_id, user_id, 'reveal')
        except Exception:
            logger.warning('record_first_contact (reveal) fallo para lead=%s', lead_id)
        return jsonify({"success": True, "phone": phone_to_return})
    finally:
        if conn:
            conn.close()


@lead_bp.route('/<int:lead_id>/whatsapp-event', methods=['POST'])
@professional_required
@rate_limit.check_rate_limit(limit=100, window=60)
def whatsapp_event(lead_id):
    """
    Endpoint de telemetría: registra clicks/éxitos/fallos del botón WhatsApp
    o del flujo SMS. No es auth-pesado: sólo profesionales autenticados.
    """
    user_id = session.get('user_id')
    lang = get_language()
    data = request.get_json(silent=True) or {}
    event = (data.get('event') or '').strip().lower()
    props = data.get('props') or {}

    if event not in {
        'wa_button_clicked', 'wa_window_opened', 'wa_popup_blocked',
        'wa_invalid_number', 'sms_button_clicked', 'sms_window_opened',
        'sms_fallback_used', 'tel_clicked', 'phone_button_clicked'
    }:
        return jsonify({"success": False, "error": t('lead.unknown_event', lang)}), 400

    ip = request.headers.get('X-Forwarded-For', request.remote_addr or '').split(',')[0].strip()
    utils.log_event(
        user_id=user_id, lead_id=lead_id, event=event,
        props=props if isinstance(props, dict) else {}, ip=ip
    )

    # SLA: senales de intencion de contacto (click en llamar / SMS).
    sla_source = {
        'tel_clicked': 'call',
        'phone_button_clicked': 'call',
        'sms_button_clicked': 'sms',
        'sms_fallback_used': 'sms',
    }.get(event)
    if sla_source:
        try:
            from services.sla import record_first_contact
            record_first_contact(lead_id, user_id, sla_source)
        except Exception:
            logger.warning('record_first_contact (%s) fallo para lead=%s', sla_source, lead_id)

    return jsonify({"success": True})
