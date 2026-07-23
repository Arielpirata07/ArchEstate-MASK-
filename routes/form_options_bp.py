from flask import Blueprint, jsonify, request

import models
from decorators import admin_required
from i18n import t, get_language


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
    lang = get_language()
    data = request.get_json()
    if not data or not data.get('category') or not data.get('value') or not data.get('label'):
        return jsonify({'error': t('form.missing_fields', lang)}), 400
    if data['category'] not in models.FORM_OPTION_CATEGORIES:
        return jsonify({'error': t('form.invalid_category', lang)}), 400
    if len(data['value']) > 100:
        return jsonify({'error': t('form.value_too_long', lang)}), 400
    if len(data['label']) > 200:
        return jsonify({'error': t('form.label_too_long', lang)}), 400
    existing = models.get_form_option_by_id_value(data['category'], data['value'])
    if existing:
        return jsonify({'error': t('form.duplicate_value', lang)}), 409
    opt_id = models.create_form_option(data)
    _invalidate_caches()
    return jsonify({'id': opt_id, 'status': 'ok'})


@form_options_bp.route('/api/form-options/<int:option_id>', methods=['PUT'])
@admin_required
def update_option(option_id):
    lang = get_language()
    data = request.get_json()
    if not data:
        return jsonify({'error': t('form.data_required', lang)}), 400
    if 'value' in data and len(data['value']) > 100:
        return jsonify({'error': t('form.value_too_long', lang)}), 400
    if 'label' in data and len(data['label']) > 200:
        return jsonify({'error': t('form.label_too_long', lang)}), 400
    existing = models.get_form_option_by_id(option_id)
    if not existing:
        return jsonify({'error': t('form.not_found', lang)}), 404
    if 'value' in data and data['value'] != existing['value']:
        duplicate = models.get_form_option_by_id_value(existing['category'], data['value'])
        if duplicate:
            return jsonify({'error': t('form.duplicate_value', lang)}), 409
    success = models.update_form_option(option_id, data)
    if not success:
        return jsonify({'error': t('form.update_error', lang)}), 500
    _invalidate_caches()
    return jsonify({'status': 'ok'})


@form_options_bp.route('/api/form-options/<int:option_id>', methods=['DELETE'])
@admin_required
def delete_option(option_id):
    lang = get_language()
    existing = models.get_form_option_by_id(option_id)
    if not existing:
        return jsonify({'error': t('form.not_found', lang)}), 404
    deleted = models.delete_form_option(option_id)
    if not deleted:
        return jsonify({'error': t('form.not_found', lang)}), 404
    _invalidate_caches()
    return jsonify({'status': 'ok'})
