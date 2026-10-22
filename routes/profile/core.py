# noodle --uses-> services (export,pdf,xlsx)
# noodle --uses-> services (notifications,email)
# noodle --queries-> database (sql,users,leads,professionals,coverage)
# noodle --renders-> templates (html,profile,edit_lead,notifications)
import os
import json
import logging
import time
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
from services.export_helpers import pdf_safe, pdf_val, _style_header_row, _apply_data_border
from i18n import t, get_language
from services.notifications import notify_admins


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


from routes.profile import profile_bp

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
    try:
        limit = int(request.args.get('limit', 200))
    except (TypeError, ValueError):
        limit = 200
    try:
        offset = int(request.args.get('offset', 0))
    except (TypeError, ValueError):
        offset = 0
    leads = models.get_user_leads(user_id, limit=limit, offset=offset)
    for lead in leads:
        if lead.get('timestamp'):
            lead['timestamp'] = utils.convert_to_argentina_time(lead['timestamp'])

    # Fase 3: compromiso de respuesta (mediana de horas habiles hasta el
    # primer contacto) para comunicarle al cliente. Nunca rompe la lista:
    # si falla, se devuelve el compromiso generico (available=False).
    commitment = {'available': False, 'hours': 0, 'sample': 0}
    conn = None
    try:
        from services.sla import get_response_commitment
        conn = models.get_db_connection()
        commitment = get_response_commitment(conn)
    except Exception:
        logger.exception('get_response_commitment fallo')
    finally:
        if conn:
            conn.close()

    return jsonify({'success': True, 'leads': leads, 'sla_commitment': commitment})


@profile_bp.route('/api/profile/lead/<int:lead_id>', methods=['GET'])
@decorators.login_required
def api_get_lead(lead_id):
    lang = get_language()
    user_id = session['user_id']
    lead = models.get_lead_by_id_and_user(lead_id, user_id)
    if not lead:
        return jsonify({'error': t('profile.lead_not_found', lang)}), 404
    if lead.get('timestamp'):
        lead['timestamp'] = utils.convert_to_argentina_time(lead['timestamp'])
    return jsonify({'success': True, 'lead': lead})


@profile_bp.route('/api/profile/lead/<int:lead_id>', methods=['PUT'])
@decorators.login_required
@rate_limit.check_rate_limit(limit=100, window=60)
def api_update_lead(lead_id):
    lang = get_language()
    user_id = session['user_id']
    data = request.json or {}

    lead = models.get_lead_by_id_and_user(lead_id, user_id)
    if not lead:
        return jsonify({'error': t('profile.lead_not_found', lang)}), 404

    allowed = ALLOWED_LEAD_EDIT_FIELDS
    update_data = {k: utils.safe_text(v) for k, v in data.items() if k in allowed}

    if not update_data:
        return jsonify({'error': t('profile.no_valid_data', lang)}), 400

    snapshot = json.dumps({k: str(lead.get(k, '')) for k in allowed})
    if not models.update_lead_versioned(lead_id, update_data, user_id, snapshot):
        return jsonify({'error': t('admin.internal_error_short', lang)}), 500

    utils.log_action('Edicion de Lead', f'Lead ID: {lead_id} editado por {session["username"]}', session)

    return jsonify({'success': True, 'message': t('profile.lead_updated', lang)})


@profile_bp.route('/api/profile/lead/<int:lead_id>/versions', methods=['GET'])
@decorators.login_required
def api_get_lead_versions(lead_id):
    lang = get_language()
    user_id = session['user_id']
    lead = models.get_lead_by_id_and_user(lead_id, user_id)
    if not lead:
        return jsonify({'error': t('profile.lead_not_found', lang)}), 404
    versions = models.get_lead_versions(lead_id)
    for v in versions:
        if v.get('edited_at'):
            v['edited_at'] = utils.convert_to_argentina_time(v['edited_at'])
    return jsonify({'success': True, 'versions': versions})


@profile_bp.route('/api/profile/user', methods=['GET'])
@decorators.login_required
def api_get_user():
    lang = get_language()
    user = models.get_user_profile(session['user_id'])
    if not user:
        return jsonify({'error': t('profile.user_not_found', lang)}), 404
    return jsonify({'success': True, 'user': user})


@profile_bp.route('/api/profile/user', methods=['PUT'])
@decorators.login_required
@rate_limit.check_rate_limit(limit=100, window=60)
def api_update_user():
    lang = get_language()
    user_id = session['user_id']
    data = request.json or {}

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

    if email:
        taken = models.get_user_by_email(email)
        if taken and taken['id'] != user_id:
            return jsonify({'error': t('profile.email_taken', lang)}), 409

    if not models.update_user_account(user_id, email, phone, {
        'first_name': first_name,
        'last_name': last_name,
        'bio': bio,
    }):
        return jsonify({'error': t('admin.internal_error_short', lang)}), 500

    if email:
        session['email'] = email
    if phone:
        session['phone'] = phone

    utils.log_action('Actualizacion de Perfil', f'Usuario: {session["username"]}', session)

    return jsonify({'success': True, 'message': t('profile.updated', lang)})


@profile_bp.route('/api/profile/user/password', methods=['PUT'])
@decorators.login_required
@rate_limit.check_rate_limit(limit=100, window=60)
def api_change_password():
    lang = get_language()
    user_id = session['user_id']
    data = request.json or {}

    current_password = data.get('current_password', '')
    new_password = data.get('new_password', '')

    if not current_password or not new_password:
        return jsonify({'error': t('profile.all_fields_required', lang)}), 400

    user = models.get_user_by_id(user_id)
    if not user or not check_password_hash(user['hash'], current_password):
        return jsonify({'error': t('profile.wrong_password', lang)}), 400

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

    return jsonify({'success': True, 'message': t('profile.password_updated', lang)})


@profile_bp.route('/api/profile/professional', methods=['GET'])
@decorators.professional_required
def api_get_professional():
    lang = get_language()
    user_id = session['user_id']
    pro = models.get_professional_by_user_id(user_id)
    if not pro:
        return jsonify({'error': t('profile.pro_not_found', lang)}), 404
    return jsonify({'success': True, 'professional': pro})


@profile_bp.route('/api/profile/professional', methods=['PUT'])
@decorators.professional_required
@rate_limit.check_rate_limit(limit=100, window=60)
def api_update_professional():
    lang = get_language()
    user_id = session['user_id']
    data = request.json or {}

    ALLOWED_FIELDS = models.ALLOWED_PROFESSIONAL_FIELDS
    update_data = {}
    for field in ALLOWED_FIELDS:
        if field in data:
            update_data[field] = utils.safe_text(data[field]).strip()

    if not update_data:
        return jsonify({'error': t('profile.no_valid_data', lang)}), 400

    models.update_professional_profile(user_id, update_data)

    utils.log_action('Actualizacion Profesional', f'Usuario: {session["username"]}', session)

    return jsonify({'success': True, 'message': t('profile.pro_updated', lang)})


@profile_bp.route('/api/profile/professional/coverage', methods=['GET'])
@decorators.professional_required
def api_get_professional_coverage():
    user_id = session['user_id']
    coverage = models.get_professional_coverage(user_id)
    return jsonify({'success': True, 'coverage': coverage})


@profile_bp.route('/api/profile/professional/coverage', methods=['PUT'])
@decorators.professional_required
@rate_limit.check_rate_limit(limit=30, window=60)
def api_update_professional_coverage():
    lang = get_language()
    user_id = session['user_id']
    data = request.json or {}

    raw_zones = data.get('zones', [])
    raw_specialties = data.get('specialties', [])
    if not isinstance(raw_zones, list) or not isinstance(raw_specialties, list):
        return jsonify({'error': t('profile.no_valid_data', lang)}), 400

    zones = [utils.safe_text(z).strip() for z in raw_zones if isinstance(z, str)]
    specialties = [utils.safe_text(s).strip() for s in raw_specialties if isinstance(s, str)]

    if len(zones) > models.MAX_COVERAGE_VALUES or len(specialties) > models.MAX_COVERAGE_VALUES:
        return jsonify({'error': t('profile.coverage_too_many', lang)}), 400

    result = models.set_professional_coverage(user_id, zones, specialties)
    if result is None:
        return jsonify({'error': t('profile.no_valid_data', lang)}), 500

    utils.log_action('Actualizacion cobertura profesional', f'Usuario: {session["username"]}', session)

    return jsonify({'success': True, 'coverage': result})


@profile_bp.route('/api/profile/professional/coverage', methods=['DELETE'])
@decorators.professional_required
@rate_limit.check_rate_limit(limit=30, window=60)
def api_reset_professional_coverage():
    user_id = session['user_id']
    result = models.set_professional_coverage(user_id, [], [])
    if result is None:
        return jsonify({'error': t('profile.no_valid_data', get_language())}), 500
    utils.log_action('Reinicio cobertura profesional', f'Usuario: {session["username"]}', session)
    return jsonify({'success': True, 'coverage': result})


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
    lang = get_language()
    user_id = session['user_id']
    data = request.json or {}

    allowed = {'theme', 'language', 'email_notifications', 'sms_notifications', 'lead_alerts', 'preferred_channel'}
    update_data = {}

    for key in allowed:
        if key in data:
            update_data[key] = data[key]

    if not update_data:
        return jsonify({'error': t('profile.no_valid_data', lang)}), 400

    if 'theme' in update_data and update_data['theme'] not in ('light', 'dark'):
        return jsonify({'error': t('profile.invalid_theme', lang)}), 400

    if 'language' in update_data and update_data['language'] not in ('es', 'en'):
        return jsonify({'error': t('profile.invalid_language', lang)}), 400

    if 'preferred_channel' in update_data and update_data['preferred_channel'] not in ('sms', 'whatsapp', 'auto'):
        return jsonify({'error': t('profile.invalid_channel', lang)}), 400

    models.update_user_preferences(user_id, update_data)
    utils.log_action('Actualizacion de Preferencias', f'Usuario: {session["username"]}', session)

    return jsonify({'success': True, 'message': t('profile.prefs_updated', lang)})


@profile_bp.route('/api/profile/sessions', methods=['GET'])
@decorators.login_required
def api_get_sessions():
    history = models.get_user_login_history(session['user_id'])
    return jsonify({'success': True, 'sessions': history})


@profile_bp.route('/api/profile/sessions/<int:entry_id>', methods=['DELETE'])
@decorators.login_required
@rate_limit.check_rate_limit(limit=100, window=60)
def api_delete_session(entry_id):
    lang = get_language()
    deleted = models.delete_login_history_entry(entry_id, session['user_id'])
    if not deleted:
        return jsonify({'error': t('profile.session_not_found', lang)}), 404
    utils.log_action('Sesion cerrada', f'Sesion ID: {entry_id}', session)
    return jsonify({'success': True, 'message': t('profile.session_closed', lang)})


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


