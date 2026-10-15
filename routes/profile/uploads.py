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

@profile_bp.route('/api/profile/user/avatar', methods=['POST'])
@decorators.login_required
@rate_limit.check_rate_limit(limit=100, window=60)
def api_upload_avatar():
    lang = get_language()
    user_id = session['user_id']
    if 'avatar' not in request.files:
        return jsonify({'error': t('profile.no_file_sent', lang)}), 400

    file = request.files['avatar']
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

    return jsonify({'success': True, 'avatar_url': url_for('static', filename=avatar_rel) + f'?v={int(time.time())}'})


@profile_bp.route('/api/profile/user/avatar', methods=['DELETE'])
@decorators.login_required
@rate_limit.check_rate_limit(limit=100, window=60)
def api_delete_avatar():
    lang = get_language()
    user_id = session['user_id']
    old_path = models.get_user_avatar_path(user_id)
    if old_path:
        old_file = os.path.join(current_app.config['AVATAR_FOLDER'], os.path.basename(old_path))
        if os.path.exists(old_file):
            os.remove(old_file)
    models.delete_user_avatar(user_id)
    utils.log_action('Avatar eliminado', f'Usuario: {session["username"]}', session)
    return jsonify({'success': True, 'message': t('profile.avatar_deleted', lang)})


# ============================================================
# NUEVOS ENDPOINTS — Perfil Profesional Extendido
# ============================================================


