"""
Blueprint para endpoints relacionados con leads: revelación server-side de
contacto WhatsApp/SMS, telemetría de eventos, y reporte de teléfonos inválidos.
"""

import json
import os
import tempfile
import threading
import time
import urllib.parse

from flask import Blueprint, redirect, request, session, jsonify, current_app

import utils
from decorators import professional_required
from i18n import t, get_language
from models import get_db_connection


lead_bp = Blueprint('lead', __name__, url_prefix='/api/lead')


_WA_PER_HOUR = 60
_REVEAL_PER_HOUR = 60

_rate_lock = threading.Lock()
_rate_file = os.path.join(tempfile.gettempdir(), 'archestate_lead_rate_limits.json')


def _load_rate_store():
    try:
        with open(_rate_file, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _save_rate_store(store):
    dir_name = os.path.dirname(_rate_file)
    fd, tmp_path = tempfile.mkstemp(dir=dir_name, suffix='.json')
    try:
        with os.fdopen(fd, 'w') as f:
            json.dump(store, f)
        os.replace(tmp_path, _rate_file)
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass


def _check_rate(key, limit, window=3600):
    now = time.time()
    with _rate_lock:
        store = _load_rate_store()
        bucket = store.get(key, [])
        bucket = [t for t in bucket if now - t < window]
        if len(bucket) >= limit:
            _save_rate_store(store)
            return False
        bucket.append(now)
        store[key] = bucket
        _save_rate_store(store)
        return True


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
            pass

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
        return jsonify({"success": True, "phone": phone_to_return})
    finally:
        if conn:
            conn.close()


@lead_bp.route('/<int:lead_id>/whatsapp-event', methods=['POST'])
@professional_required
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
    return jsonify({"success": True})
