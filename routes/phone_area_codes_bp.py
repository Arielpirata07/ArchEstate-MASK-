from flask import Blueprint, jsonify, request

import models
from decorators import admin_required
from i18n import t, get_language


def _invalidate_caches():
    from app_setup import filter_cache
    filter_cache.invalidate()


phone_area_codes_bp = Blueprint('phone_area_codes', __name__)


@phone_area_codes_bp.route('/api/phone-area-codes', methods=['GET'])
def list_area_codes():
    country_code = request.args.get('country_code')
    codes = models.get_phone_area_codes(country_code=country_code, active_only=True)
    grouped = {}
    for c in codes:
        grouped.setdefault(c['country_code'], []).append(c)
    return jsonify({'codes': grouped})


@phone_area_codes_bp.route('/api/phone-area-codes/all', methods=['GET'])
@admin_required
def list_all_area_codes():
    codes = models.get_phone_area_codes(active_only=False)
    return jsonify({'codes': [dict(c) for c in codes]})


@phone_area_codes_bp.route('/api/phone-area-codes', methods=['POST'])
@admin_required
def create_area_code():
    lang = get_language()
    data = request.get_json()
    if not data or not data.get('code') or not data.get('city'):
        return jsonify({'error': t('form.missing_fields', lang)}), 400
    if len(data['code']) > 10:
        return jsonify({'error': t('pac.code_too_long', lang)}), 400
    if len(data['city']) > 200:
        return jsonify({'error': t('pac.city_too_long', lang)}), 400
    cc = data.get('country_code', '+54')
    existing = models.get_phone_area_code_by_code_country(data['code'], cc)
    if existing:
        return jsonify({'error': t('pac.duplicate_code', lang)}), 409
    area_id = models.create_phone_area_code(data)
    _invalidate_caches()
    return jsonify({'id': area_id, 'status': 'ok'})


@phone_area_codes_bp.route('/api/phone-area-codes/<int:area_id>', methods=['PUT'])
@admin_required
def update_area_code(area_id):
    lang = get_language()
    data = request.get_json()
    if not data:
        return jsonify({'error': t('form.data_required', lang)}), 400
    if 'code' in data and len(data['code']) > 10:
        return jsonify({'error': t('pac.code_too_long', lang)}), 400
    if 'city' in data and len(data['city']) > 200:
        return jsonify({'error': t('pac.city_too_long', lang)}), 400
    existing = models.get_phone_area_code_by_id(area_id)
    if not existing:
        return jsonify({'error': t('form.not_found', lang)}), 404
    if 'code' in data and data['code'] != existing['code']:
        cc = data.get('country_code', existing['country_code'])
        duplicate = models.get_phone_area_code_by_code_country(data['code'], cc)
        if duplicate:
            return jsonify({'error': t('pac.duplicate_code', lang)}), 409
    success = models.update_phone_area_code(area_id, data)
    if not success:
        return jsonify({'error': t('form.update_error', lang)}), 500
    _invalidate_caches()
    return jsonify({'status': 'ok'})


@phone_area_codes_bp.route('/api/phone-area-codes/<int:area_id>', methods=['DELETE'])
@admin_required
def delete_area_code(area_id):
    lang = get_language()
    existing = models.get_phone_area_code_by_id(area_id)
    if not existing:
        return jsonify({'error': t('form.not_found', lang)}), 404
    deleted = models.delete_phone_area_code(area_id)
    if not deleted:
        return jsonify({'error': t('form.not_found', lang)}), 404
    _invalidate_caches()
    return jsonify({'status': 'ok'})
