from flask import Blueprint, render_template, request, session, jsonify, redirect, url_for
import json

import models
import decorators
import validators
import utils
import rate_limit
from werkzeug.security import generate_password_hash, check_password_hash


profile_bp = Blueprint('profile', __name__, url_prefix='')


def _log_action(action, target):
    conn = None
    try:
        conn = models.get_db_connection()
        safe_action = utils.safe_text(action)[:100]
        safe_target = utils.safe_text(target)[:200]
        safe_admin = utils.safe_text(session.get('username', 'sistema'))[:50]
        conn.execute('INSERT INTO audit_log (action, target, admin) VALUES (?, ?, ?)',
                     (safe_action, safe_target, safe_admin))
        conn.commit()
    except Exception as e:
        print(f"Error al registrar auditoria: {e}")
    finally:
        if conn:
            conn.close()

ALLOWED_LEAD_EDIT_FIELDS = [
    'zone', 'budget', 'currency', 'phone',
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

    _log_action('Edicion de Lead', f'Lead ID: {lead_id} editado por {session["username"]}')

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

    _log_action('Actualizacion de Perfil', f'Usuario: {session["username"]}')

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

    _log_action('Cambio de Contrasena', f'Usuario: {session["username"]}')

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

    _log_action('Actualizacion Profesional', f'Usuario: {session["username"]}')

    return jsonify({'status': 'success', 'message': 'Perfil profesional actualizado'})
