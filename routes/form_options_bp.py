from flask import Blueprint, jsonify, request

import models
from decorators import admin_required


def _invalidate_caches():
    from app_setup import filter_cache
    filter_cache.invalidate()


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
    if len(data['value']) > 100:
        return jsonify({'error': 'El valor no puede superar 100 caracteres'}), 400
    if len(data['label']) > 200:
        return jsonify({'error': 'La etiqueta no puede superar 200 caracteres'}), 400
    existing = models.get_form_option_by_id_value(data['category'], data['value'])
    if existing:
        return jsonify({'error': 'Ya existe una opcion con ese valor en esta categoria'}), 409
    opt_id = models.create_form_option(data)
    _invalidate_caches()
    return jsonify({'id': opt_id, 'status': 'ok'})


@form_options_bp.route('/api/form-options/<int:option_id>', methods=['PUT'])
@admin_required
def update_option(option_id):
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Datos requeridos'}), 400
    if 'value' in data and len(data['value']) > 100:
        return jsonify({'error': 'El valor no puede superar 100 caracteres'}), 400
    if 'label' in data and len(data['label']) > 200:
        return jsonify({'error': 'La etiqueta no puede superar 200 caracteres'}), 400
    existing = models.get_form_option_by_id(option_id)
    if not existing:
        return jsonify({'error': 'No encontrado'}), 404
    if 'value' in data and data['value'] != existing['value']:
        duplicate = models.get_form_option_by_id_value(existing['category'], data['value'])
        if duplicate:
            return jsonify({'error': 'Ya existe una opcion con ese valor en esta categoria'}), 409
    success = models.update_form_option(option_id, data)
    if not success:
        return jsonify({'error': 'Error al actualizar'}), 500
    _invalidate_caches()
    return jsonify({'status': 'ok'})


@form_options_bp.route('/api/form-options/<int:option_id>', methods=['DELETE'])
@admin_required
def delete_option(option_id):
    existing = models.get_form_option_by_id(option_id)
    if not existing:
        return jsonify({'error': 'No encontrado'}), 404
    deleted = models.delete_form_option(option_id)
    if not deleted:
        return jsonify({'error': 'No encontrado'}), 404
    _invalidate_caches()
    return jsonify({'status': 'ok'})
