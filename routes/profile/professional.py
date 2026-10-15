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

@profile_bp.route('/api/profile/professional/full', methods=['GET'])
@decorators.professional_required
def api_get_professional_full():
    lang = get_language()
    user_id = session['user_id']
    pro = models.get_professional_full_profile(user_id)
    if not pro:
        return jsonify({'error': t('profile.pro_not_found', lang)}), 404
    return jsonify({'success': True, 'professional': pro})


@profile_bp.route('/api/profile/professional/full', methods=['PUT'])
@decorators.professional_required
@rate_limit.check_rate_limit(limit=100, window=60)
def api_update_professional_full():
    lang = get_language()
    user_id = session['user_id']
    data = request.json or {}

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
        return jsonify({'error': t('profile.no_valid_data', lang)}), 400
    models.create_or_update_professional_profile(user_id, update_data)

    geo_fields = {}
    for key in ('province', 'zone', 'country'):
        if key in data:
            geo_fields[key] = utils.safe_text(data[key]).strip()
    if geo_fields:
        models.update_professional_profile(user_id, geo_fields)

    utils.log_action('Perfil profesional actualizado', f'Usuario: {session["username"]}', session)

    return jsonify({'success': True, 'message': t('profile.pro_updated', lang)})


@profile_bp.route('/api/profile/professional/photo', methods=['POST'])
@decorators.professional_required
@rate_limit.check_rate_limit(limit=100, window=60)
def api_upload_professional_photo():
    lang = get_language()
    user_id = session['user_id']
    if 'photo' not in request.files:
        return jsonify({'error': t('profile.no_file_sent', lang)}), 400

    file = request.files['photo']
    if file.filename == '':
        return jsonify({'error': t('profile.empty_filename', lang)}), 400

    if not utils.allowed_file(file.filename):
        return jsonify({'error': t('profile.invalid_format', lang)}), 400

    mime_valid, detected_ext, mime_error = utils.validate_mime_type(file, file.filename)
    if not mime_valid:
        return jsonify({'error': mime_error}), 400

    file.seek(0, os.SEEK_END)
    size = file.tell()
    if size > config.MAX_UPLOAD_SIZE:
        return jsonify({'error': t('profile.file_too_large', lang)}), 400
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

    return jsonify({'success': True, 'photo_url': url_for('static', filename=photo_rel) + f'?v={int(time.time())}'})


@profile_bp.route('/api/profile/professional/photo', methods=['DELETE'])
@decorators.professional_required
@rate_limit.check_rate_limit(limit=100, window=60)
def api_delete_professional_photo():
    lang = get_language()
    user_id = session['user_id']
    old_path = models.get_professional_photo_path(user_id)
    if old_path:
        old_file = os.path.join(current_app.config['AVATAR_FOLDER'], os.path.basename(old_path))
        if os.path.exists(old_file):
            os.remove(old_file)
    models.create_or_update_professional_profile(user_id, {'photo_path': ''})
    utils.log_action('Foto profesional eliminada', f'Usuario: {session["username"]}', session)
    return jsonify({'success': True, 'message': t('profile.photo_deleted', lang)})


# ============================================================
# NOTIFICACIONES
# ============================================================


