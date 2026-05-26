import os
import json

from flask import Blueprint, render_template, request, session, jsonify, redirect, url_for, current_app
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

import config
import models
import decorators
import validators
import utils
import rate_limit


profile_bp = Blueprint('profile', __name__, url_prefix='')


ALLOWED_LEAD_EDIT_FIELDS = [
    'zone', 'province', 'budget', 'currency',
    'floor_block', 'usable_m2', 'elevator',
    'land_area', 'built_area', 'pool',
    'architectural_style', 'bedrooms', 'bathrooms',
    'total_area', 'amenities', 'ambientes',
    'parking', 'orientation', 'property_condition',
    'property_age'
]


@profile_bp.route('/mi-perfil')
@decorators.login_required
def profile_view():
    if session.get('role') == 'admin':
        return redirect(url_for('admin_view'))
    user = models.get_user_profile(session['user_id'])
    return render_template('profile.html', user=user)


@profile_bp.route('/mi-perfil/lead/<int:lead_id>/editar')
@decorators.login_required
def edit_lead_view(lead_id):
    user_id = session['user_id']
    lead = models.get_lead_by_id_and_user(lead_id, user_id)
    if not lead:
        return redirect(url_for('profile_view'))
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
@rate_limit.check_rate_limit(limit=10, window=60)
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
@rate_limit.check_rate_limit(limit=10, window=60)
def api_update_user():
    user_id = session['user_id']
    data = request.json

    email = utils.safe_text(data.get('email', '')).strip()
    phone = utils.safe_text(data.get('phone', '')).strip()
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
@rate_limit.check_rate_limit(limit=5, window=60)
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
@rate_limit.check_rate_limit(limit=10, window=60)
def api_update_professional():
    user_id = session['user_id']
    data = request.json

    update_data = {}
    if 'specialty' in data:
        update_data['specialty'] = utils.safe_text(data['specialty']).strip()
    if 'title' in data:
        update_data['title'] = utils.safe_text(data['title']).strip()

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
@rate_limit.check_rate_limit(limit=10, window=60)
def api_update_settings():
    user_id = session['user_id']
    data = request.json

    allowed = {'theme', 'language', 'email_notifications', 'sms_notifications', 'lead_alerts'}
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
@rate_limit.check_rate_limit(limit=5, window=60)
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
@rate_limit.check_rate_limit(limit=5, window=60)
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
@rate_limit.check_rate_limit(limit=5, window=60)
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
@rate_limit.check_rate_limit(limit=10, window=60)
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
@rate_limit.check_rate_limit(limit=5, window=60)
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
@rate_limit.check_rate_limit(limit=5, window=60)
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
