import logging

from flask import Blueprint, jsonify, request

import models
import utils
from decorators import admin_required
from i18n import t, get_language

logger = logging.getLogger(__name__)

organizations_bp = Blueprint('organizations', __name__, url_prefix='')


@organizations_bp.route('/api/admin/organizations')
@admin_required
def list_organizations():
    lang = get_language()
    try:
        orgs = models.get_organizations()
        return jsonify({'success': True, 'organizations': orgs})
    except Exception:
        logger.exception('Error listing organizations')
        return jsonify({'success': False, 'error': t('admin.internal_error_short', lang)}), 500


@organizations_bp.route('/api/admin/organizations', methods=['POST'])
@admin_required
def create_org():
    lang = get_language()
    data = request.json or {}
    name = (data.get('name') or '').strip()
    description = (data.get('description') or '').strip()

    if not name:
        return jsonify({'success': False, 'error': t('org.name_required', lang)}), 400

    try:
        org_id = models.create_organization(name, description)
        utils.log_action('Organizacion Creada', f'Org: {name} (ID: {org_id})', request)
        return jsonify({'success': True, 'id': org_id, 'message': t('org.created', lang)})
    except Exception:
        logger.exception('Error creating organization')
        return jsonify({'success': False, 'error': t('admin.internal_error_short', lang)}), 500


@organizations_bp.route('/api/admin/organizations/<int:org_id>', methods=['PUT'])
@admin_required
def update_org(org_id):
    lang = get_language()
    data = request.json or {}

    org = models.get_organization_by_id(org_id)
    if not org:
        return jsonify({'success': False, 'error': t('org.not_found', lang)}), 404

    try:
        models.update_organization(org_id, data)
        utils.log_action('Organizacion Actualizada', f'Org ID: {org_id}', request)
        return jsonify({'success': True, 'message': t('org.updated', lang)})
    except Exception:
        logger.exception('Error updating organization')
        return jsonify({'success': False, 'error': t('admin.internal_error_short', lang)}), 500


@organizations_bp.route('/api/admin/organizations/<int:org_id>/deactivate', methods=['POST'])
@admin_required
def deactivate_org(org_id):
    lang = get_language()

    org = models.get_organization_by_id(org_id)
    if not org:
        return jsonify({'success': False, 'error': t('org.not_found', lang)}), 404

    try:
        models.deactivate_organization(org_id)
        utils.log_action('Organizacion Desactivada', f'Org: {org["name"]} (ID: {org_id})', request)
        return jsonify({'success': True, 'message': t('org.deactivated', lang)})
    except Exception:
        logger.exception('Error deactivating organization')
        return jsonify({'success': False, 'error': t('admin.internal_error_short', lang)}), 500


@organizations_bp.route('/api/admin/organizations/<int:org_id>', methods=['DELETE'])
@admin_required
def delete_org(org_id):
    lang = get_language()

    org = models.get_organization_by_id(org_id)
    if not org:
        return jsonify({'success': False, 'error': t('org.not_found', lang)}), 404

    try:
        models.delete_organization(org_id)
        utils.log_action('Organizacion Eliminada', f'Org: {org["name"]} (ID: {org_id})', request)
        return jsonify({'success': True, 'message': t('org.deleted', lang)})
    except Exception:
        logger.exception('Error deleting organization')
        return jsonify({'success': False, 'error': t('admin.internal_error_short', lang)}), 500


@organizations_bp.route('/api/admin/professionals/<int:user_id>/organization', methods=['PUT'])
@admin_required
def set_pro_org(user_id):
    lang = get_language()
    data = request.json or {}
    org_id = data.get('org_id')

    if org_id is not None:
        try:
            org_id = int(org_id)
        except (ValueError, TypeError):
            return jsonify({'success': False, 'error': t('org.invalid_org', lang)}), 400

    try:
        success = models.set_professional_organization(user_id, org_id)
        if not success:
            return jsonify({'success': False, 'error': t('org.invalid_org', lang)}), 400
        return jsonify({'success': True, 'message': t('org.pro_assigned', lang)})
    except Exception:
        logger.exception('Error setting professional organization')
        return jsonify({'success': False, 'error': t('admin.internal_error_short', lang)}), 500


@organizations_bp.route('/api/admin/leads/<int:lead_id>/organization', methods=['PUT'])
@admin_required
def set_lead_org(lead_id):
    lang = get_language()
    data = request.json or {}
    org_id = data.get('org_id')

    if org_id is not None:
        try:
            org_id = int(org_id)
        except (ValueError, TypeError):
            return jsonify({'success': False, 'error': t('org.invalid_org', lang)}), 400

    try:
        success = models.set_lead_organization(lead_id, org_id)
        if not success:
            return jsonify({'success': False, 'error': t('org.invalid_org', lang)}), 400
        return jsonify({'success': True, 'message': t('org.lead_assigned', lang)})
    except Exception:
        logger.exception('Error setting lead organization')
        return jsonify({'success': False, 'error': t('admin.internal_error_short', lang)}), 500
