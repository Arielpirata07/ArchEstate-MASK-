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

@profile_bp.route('/notificaciones')
@decorators.login_required
def notifications_view():
    lang = get_language()
    return render_template('notifications.html')


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
        'current_user_id': user_id,
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


@profile_bp.route('/api/profile/notifications/all')
@decorators.login_required
def all_notifications():
    user_id = session['user_id']
    page = request.args.get('page', 1, type=int)
    result = models.get_all_user_notifications(user_id, page=page)
    unread = models.get_unread_notification_count(user_id)
    return jsonify({
        'success': True,
        'notifications': result['items'],
        'total': result['total'],
        'page': result['page'],
        'pages': result['pages'],
        'unread': unread,
        'current_user_id': user_id,
    })


@profile_bp.route('/api/profile/notifications/delete-read', methods=['POST'])
@decorators.login_required
def delete_read_notifications():
    user_id = session['user_id']
    count = models.delete_read_notifications(user_id)
    lang = get_language()
    return jsonify({
        'success': True,
        'deleted': count,
        'message': t('notif.read_deleted', lang),
    })


@profile_bp.route('/api/profile/notifications/<int:notification_id>', methods=['DELETE'])
@decorators.login_required
def delete_notification(notification_id):
    user_id = session['user_id']
    ok = models.delete_notification(notification_id, user_id)
    return jsonify({'success': ok})


@profile_bp.route('/api/profile/notification-filters', methods=['PUT'])
@decorators.professional_required
def update_notification_filters():
    lang = get_language()
    user_id = session['user_id']
    data = request.json or {}
    filters = {
        'types': data.get('types', []),
        'property_types': data.get('property_types', []),
    }
    # Validate types against form_options
    valid_types = set(models.get_form_options_by_category('operation_type'))
    valid_prop_types = set(models.get_form_options_by_category('property_type'))
    filters['types'] = [ft for ft in filters['types'] if ft in valid_types]
    filters['property_types'] = [pt for pt in filters['property_types'] if pt in valid_prop_types]
    # Budget range
    budget_min = data.get('budget_min')
    budget_max = data.get('budget_max')
    updates = {'notification_filters': json.dumps(filters, ensure_ascii=False)}
    if budget_min is not None:
        try:
            updates['budget_min'] = max(0, float(budget_min))
        except (ValueError, TypeError):
            return jsonify({'success': False, 'error': t('profile.invalid_budget_range', lang)}), 400
    if budget_max is not None:
        try:
            updates['budget_max'] = max(0, float(budget_max))
        except (ValueError, TypeError):
            return jsonify({'success': False, 'error': t('profile.invalid_budget_range', lang)}), 400
    ok = models.update_user_preferences(user_id, updates)
    if ok:
        return jsonify({'success': True, 'filters': filters, 'budget_min': updates.get('budget_min', 0), 'budget_max': updates.get('budget_max', 0)})
    return jsonify({'success': False, 'error': t('profile.save_error', lang)}), 500


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
    lang = get_language()
    user_id = session['user_id']
    data = request.json or {}
    channel = data.get('channel', '').strip().lower()
    valid_channels = {'email', 'whatsapp', 'ambos', 'auto'}
    if channel not in valid_channels:
        return jsonify({'success': False, 'error': t('profile.invalid_channel', lang)}), 400
    ok = models.update_user_preferences(user_id, {'preferred_channel': channel})
    if ok:
        return jsonify({'success': True, 'channel': channel})
    return jsonify({'success': False, 'error': t('profile.save_error', lang)}), 500


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


@profile_bp.route('/api/profile/contact-admin', methods=['POST'])
@decorators.login_required
def contact_admin():
    lang = get_language()
    data = request.json or {}
    subject = (data.get('subject') or '').strip()
    message = (data.get('message') or '').strip()

    if not subject or not message:
        return jsonify({"success": False, "error": t('profile.contact_admin_required', lang)}), 400

    user = models.get_user_by_id(session['user_id'])
    username = user['username'] if user else 'Desconocido'

    title = t('profile.admin_msg_title', lang, user=username, subject=subject)
    body = t('profile.admin_msg_body', lang, message=message)

    notified = notify_admins(title=title, body=body)
    utils.log_action('Contacto admin desde perfil', f'{username}: {subject}', session)
    return jsonify({"success": True, "message": t('profile.contact_admin_sent', lang)})


# ============================================================
# EXPORTACIÓN DE REPORTES
# ============================================================


