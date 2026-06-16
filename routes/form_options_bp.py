from flask import Blueprint, jsonify, request

import models
from decorators import admin_required

form_options_bp = Blueprint('form_options', __name__)


@form_options_bp.route('/api/form-options', methods=['GET'])
def list_options():
    category = request.args.get('category')
    options = models.get_form_options(category=category, active_only=True)
    grouped = {}
    for opt in options:
        grouped.setdefault(opt['category'], []).append(opt)
    return jsonify({'options': grouped})


@form_options_bp.route('/api/form-options/all', methods=['GET'])
@admin_required
def list_all_options():
    options = models.get_form_options(active_only=False)
    return jsonify({'options': [dict(o) for o in options]})


@form_options_bp.route('/api/form-options', methods=['POST'])
@admin_required
def create_option():
    data = request.get_json()
    if not data or not data.get('category') or not data.get('value') or not data.get('label'):
        return jsonify({'error': 'Faltan campos requeridos'}), 400
    if data['category'] not in models.FORM_OPTION_CATEGORIES:
        return jsonify({'error': 'Categoria invalida'}), 400
    existing = models.get_form_option_by_id_value(data['category'], data['value'])
    if existing:
        return jsonify({'error': 'Ya existe una opcion con ese valor en esta categoria'}), 409
    opt_id = models.create_form_option(data)
    return jsonify({'id': opt_id, 'status': 'ok'})


@form_options_bp.route('/api/form-options/<int:option_id>', methods=['PUT'])
@admin_required
def update_option(option_id):
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Datos requeridos'}), 400
    existing = models.get_form_option_by_id(option_id)
    if not existing:
        return jsonify({'error': 'No encontrado'}), 404
    success = models.update_form_option(option_id, data)
    if not success:
        return jsonify({'error': 'Error al actualizar'}), 500
    return jsonify({'status': 'ok'})


@form_options_bp.route('/api/form-options/<int:option_id>', methods=['DELETE'])
@admin_required
def delete_option(option_id):
    existing = models.get_form_option_by_id(option_id)
    if not existing:
        return jsonify({'error': 'No encontrado'}), 404
    models.delete_form_option(option_id)
    return jsonify({'status': 'ok'})
