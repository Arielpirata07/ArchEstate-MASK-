import os
import json
import logging
from datetime import datetime
from io import BytesIO

from flask import Blueprint, render_template, request, session, jsonify, redirect, url_for, current_app, send_file
from fpdf import FPDF
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

import config
import models
import decorators
import validators
import utils
from utils import parse_budget
import rate_limit


logger = logging.getLogger(__name__)


profile_bp = Blueprint('profile', __name__, url_prefix='')


ALLOWED_LEAD_EDIT_FIELDS = [
    'zone', 'province', 'budget', 'currency',
    'floor_block', 'usable_m2', 'elevator',
    'land_area', 'built_area', 'pool',
    'architectural_style', 'bedrooms', 'bathrooms',
    'total_area', 'amenities', 'ambientes',
    'parking', 'orientation', 'property_condition',
    'property_age', 'community_pool', 'additional_features'
]


@profile_bp.route('/mi-perfil')
@decorators.login_required
def profile_view():
    if session.get('role') == 'admin':
        return redirect(url_for('admin.admin_view'))
    user = models.get_user_profile(session['user_id'])
    return render_template('profile.html', user=user)


@profile_bp.route('/mi-perfil/lead/<int:lead_id>/editar')
@decorators.login_required
def edit_lead_view(lead_id):
    user_id = session['user_id']
    lead = models.get_lead_by_id_and_user(lead_id, user_id)
    if not lead:
        return redirect(url_for('profile.profile_view'))
    versions = models.get_lead_versions(lead_id)
    return render_template('edit_lead.html', lead=lead, versions=versions)


@profile_bp.route('/api/profile/leads', methods=['GET'])
@decorators.login_required
def api_get_user_leads():
    user_id = session['user_id']
    leads = models.get_user_leads(user_id)
    for lead in leads:
        if lead.get('timestamp'):
            lead['timestamp'] = utils.convert_to_argentina_time(lead['timestamp'])
    return jsonify({'success': True, 'leads': leads})


@profile_bp.route('/api/profile/lead/<int:lead_id>', methods=['GET'])
@decorators.login_required
def api_get_lead(lead_id):
    user_id = session['user_id']
    lead = models.get_lead_by_id_and_user(lead_id, user_id)
    if not lead:
        return jsonify({'error': 'Solicitud no encontrada'}), 404
    if lead.get('timestamp'):
        lead['timestamp'] = utils.convert_to_argentina_time(lead['timestamp'])
    return jsonify({'success': True, 'lead': lead})


@profile_bp.route('/api/profile/lead/<int:lead_id>', methods=['PUT'])
@decorators.login_required
@rate_limit.check_rate_limit(limit=100, window=60)
def api_update_lead(lead_id):
    user_id = session['user_id']
    data = request.json

    lead = models.get_lead_by_id_and_user(lead_id, user_id)
    if not lead:
        return jsonify({'error': 'Solicitud no encontrada'}), 404

    allowed = ALLOWED_LEAD_EDIT_FIELDS
    update_data = {k: utils.safe_text(v) for k, v in data.items() if k in allowed}

    if not update_data:
        return jsonify({'error': 'No hay datos validos para actualizar'}), 400

    snapshot = json.dumps({k: str(lead.get(k, '')) for k in allowed})
    max_ver = models.get_lead_max_version(lead_id)
    models.create_lead_version(lead_id, max_ver + 1, snapshot, user_id, '')

    models.update_lead(lead_id, update_data)

    utils.log_action('Edicion de Lead', f'Lead ID: {lead_id} editado por {session["username"]}', session)

    return jsonify({'status': 'success', 'message': 'Solicitud actualizada'})


@profile_bp.route('/api/profile/lead/<int:lead_id>/versions', methods=['GET'])
@decorators.login_required
def api_get_lead_versions(lead_id):
    user_id = session['user_id']
    lead = models.get_lead_by_id_and_user(lead_id, user_id)
    if not lead:
        return jsonify({'error': 'Solicitud no encontrada'}), 404
    versions = models.get_lead_versions(lead_id)
    for v in versions:
        if v.get('edited_at'):
            v['edited_at'] = utils.convert_to_argentina_time(v['edited_at'])
    return jsonify({'success': True, 'versions': versions})


@profile_bp.route('/api/profile/user', methods=['GET'])
@decorators.login_required
def api_get_user():
    user = models.get_user_profile(session['user_id'])
    if not user:
        return jsonify({'error': 'Usuario no encontrado'}), 404
    return jsonify({'success': True, 'user': user})


@profile_bp.route('/api/profile/user', methods=['PUT'])
@decorators.login_required
@rate_limit.check_rate_limit(limit=100, window=60)
def api_update_user():
    user_id = session['user_id']
    data = request.json

    email = utils.safe_text(data.get('email', '')).strip()
    phone = (data.get('phone', '') or '').strip()
    first_name = utils.safe_text(data.get('first_name', '')).strip()
    last_name = utils.safe_text(data.get('last_name', '')).strip()
    bio = utils.safe_text(data.get('bio', '')).strip()

    if email:
        is_valid, error = validators.validate_email(email)
        if not is_valid:
            return jsonify({'error': error}), 400

    if phone:
        is_valid, error = validators.validate_phone(phone)
        if not is_valid:
            return jsonify({'error': error}), 400

    models.update_user_credentials(user_id, email, phone)
    models.update_user_profile(user_id, {
        'first_name': first_name,
        'last_name': last_name,
        'bio': bio,
    })

    session['email'] = email
    session['phone'] = phone

    utils.log_action('Actualizacion de Perfil', f'Usuario: {session["username"]}', session)

    return jsonify({'status': 'success', 'message': 'Perfil actualizado'})


@profile_bp.route('/api/profile/user/password', methods=['PUT'])
@decorators.login_required
@rate_limit.check_rate_limit(limit=100, window=60)
def api_change_password():
    user_id = session['user_id']
    data = request.json

    current_password = data.get('current_password', '')
    new_password = data.get('new_password', '')

    if not current_password or not new_password:
        return jsonify({'error': 'Todos los campos son requeridos'}), 400

    user = models.get_user_by_id(user_id)
    if not user or not check_password_hash(user['hash'], current_password):
        return jsonify({'error': 'La contrasena actual es incorrecta'}), 400

    is_valid, error = validators.validate_password(new_password)
    if not is_valid:
        return jsonify({'error': error}), 400

    conn = models.get_db_connection()
    try:
        conn.execute('UPDATE users SET hash = ? WHERE id = ?',
                     (generate_password_hash(new_password), user_id))
        conn.commit()
    finally:
        conn.close()

    utils.log_action('Cambio de Contrasena', f'Usuario: {session["username"]}', session)

    return jsonify({'status': 'success', 'message': 'Contrasena actualizada'})


@profile_bp.route('/api/profile/professional', methods=['GET'])
@decorators.professional_required
def api_get_professional():
    user_id = session['user_id']
    pro = models.get_professional_by_user_id(user_id)
    if not pro:
        return jsonify({'error': 'Perfil profesional no encontrado'}), 404
    return jsonify({'success': True, 'professional': pro})


@profile_bp.route('/api/profile/professional', methods=['PUT'])
@decorators.professional_required
@rate_limit.check_rate_limit(limit=100, window=60)
def api_update_professional():
    user_id = session['user_id']
    data = request.json

    ALLOWED_FIELDS = {'specialty', 'title', 'province', 'zone'}
    update_data = {}
    for field in ALLOWED_FIELDS:
        if field in data:
            update_data[field] = utils.safe_text(data[field]).strip()

    if not update_data:
        return jsonify({'error': 'No hay datos validos para actualizar'}), 400

    models.update_professional_profile(user_id, update_data)

    utils.log_action('Actualizacion Profesional', f'Usuario: {session["username"]}', session)

    return jsonify({'status': 'success', 'message': 'Perfil profesional actualizado'})


# ============================================================
# NUEVOS ENDPOINTS — Preferencias, Sesiones, Actividad
# ============================================================


@profile_bp.route('/api/profile/settings', methods=['GET'])
@decorators.login_required
def api_get_settings():
    prefs = models.get_user_preferences(session['user_id'])
    return jsonify({'success': True, 'preferences': prefs})


@profile_bp.route('/api/profile/settings', methods=['PUT'])
@decorators.login_required
@rate_limit.check_rate_limit(limit=100, window=60)
def api_update_settings():
    user_id = session['user_id']
    data = request.json

    allowed = {'theme', 'language', 'email_notifications', 'sms_notifications', 'lead_alerts', 'preferred_channel'}
    update_data = {}

    for key in allowed:
        if key in data:
            update_data[key] = data[key]

    if not update_data:
        return jsonify({'error': 'No hay datos validos para actualizar'}), 400

    if 'theme' in update_data and update_data['theme'] not in ('light', 'dark'):
        return jsonify({'error': 'Tema no valido'}), 400

    if 'language' in update_data and update_data['language'] not in ('es', 'en'):
        return jsonify({'error': 'Idioma no valido'}), 400

    if 'preferred_channel' in update_data and update_data['preferred_channel'] not in ('sms', 'whatsapp', 'auto'):
        return jsonify({'error': 'Canal no valido. Usa sms, whatsapp o auto.'}), 400

    models.update_user_preferences(user_id, update_data)
    utils.log_action('Actualizacion de Preferencias', f'Usuario: {session["username"]}', session)

    return jsonify({'status': 'success', 'message': 'Preferencias actualizadas'})


@profile_bp.route('/api/profile/sessions', methods=['GET'])
@decorators.login_required
def api_get_sessions():
    history = models.get_user_login_history(session['user_id'])
    return jsonify({'success': True, 'sessions': history})


@profile_bp.route('/api/profile/sessions/<int:entry_id>', methods=['DELETE'])
@decorators.login_required
@rate_limit.check_rate_limit(limit=100, window=60)
def api_delete_session(entry_id):
    deleted = models.delete_login_history_entry(entry_id, session['user_id'])
    if not deleted:
        return jsonify({'error': 'Sesion no encontrada'}), 404
    utils.log_action('Sesion cerrada', f'Sesion ID: {entry_id}', session)
    return jsonify({'status': 'success', 'message': 'Sesion cerrada'})


@profile_bp.route('/api/profile/activity', methods=['GET'])
@decorators.login_required
def api_get_activity():
    limit = request.args.get('limit', 50, type=int)
    limit = min(limit, 100)
    activity = models.get_user_activity(session['user_id'], limit)
    for entry in activity:
        if entry.get('timestamp'):
            entry['timestamp'] = utils.convert_to_argentina_time(entry['timestamp'])
    return jsonify({'success': True, 'activity': activity})


@profile_bp.route('/api/profile/user/avatar', methods=['POST'])
@decorators.login_required
@rate_limit.check_rate_limit(limit=100, window=60)
def api_upload_avatar():
    user_id = session['user_id']
    if 'avatar' not in request.files:
        return jsonify({'error': 'No se envio ningun archivo'}), 400

    file = request.files['avatar']
    if file.filename == '':
        return jsonify({'error': 'Nombre de archivo vacio'}), 400

    if not utils.allowed_file(file.filename):
        return jsonify({'error': 'Formato no permitido. Usa JPG, PNG, GIF o WebP'}), 400

    mime_valid, detected_ext, mime_error = utils.validate_mime_type(file, file.filename)
    if not mime_valid:
        return jsonify({'error': mime_error}), 400

    file.seek(0, os.SEEK_END)
    size = file.tell()
    if size > config.MAX_UPLOAD_SIZE:
        return jsonify({'error': 'El archivo excede el tamaño maximo de 16MB'}), 400
    file.seek(0)

    ext = detected_ext or 'jpg'
    safe_filename = f'user_{user_id}_avatar.{ext}'
    avatar_dir = current_app.config['AVATAR_FOLDER']
    filepath = os.path.join(avatar_dir, safe_filename)

    # Eliminar avatar anterior si existe
    old_path = models.get_user_avatar_path(user_id)
    if old_path:
        old_file = os.path.join(avatar_dir, os.path.basename(old_path))
        if os.path.exists(old_file):
            os.remove(old_file)

    file.save(filepath)

    avatar_rel = f'uploads/avatars/{safe_filename}'
    models.update_user_avatar(user_id, avatar_rel)
    utils.log_action('Avatar actualizado', f'Usuario: {session["username"]}', session)

    return jsonify({'status': 'success', 'avatar_url': url_for('static', filename=avatar_rel)})


@profile_bp.route('/api/profile/user/avatar', methods=['DELETE'])
@decorators.login_required
@rate_limit.check_rate_limit(limit=100, window=60)
def api_delete_avatar():
    user_id = session['user_id']
    old_path = models.get_user_avatar_path(user_id)
    if old_path:
        old_file = os.path.join(current_app.config['AVATAR_FOLDER'], os.path.basename(old_path))
        if os.path.exists(old_file):
            os.remove(old_file)
    models.delete_user_avatar(user_id)
    utils.log_action('Avatar eliminado', f'Usuario: {session["username"]}', session)
    return jsonify({'status': 'success', 'message': 'Avatar eliminado'})


# ============================================================
# NUEVOS ENDPOINTS — Perfil Profesional Extendido
# ============================================================


@profile_bp.route('/api/profile/professional/full', methods=['GET'])
@decorators.professional_required
def api_get_professional_full():
    user_id = session['user_id']
    pro = models.get_professional_full_profile(user_id)
    if not pro:
        return jsonify({'error': 'Perfil profesional no encontrado'}), 404
    return jsonify({'success': True, 'professional': pro})


@profile_bp.route('/api/profile/professional/full', methods=['PUT'])
@decorators.professional_required
@rate_limit.check_rate_limit(limit=100, window=60)
def api_update_professional_full():
    user_id = session['user_id']
    data = request.json

    allowed = {
        'bio_pro', 'experience_years', 'services_offered',
        'portfolio', 'availability', 'social_links',
        'fee_range_min', 'fee_range_max', 'professional_address'
    }
    update_data = {}
    for key in allowed:
        if key in data:
            val = data[key]
            if isinstance(val, str):
                val = utils.safe_text(val).strip()
            update_data[key] = val

    if not update_data:
        return jsonify({'error': 'No hay datos validos para actualizar'}), 400

    models.create_or_update_professional_profile(user_id, update_data)
    utils.log_action('Perfil profesional actualizado', f'Usuario: {session["username"]}', session)

    return jsonify({'status': 'success', 'message': 'Perfil profesional actualizado'})


@profile_bp.route('/api/profile/professional/photo', methods=['POST'])
@decorators.professional_required
@rate_limit.check_rate_limit(limit=100, window=60)
def api_upload_professional_photo():
    user_id = session['user_id']
    if 'photo' not in request.files:
        return jsonify({'error': 'No se envio ningun archivo'}), 400

    file = request.files['photo']
    if file.filename == '':
        return jsonify({'error': 'Nombre de archivo vacio'}), 400

    if not utils.allowed_file(file.filename):
        return jsonify({'error': 'Formato no permitido. Usa JPG, PNG, GIF o WebP'}), 400

    mime_valid, detected_ext, mime_error = utils.validate_mime_type(file, file.filename)
    if not mime_valid:
        return jsonify({'error': mime_error}), 400

    file.seek(0, os.SEEK_END)
    size = file.tell()
    if size > config.MAX_UPLOAD_SIZE:
        return jsonify({'error': 'El archivo excede el tamaño maximo de 16MB'}), 400
    file.seek(0)

    ext = detected_ext or 'jpg'
    safe_filename = f'pro_{user_id}_photo.{ext}'
    avatar_dir = current_app.config['AVATAR_FOLDER']
    filepath = os.path.join(avatar_dir, safe_filename)

    old_path = models.get_professional_photo_path(user_id)
    if old_path:
        old_file = os.path.join(avatar_dir, os.path.basename(old_path))
        if os.path.exists(old_file):
            os.remove(old_file)

    file.save(filepath)

    photo_rel = f'uploads/avatars/{safe_filename}'
    models.create_or_update_professional_profile(user_id, {'photo_path': photo_rel})
    utils.log_action('Foto profesional actualizada', f'Usuario: {session["username"]}', session)

    return jsonify({'status': 'success', 'photo_url': url_for('static', filename=photo_rel)})


@profile_bp.route('/api/profile/professional/photo', methods=['DELETE'])
@decorators.professional_required
@rate_limit.check_rate_limit(limit=100, window=60)
def api_delete_professional_photo():
    user_id = session['user_id']
    old_path = models.get_professional_photo_path(user_id)
    if old_path:
        old_file = os.path.join(current_app.config['AVATAR_FOLDER'], os.path.basename(old_path))
        if os.path.exists(old_file):
            os.remove(old_file)
    models.create_or_update_professional_profile(user_id, {'photo_path': ''})
    utils.log_action('Foto profesional eliminada', f'Usuario: {session["username"]}', session)
    return jsonify({'status': 'success', 'message': 'Foto eliminada'})


# ============================================================
# NOTIFICACIONES
# ============================================================


@profile_bp.route('/api/profile/notifications')
@decorators.login_required
def profile_notifications():
    user_id = session['user_id']
    notifications = models.get_user_notifications(user_id)
    unread = models.get_unread_notification_count(user_id)
    return jsonify({
        'success': True,
        'notifications': notifications,
        'unread': unread,
    })


@profile_bp.route('/api/profile/notifications/read', methods=['POST'])
@decorators.login_required
def mark_notification_read():
    user_id = session['user_id']
    data = request.json or {}
    nid = data.get('notification_id')
    if not nid:
        return jsonify({'success': False, 'error': 'notification_id requerido'}), 400
    ok = models.mark_notification_read(nid, user_id)
    return jsonify({'success': ok})


@profile_bp.route('/api/profile/notifications/read-all', methods=['POST'])
@decorators.login_required
def mark_all_notifications_read():
    user_id = session['user_id']
    models.mark_all_notifications_read(user_id)
    return jsonify({'success': True})


@profile_bp.route('/api/profile/notification-filters', methods=['PUT'])
@decorators.professional_required
def update_notification_filters():
    user_id = session['user_id']
    data = request.json or {}
    filters = {
        'types': data.get('types', []),
        'property_types': data.get('property_types', []),
    }
    # Validate types against form_options
    valid_types = set(models.get_form_options_by_category('operation_type'))
    valid_prop_types = set(models.get_form_options_by_category('property_type'))
    filters['types'] = [t for t in filters['types'] if t in valid_types]
    filters['property_types'] = [pt for pt in filters['property_types'] if pt in valid_prop_types]
    # Budget range
    budget_min = data.get('budget_min')
    budget_max = data.get('budget_max')
    updates = {'notification_filters': json.dumps(filters, ensure_ascii=False)}
    if budget_min is not None:
        updates['budget_min'] = max(0, float(budget_min))
    if budget_max is not None:
        updates['budget_max'] = max(0, float(budget_max))
    ok = models.update_user_preferences(user_id, updates)
    if ok:
        return jsonify({'success': True, 'filters': filters, 'budget_min': updates.get('budget_min', 0), 'budget_max': updates.get('budget_max', 0)})
    return jsonify({'success': False, 'error': 'Error al guardar'}), 500


@profile_bp.route('/api/profile/notification-filters', methods=['GET'])
@decorators.login_required
def get_notification_filters():
    user_id = session['user_id']
    prefs = models.get_user_preferences(user_id)
    raw = prefs.get('notification_filters', '')
    filters = {}
    if raw:
        try:
            filters = json.loads(raw) if isinstance(raw, str) else raw
        except (json.JSONDecodeError, TypeError):
            filters = {}
    return jsonify({
        'success': True,
        'filters': filters,
        'budget_min': prefs.get('budget_min', 0),
        'budget_max': prefs.get('budget_max', 0),
    })


@profile_bp.route('/api/profile/notification-channel', methods=['PUT'])
@decorators.login_required
def update_notification_channel():
    user_id = session['user_id']
    data = request.json or {}
    channel = data.get('channel', '').strip().lower()
    valid_channels = {'email', 'whatsapp', 'ambos', 'auto'}
    if channel not in valid_channels:
        return jsonify({'success': False, 'error': 'Canal inválido'}), 400
    ok = models.update_user_preferences(user_id, {'preferred_channel': channel})
    if ok:
        return jsonify({'success': True, 'channel': channel})
    return jsonify({'success': False, 'error': 'Error al guardar'}), 500


@profile_bp.route('/api/profile/notification-channel', methods=['GET'])
@decorators.login_required
def get_notification_channel():
    user_id = session['user_id']
    prefs = models.get_user_preferences(user_id)
    return jsonify({
        'success': True,
        'channel': prefs.get('preferred_channel', 'email'),
        'whatsapp_notifications': prefs.get('whatsapp_notifications', 1),
    })


# ============================================================
# EXPORTACIÓN DE REPORTES
# ============================================================


def _query_monthly_contacts(user_id):
    """Retorna leads contactados en los últimos 30 días para un profesional."""
    conn = None
    try:
        conn = models.get_db_connection()
        rows = conn.execute('''
            SELECT l.id, l.type, l.property_type, l.zone, l.province,
                   l.budget, l.currency, l.timestamp,
                   lt.seen, lt.contacted, lt.seen_at, lt.contacted_at
            FROM leads l
            JOIN lead_tracking lt ON l.id = lt.lead_id
            WHERE lt.professional_id = ?
              AND lt.seen = 1
              AND lt.contacted = 1
              AND lt.contacted_at >= datetime('now', '-30 days')
            ORDER BY lt.contacted_at DESC
            LIMIT 1000
        ''', (user_id,)).fetchall()
        return [dict(r) for r in rows]
    finally:
        if conn:
            conn.close()



def _build_export_stats(leads):
    """Construye stats a partir de la lista de leads."""
    total = len(leads)
    budgets = []
    zones = {}
    currencies = {}
    types = {}
    budget_by_currency = {}
    for lead in leads:
        b = parse_budget(lead.get('budget'))
        budgets.append(b)
        z = lead.get('zone') or 'Sin zona'
        zones[z] = zones.get(z, 0) + 1
        c = lead.get('currency') or 'ARG'
        currencies[c] = currencies.get(c, 0) + 1
        t = lead.get('type') or 'Otro'
        types[t] = types.get(t, 0) + 1
        by_curr = budget_by_currency.setdefault(c, {'count': 0, 'total': 0.0})
        by_curr['count'] += 1
        by_curr['total'] += b
    avg_budget = round(sum(budgets) / total, 2) if total else 0
    total_budget = sum(budgets)
    sorted_zones = sorted(zones.items(), key=lambda x: x[1], reverse=True)
    return {
        'total': total,
        'avg_budget': avg_budget,
        'total_budget': total_budget,
        'zones': sorted_zones,
        'currencies': currencies,
        'types': types,
        'zone_count': len(zones),
        'budget_by_currency': budget_by_currency,
    }


def pdf_safe(value):
    """Sanitize a value for PDF output (Latin-1 safe)."""
    if value is None:
        return ''
    text = str(value)
    replacements = {
        '\u20ac': 'EUR', '\u00a3': 'GBP', '\u00a5': 'JPY',
        '\u2014': '-', '\u2013': '-', '\u2022': '-',
        '\u2122': 'TM', '\u00a9': '(c)', '\u00ae': '(R)',
        '\u2026': '...', '\u00b2': '2', '\u00b3': '3', '\u00b0': 'deg',
        '\u221a': 'sqrt', '\u00d7': 'x', '\u00f7': '/',
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    accents = {
        '\u00e1': 'a', '\u00e9': 'e', '\u00ed': 'i', '\u00f3': 'o', '\u00fa': 'u',
        '\u00e0': 'a', '\u00e8': 'e', '\u00ec': 'i', '\u00f2': 'o', '\u00f9': 'u',
        '\u00e4': 'a', '\u00eb': 'e', '\u00ef': 'i', '\u00f6': 'o', '\u00fc': 'u',
        '\u00e3': 'a', '\u00f5': 'o', '\u00f1': 'n',
        '\u00c1': 'A', '\u00c9': 'E', '\u00cd': 'I', '\u00d3': 'O', '\u00da': 'U',
        '\u00c0': 'A', '\u00c8': 'E', '\u00cc': 'I', '\u00d2': 'O', '\u00d9': 'U',
        '\u00c4': 'A', '\u00cb': 'E', '\u00cf': 'I', '\u00d6': 'O', '\u00dc': 'U',
        '\u00c3': 'A', '\u00d5': 'O', '\u00d1': 'N',
        '\u00e7': 'c', '\u00c7': 'C', '\u00df': 'ss',
    }
    for old, new in accents.items():
        text = text.replace(old, new)
    return ''.join(c if ord(c) < 128 else '?' for c in text)


def pdf_val(value, default='-'):
    text = pdf_safe(value)
    return text if text else default


def _style_header_row(ws, col_count):
    """Apply ArchEstate header style to the first row of a worksheet."""
    header_font = Font(name='Manrope', bold=True, size=10, color='FFFFFF')
    header_fill = PatternFill(start_color='000410', end_color='000410', fill_type='solid')
    header_align = Alignment(horizontal='center', vertical='center')
    thin_border = Border(
        left=Side(style='thin', color='D4BC9A'),
        right=Side(style='thin', color='D4BC9A'),
        top=Side(style='thin', color='D4BC9A'),
        bottom=Side(style='thin', color='D4BC9A'),
    )
    for col in range(1, col_count + 1):
        cell = ws.cell(row=1, column=col)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = header_align
        cell.border = thin_border


def _apply_data_border(ws, row, col_count):
    """Apply subtle borders to a data row."""
    border = Border(
        left=Side(style='thin', color='E8D5B7'),
        right=Side(style='thin', color='E8D5B7'),
        top=Side(style='thin', color='E8D5B7'),
        bottom=Side(style='thin', color='E8D5B7'),
    )
    for col in range(1, col_count + 1):
        ws.cell(row=row, column=col).border = border


@profile_bp.route('/api/profile/professional/export/xlsx')
@decorators.professional_required
def profile_export_history_xlsx():
    try:
        user_id = session['user_id']
        leads = _query_monthly_contacts(user_id)
        stats = _build_export_stats(leads)

        wb = Workbook()
        data_font = Font(name='Manrope', size=10, color='000410')
        label_font = Font(name='Manrope', size=10, bold=True, color='735A3A')

        # ─── Sheet 1: Resumen ───
        ws_resumen = wb.active
        ws_resumen.title = 'Resumen'
        resumen_data = [
            ['Total Leads Contactados', stats['total']],
            ['Presupuesto Promedio', f"${stats['avg_budget']:,.2f}"],
            ['Presupuesto Total', f"${stats['total_budget']:,.2f}"],
            ['Zonas Diferentes', stats['zone_count']],
        ]
        for col, h in enumerate(['Métrica', 'Valor'], 1):
            ws_resumen.cell(row=1, column=col, value=h)
        _style_header_row(ws_resumen, 2)
        ws_resumen.column_dimensions['A'].width = 32
        ws_resumen.column_dimensions['B'].width = 22
        for row_idx, row_data in enumerate(resumen_data, 2):
            ws_resumen.cell(row=row_idx, column=1, value=row_data[0]).font = label_font
            ws_resumen.cell(row=row_idx, column=2, value=row_data[1]).font = data_font
            ws_resumen.cell(row=row_idx, column=2).alignment = Alignment(horizontal='center')
            _apply_data_border(ws_resumen, row_idx, 2)

        note_row = len(resumen_data) + 3
        ws_resumen.cell(row=note_row, column=1,
            value='Generado por ArchEstate · The Private Ledger'
        ).font = Font(name='Manrope', size=8, italic=True, color='A68A64')

        # ─── Sheet 2: Leads ───
        ws_leads = wb.create_sheet('Leads')
        headers = ['ID', 'Tipo', 'Propiedad', 'Zona', 'Provincia', 'Presupuesto',
                   'Moneda', 'Creado', 'Visto', 'Contactado']
        for col, h in enumerate(headers, 1):
            ws_leads.cell(row=1, column=col, value=h)
        _style_header_row(ws_leads, len(headers))
        col_widths = [8, 22, 16, 20, 18, 14, 10, 18, 18, 18]
        for i, w in enumerate(col_widths, 1):
            ws_leads.column_dimensions[get_column_letter(i)].width = w
        ws_leads.auto_filter.ref = f'A1:J{len(leads) + 1}'
        for row_idx, lead in enumerate(leads, 2):
            vals = [
                lead['id'], lead['type'], lead['property_type'], lead['zone'],
                lead.get('province', ''), lead['budget'], lead['currency'],
                lead.get('timestamp', ''), lead.get('seen_at', ''), lead.get('contacted_at', ''),
            ]
            for col, val in enumerate(vals, 1):
                cell = ws_leads.cell(row=row_idx, column=col, value=val)
                cell.font = data_font
                cell.alignment = Alignment(horizontal='center', vertical='center')
            _apply_data_border(ws_leads, row_idx, len(headers))

        # ─── Sheet 3: Por Zona ───
        ws_zones = wb.create_sheet('Por Zona')
        for col, h in enumerate(['Zona', 'Cantidad', '% del Total'], 1):
            ws_zones.cell(row=1, column=col, value=h)
        _style_header_row(ws_zones, 3)
        ws_zones.column_dimensions['A'].width = 30
        ws_zones.column_dimensions['B'].width = 14
        ws_zones.column_dimensions['C'].width = 14
        ws_zones.auto_filter.ref = f'A1:C{len(stats["zones"]) + 1}'
        for row_idx, (zone, count) in enumerate(stats['zones'], 2):
            pct = round(count / stats['total'] * 100, 1) if stats['total'] else 0
            ws_zones.cell(row=row_idx, column=1, value=zone).font = label_font
            ws_zones.cell(row=row_idx, column=2, value=count).font = data_font
            ws_zones.cell(row=row_idx, column=2).alignment = Alignment(horizontal='center')
            ws_zones.cell(row=row_idx, column=3, value=f'{pct}%').font = data_font
            ws_zones.cell(row=row_idx, column=3).alignment = Alignment(horizontal='center')
            _apply_data_border(ws_zones, row_idx, 3)

        # ─── Sheet 4: Inversiones ───
        ws_inv = wb.create_sheet('Inversiones')
        for col, h in enumerate(['Moneda', 'Cantidad', 'Presupuesto Total', 'Presupuesto Promedio'], 1):
            ws_inv.cell(row=1, column=col, value=h)
        _style_header_row(ws_inv, 4)
        ws_inv.column_dimensions['A'].width = 16
        ws_inv.column_dimensions['B'].width = 14
        ws_inv.column_dimensions['C'].width = 22
        ws_inv.column_dimensions['D'].width = 24
        ws_inv.auto_filter.ref = f'A1:D{len(stats["currencies"]) + 1}'
        row_idx = 2
        for currency, count in sorted(stats['currencies'].items()):
            bc = stats['budget_by_currency'].get(currency, {'count': 0, 'total': 0.0})
            total_c = bc['total']
            avg_c = round(total_c / bc['count'], 2) if bc['count'] else 0
            ws_inv.cell(row=row_idx, column=1, value=currency).font = label_font
            ws_inv.cell(row=row_idx, column=2, value=count).font = data_font
            ws_inv.cell(row=row_idx, column=2).alignment = Alignment(horizontal='center')
            ws_inv.cell(row=row_idx, column=3, value=f"${total_c:,.2f}").font = data_font
            ws_inv.cell(row=row_idx, column=3).alignment = Alignment(horizontal='center')
            ws_inv.cell(row=row_idx, column=4, value=f"${avg_c:,.2f}").font = data_font
            ws_inv.cell(row=row_idx, column=4).alignment = Alignment(horizontal='center')
            _apply_data_border(ws_inv, row_idx, 4)
            row_idx += 1

        buffer = BytesIO()
        wb.save(buffer)
        buffer.seek(0)

        now_str = datetime.now().strftime('%Y%m%d_%H%M')
        return send_file(
            buffer,
            as_attachment=True,
            download_name=f'reporte_rendimiento_{now_str}.xlsx',
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        )
    except Exception:
        logger.exception('Error exporting XLSX report')
        return jsonify({'error': 'Error al generar el reporte XLSX'}), 500


@profile_bp.route('/api/profile/professional/export/pdf')
@decorators.professional_required
def profile_export_history_pdf():
    try:
        user_id = session['user_id']
        leads = _query_monthly_contacts(user_id)
        stats = _build_export_stats(leads)

        # Fetch professional name
        conn = models.get_db_connection()
        pro = conn.execute(
            'SELECT name FROM professionals WHERE user_id = ?', (user_id,)
        ).fetchone()
        prof_name = pdf_safe(pro['name']) if pro else 'Profesional'
        conn.close()

        midnight = (0, 4, 16)
        gold = (115, 90, 58)
        gold_light = (166, 138, 100)
        gray_bg = (245, 243, 240)
        white = (255, 255, 255)

        class ReportPDF(FPDF):
            def header(self):
                if self.page_no() == 1:
                    return
                self.set_fill_color(*midnight)
                self.rect(0, 0, 210, 10, 'F')
                self.set_font('Helvetica', 'B', 7)
                self.set_text_color(*gold_light)
                self.set_y(2)
                self.cell(0, 6, 'ArchEstate - Reporte de Rendimiento', ln=True, align='C')
                self.ln(4)

            def footer(self):
                self.set_y(-12)
                self.set_font('Helvetica', 'I', 7)
                self.set_text_color(150, 150, 150)
                self.cell(0, 8, f'Pagina {self.page_no()}/{{nb}}  |  {datetime.now().strftime("%d/%m/%Y %H:%M")}', ln=True, align='C')

        pdf = ReportPDF()
        pdf.alias_nb_pages()
        pdf.set_auto_page_break(auto=True, margin=18)

        # ─── PAGE 1 — Brand Header ───
        pdf.add_page()
        pdf.set_fill_color(*midnight)
        pdf.rect(0, 0, 210, 28, 'F')

        pdf.set_y(4)
        pdf.set_font('Times', 'BI', 18)
        pdf.set_text_color(*gold_light)
        pdf.cell(0, 10, 'ArchEstate', ln=True, align='C')
        pdf.set_font('Helvetica', '', 7)
        pdf.set_text_color(166, 138, 100)
        pdf.cell(0, 5, 'The Private Ledger', ln=True, align='C')

        pdf.set_y(24)
        pdf.set_draw_color(*gold)
        pdf.set_line_width(0.5)
        pdf.line(20, 28, 190, 28)

        # ─── Professional info ───
        pdf.set_y(32)
        pdf.set_font('Helvetica', 'B', 10)
        pdf.set_text_color(*midnight)
        pdf.cell(0, 6, pdf_safe(prof_name), ln=True, align='L')
        pdf.set_font('Helvetica', '', 8)
        pdf.set_text_color(100, 100, 100)
        pdf.cell(0, 5, 'Leads contactados en los ultimos 30 dias', ln=True, align='L')
        pdf.ln(6)

        # ─── Summary cards (2x2) ───
        card_w = 82
        card_h = 18
        gap = 6
        left_margin = 14
        pdf.set_font('Helvetica', '', 9)

        cards = [
            ('Total Leads', str(stats['total']), f"{stats['zone_count']} zonas activas"),
            ('Presupuesto Total', f"${stats['total_budget']:,.2f}", f"Promedio ${stats['avg_budget']:,.2f}"),
        ]
        pdf.set_x(left_margin)
        for title, value, sub in cards:
            x0 = pdf.get_x()
            y0 = pdf.get_y()
            pdf.set_fill_color(*gold)
            pdf.rect(x0, y0, 4, card_h, 'F')
            pdf.set_fill_color(*gray_bg)
            pdf.rect(x0 + 4, y0, card_w - 4, card_h, 'F')
            pdf.set_text_color(*midnight)
            pdf.set_xy(x0 + 8, y0 + 2)
            pdf.set_font('Helvetica', '', 7)
            pdf.cell(card_w - 12, 4, pdf_safe(title))
            pdf.set_xy(x0 + 8, y0 + 6)
            pdf.set_font('Helvetica', 'B', 13)
            pdf.cell(card_w - 12, 7, pdf_safe(value))
            pdf.set_xy(x0 + 8, y0 + 13)
            pdf.set_font('Helvetica', 'I', 7)
            pdf.set_text_color(100, 100, 100)
            pdf.cell(card_w - 12, 4, pdf_safe(sub))
            pdf.set_x(x0 + card_w + gap)

        pdf.ln(card_h + 4)
        pdf.set_text_color(*midnight)

        pdf.set_x(left_margin)
        cards2 = [
            ('Promedio / Lead', f"${stats['avg_budget']:,.2f}", 'Valor estimado promedio'),
            ('Monedas activas', str(len(stats['currencies'])), f"{', '.join(sorted(stats['currencies'].keys()))}"),
        ]
        for title, value, sub in cards2:
            x0 = pdf.get_x()
            y0 = pdf.get_y()
            pdf.set_fill_color(*gold)
            pdf.rect(x0, y0, 4, card_h, 'F')
            pdf.set_fill_color(*gray_bg)
            pdf.rect(x0 + 4, y0, card_w - 4, card_h, 'F')
            pdf.set_text_color(*midnight)
            pdf.set_xy(x0 + 8, y0 + 2)
            pdf.set_font('Helvetica', '', 7)
            pdf.cell(card_w - 12, 4, pdf_safe(title))
            pdf.set_xy(x0 + 8, y0 + 6)
            pdf.set_font('Helvetica', 'B', 13)
            pdf.cell(card_w - 12, 7, pdf_safe(value))
            pdf.set_xy(x0 + 8, y0 + 13)
            pdf.set_font('Helvetica', 'I', 7)
            pdf.set_text_color(100, 100, 100)
            pdf.cell(card_w - 12, 4, pdf_safe(sub))
            pdf.set_x(x0 + card_w + gap)

        pdf.ln(card_h + 8)

        # ─── Currency breakdown ───
        def section_header(title):
            pdf.set_fill_color(*gold)
            pdf.set_text_color(*white)
            pdf.set_font('Helvetica', 'B', 10)
            pdf.cell(0, 7, pdf_safe('  ' + title.upper()), ln=True, fill=True)
            pdf.set_text_color(*midnight)
            pdf.set_font('Helvetica', '', 9)
            pdf.ln(2)

        section_header('Distribucion por Moneda')
        pdf.set_font('Helvetica', 'B', 8)
        pdf.set_fill_color(*gray_bg)
        cw = [30, 30, 50, 50, 30]
        ch = ['Moneda', 'Cantidad', 'Presupuesto Total', 'Presupuesto Promedio', '%']
        for i, (h, w) in enumerate(zip(ch, cw)):
            pdf.cell(w, 6, pdf_safe(h), border=1, align='C', fill=True)
        pdf.ln()
        pdf.set_font('Helvetica', '', 8)
        for currency, count in sorted(stats['currencies'].items()):
            bc = stats['budget_by_currency'].get(currency, {'count': 0, 'total': 0.0})
            total_c = bc['total']
            avg_c = round(total_c / bc['count'], 2) if bc['count'] else 0
            pct = round(count / stats['total'] * 100, 1) if stats['total'] else 0
            vals = [currency, str(count), f"${total_c:,.2f}", f"${avg_c:,.2f}", f"{pct}%"]
            for v, w in zip(vals, cw):
                pdf.cell(w, 5, pdf_safe(v), border=1, align='C')
            pdf.ln()
        pdf.ln(5)

        # ─── Property type breakdown ───
        section_header('Distribucion por Tipo de Propiedad')
        pdf.set_font('Helvetica', 'B', 8)
        pdf.set_fill_color(*gray_bg)
        cw2 = [80, 40, 40, 30]
        ch2 = ['Tipo', 'Cantidad', '% del Total', 'Prom. Presupuesto']
        for h, w in zip(ch2, cw2):
            pdf.cell(w, 6, pdf_safe(h), border=1, align='C', fill=True)
        pdf.ln()
        pdf.set_font('Helvetica', '', 8)

        # Compute per-type budgets
        type_budgets = {}
        for lead in leads:
            t = lead.get('type') or 'Otro'
            b = parse_budget(lead.get('budget'))
            tb = type_budgets.setdefault(t, {'count': 0, 'total': 0.0})
            tb['count'] += 1
            tb['total'] += b
        for t, count in sorted(stats['types'].items(), key=lambda x: x[1], reverse=True):
            tb = type_budgets.get(t, {'count': 0, 'total': 0.0})
            avg_t = round(tb['total'] / tb['count'], 2) if tb['count'] else 0
            pct = round(count / stats['total'] * 100, 1) if stats['total'] else 0
            vals = [pdf_safe(t)[:35], str(count), f"{pct}%", f"${avg_t:,.2f}"]
            for v, w in zip(vals, cw2):
                pdf.cell(w, 5, pdf_safe(v), border=1, align='C')
            pdf.ln()
        pdf.ln(5)

        # ─── Zone breakdown ───
        section_header('Zonas con Mayor Captacion')
        pdf.set_font('Helvetica', 'B', 8)
        pdf.set_fill_color(*gray_bg)
        cw3 = [90, 40, 40, 22]
        ch3 = ['Zona', 'Cantidad', '% del Total', 'Bar']
        for h, w in zip(ch3, cw3):
            pdf.cell(w, 6, pdf_safe(h), border=1, align='C', fill=True)
        pdf.ln()
        pdf.set_font('Helvetica', '', 8)
        max_count = max((c for _, c in stats['zones']), default=1)
        for zone, count in stats['zones'][:10]:
            pct = round(count / stats['total'] * 100, 1) if stats['total'] else 0
            vals = [pdf_safe(zone)[:40], str(count), f"{pct}%"]
            for v, w in zip(vals, cw3[:3]):
                pdf.cell(w, 5, pdf_safe(v), border=1, align='C')
            # Mini bar
            bar_ratio = count / max_count
            bar_w = int(bar_ratio * 18)
            x0 = pdf.get_x()
            y0 = pdf.get_y()
            pdf.set_fill_color(*gold_light)
            pdf.rect(x0, y0 + 1, bar_w, 3, 'F')
            pdf.cell(cw3[3], 5, '', border=1)
            pdf.ln()
        pdf.ln(5)

        # ─── Leads detail table ───
        section_header('Detalle de Leads (ultimos 30)')
        pdf.set_font('Helvetica', 'B', 7)
        pdf.set_fill_color(*midnight)
        pdf.set_text_color(*white)
        cols_l = [8, 8, 32, 26, 24, 22, 28, 22]
        headers_l = ['#', 'ID', 'Tipo', 'Zona', 'Presupuesto', 'Moneda', 'Provincia', 'Contactado']
        for h, w in zip(headers_l, cols_l):
            pdf.cell(w, 6, pdf_safe(h), border=1, align='C', fill=True)
        pdf.ln()
        pdf.set_text_color(*midnight)
        pdf.set_font('Helvetica', '', 7)
        for idx, lead in enumerate(leads[:30], 1):
            contact_date = lead.get('contacted_at', '')[:10] if lead.get('contacted_at') else ''
            budget = pdf_val(lead['budget'])
            vals = [
                str(idx), str(lead['id']), pdf_safe(lead['type'])[:28],
                pdf_safe(lead['zone'])[:22],
                budget[:20], pdf_safe(lead.get('currency', ''))[:8],
                pdf_safe(lead.get('province', ''))[:24],
                contact_date[:20],
            ]
            if idx % 2 == 0:
                pdf.set_fill_color(*gray_bg)
                fill = True
            else:
                fill = False
            for v, w in zip(vals, cols_l):
                pdf.cell(w, 5, pdf_safe(v), border=1, align='C', fill=fill)
            pdf.ln()
            if pdf.get_y() > 258:
                pdf.add_page()

        pdf.ln(5)
        pdf.set_font('Helvetica', 'I', 7)
        pdf.set_text_color(*gold_light)
        gen_date = datetime.now().strftime('%d/%m/%Y %H:%M')
        pdf.cell(0, 5, f'Generado por ArchEstate . The Private Ledger | {gen_date}', ln=True, align='C')

        pdf_output = pdf.output(dest='S')
        if isinstance(pdf_output, str):
            pdf_output = pdf_output.encode('latin-1')

        buffer = BytesIO(pdf_output)
        buffer.seek(0)

        now_str = datetime.now().strftime('%Y%m%d_%H%M')
        return send_file(
            buffer,
            as_attachment=True,
            download_name=f'reporte_rendimiento_{now_str}.pdf',
            mimetype='application/pdf',
        )
    except Exception:
        logger.exception('Error exporting PDF report')
        return jsonify({'error': 'Error al generar el reporte PDF'}), 500
