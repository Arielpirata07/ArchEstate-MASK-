# noodle --uses-> services (export,pdf,xlsx)
# noodle --uses-> services (matching,coverage)
# noodle --queries-> database (sql,leads,professionals)
# noodle --renders-> templates (html,professional,lead_detail)
import csv
import io
import logging
import os
import re

from datetime import datetime
from io import StringIO

import openpyxl
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side, numbers
import pytz

logger = logging.getLogger(__name__)

from flask import Blueprint, flash, jsonify, redirect, render_template, request, Response, send_file, session, url_for
from fpdf import FPDF
from werkzeug.utils import secure_filename

import config
import models
import rate_limit
import utils
from decorators import login_required, professional_required
from i18n import t, get_language
from services.database import date_format_sql, now_sql
from services.export_helpers import pdf_safe, pdf_val, _style_header_row, _apply_data_border
from services.matching import lead_matches_coverage
from utils import allowed_file, convert_to_argentina_time


from routes.professional import professional_bp
from routes.professional.helpers import _get_approved_professional, _get_pro_geo_filter

@professional_bp.route('/api/pipeline/stages')
@professional_required
def pipeline_stages():
    lang = get_language()
    conn = None
    try:
        conn = models.get_db_connection()
        _, error = _get_approved_professional(conn, session['user_id'], lang)
        if error:
            return error
        my_leads = request.args.get('my_leads', '1').strip() == '1'
        extra_where, extra_params = '', ()
        if my_leads:
            conds, geo_params = _get_pro_geo_filter(conn, session['user_id'])
            if conds:
                extra_where = ' AND '.join(conds)
                extra_params = tuple(geo_params)
        counts = models.get_pipeline_counts(session['user_id'], extra_where, extra_params)
        return jsonify({
            'success': True,
            'stages': [{'stage': stage, 'count': counts.get(stage, 0)} for stage in models.PIPELINE_STAGES]
        })
    except Exception:
        logger.exception('Error en pipeline_stages')
        return jsonify({'success': False, 'error': t('prof.internal_error_short', lang)}), 500
    finally:
        if conn:
            conn.close()


@professional_bp.route('/api/pipeline/leads')
@professional_required
def pipeline_leads():
    lang = get_language()
    conn = None
    try:
        conn = models.get_db_connection()
        _, error = _get_approved_professional(conn, session['user_id'], lang)
        if error:
            return error

        stage = request.args.get('stage', '').strip()
        if stage and stage not in models.PIPELINE_STAGES:
            return jsonify({'success': False, 'error': t('pipeline.invalid_stage', lang)}), 400
        my_leads = request.args.get('my_leads', '1').strip() == '1'
        search = request.args.get('search', '').strip()
        type_filter = request.args.get('type', '').strip()
        prop_type = request.args.get('property_type', '').strip()
        zone_filter = request.args.get('zone', '').strip()
        try:
            page = max(1, int(request.args.get('page', '1')))
        except ValueError:
            page = 1
        try:
            per_page = max(5, min(100, int(request.args.get('per_page', '25'))))
        except ValueError:
            per_page = 25
        offset = (page - 1) * per_page

        query = '''SELECT leads.*, COALESCE(lead_stages.stage, 'new') AS pipeline_stage,
                   lead_stages.updated_at AS stage_updated_at
                   FROM leads LEFT JOIN lead_stages
                   ON lead_stages.lead_id = leads.id AND lead_stages.professional_id = ?
                   WHERE 1=1'''
        params = [session['user_id']]

        if my_leads:
            conds, geo_params = _get_pro_geo_filter(conn, session['user_id'])
            for c in conds:
                query += f' AND {c}'
            params.extend(geo_params)
        if stage:
            if stage == 'new':
                query += ' AND (lead_stages.stage IS NULL OR lead_stages.stage = ?)'
                params.append(stage)
            else:
                query += ' AND lead_stages.stage = ?'
                params.append(stage)
        if search:
            query += ' AND (leads.zone LIKE ? OR leads.email LIKE ? OR leads.type LIKE ? OR leads.budget LIKE ?)'
            search_param = f'%{search}%'
            params.extend([search_param, search_param, search_param, search_param])
        if type_filter:
            query += ' AND leads.type = ?'
            params.append(type_filter)
        if prop_type:
            query += ' AND leads.property_type = ?'
            params.append(prop_type)
        if zone_filter:
            query += ' AND leads.zone LIKE ?'
            params.append(f'%{zone_filter}%')

        total = conn.execute(f'SELECT COUNT(*) AS total FROM ({query}) AS sub', params).fetchone()['total']
        query += ' ORDER BY leads.timestamp DESC, leads.id DESC LIMIT ? OFFSET ?'
        params.extend([per_page, offset])
        rows = conn.execute(query, params).fetchall()

        from datetime import datetime as _dt
        # stage_updated_at se guarda en UTC (ver models/pipeline.py): comparar
        # contra hora local del servidor desfasaba days_in_stage por el offset.
        now = utils.utc_now()
        leads_list = []
        for row in rows:
            lead_dict = dict(row)
            lead_dict['timestamp'] = convert_to_argentina_time(lead_dict['timestamp'])
            try:
                updated = _dt.strptime((lead_dict.get('stage_updated_at') or '')[:19], '%Y-%m-%d %H:%M:%S')
                lead_dict['days_in_stage'] = max(0, (now - updated).days)
            except ValueError:
                lead_dict['days_in_stage'] = 0
            leads_list.append(lead_dict)

        total_pages = max(1, (total + per_page - 1) // per_page)
        return jsonify({
            'success': True, 'leads': leads_list, 'total': total,
            'page': page, 'per_page': per_page, 'total_pages': total_pages
        })
    except Exception:
        logger.exception('Error en pipeline_leads')
        return jsonify({'success': False, 'error': t('prof.internal_error_short', lang)}), 500
    finally:
        if conn:
            conn.close()


@professional_bp.route('/api/pipeline/lead/<int:lead_id>/move', methods=['POST'])
@professional_required
@rate_limit.check_rate_limit(limit=60, window=60)
def pipeline_move_lead(lead_id):
    lang = get_language()
    conn = None
    try:
        conn = models.get_db_connection()
        _, error = _get_approved_professional(conn, session['user_id'], lang)
        if error:
            return error

        lead = conn.execute('SELECT id FROM leads WHERE id = ?', (lead_id,)).fetchone()
        if not lead:
            return jsonify({'success': False, 'error': t('prof.lead_not_found', lang)}), 404

        data = request.get_json(silent=True) or {}
        to_stage = (data.get('stage') or '').strip()
        if to_stage not in models.PIPELINE_STAGES:
            return jsonify({'success': False, 'error': t('pipeline.invalid_stage', lang)}), 400

        argentina_tz = pytz.timezone('America/Argentina/Buenos_Aires')
        now = datetime.now(argentina_tz).strftime('%Y-%m-%d %H:%M:%S')
        result = models.move_lead_stage(session['user_id'], lead_id, to_stage, now)
        if not result:
            return jsonify({'success': False, 'error': t('prof.internal_error_short', lang)}), 500
        from_stage, new_stage = result
        return jsonify({
            'success': True, 'lead_id': lead_id,
            'from_stage': from_stage, 'to_stage': new_stage,
            'message': t('pipeline.move_success', lang)
        })
    except Exception:
        logger.exception('Error en pipeline_move_lead')
        return jsonify({'success': False, 'error': t('prof.internal_error_short', lang)}), 500
    finally:
        if conn:
            conn.close()


@professional_bp.route('/api/pipeline/leads/bulk-move', methods=['POST'])
@professional_required
@rate_limit.check_rate_limit(limit=60, window=60)
def pipeline_bulk_move():
    lang = get_language()
    conn = None
    try:
        conn = models.get_db_connection()
        _, error = _get_approved_professional(conn, session['user_id'], lang)
        if error:
            return error

        data = request.get_json(silent=True) or {}
        to_stage = (data.get('stage') or '').strip()
        lead_ids = data.get('ids') or data.get('lead_ids') or []
        if to_stage not in models.PIPELINE_STAGES:
            return jsonify({'success': False, 'error': t('pipeline.invalid_stage', lang)}), 400
        if not isinstance(lead_ids, list) or not lead_ids:
            return jsonify({'success': False, 'error': t('pipeline.invalid_ids', lang)}), 400
        try:
            lead_ids = [int(i) for i in lead_ids][:100]
        except (ValueError, TypeError):
            return jsonify({'success': False, 'error': t('pipeline.invalid_ids', lang)}), 400

        argentina_tz = pytz.timezone('America/Argentina/Buenos_Aires')
        now = datetime.now(argentina_tz).strftime('%Y-%m-%d %H:%M:%S')
        # Una sola transacción all-or-nothing (ids inexistentes se ignoran).
        moved = models.move_lead_stage_batch(session['user_id'], lead_ids, to_stage, now)
        return jsonify({'success': True, 'moved': moved, 'to_stage': to_stage})
    except Exception:
        logger.exception('Error en pipeline_bulk_move')
        return jsonify({'success': False, 'error': t('prof.internal_error_short', lang)}), 500
    finally:
        if conn:
            conn.close()


@professional_bp.route('/api/pipeline/stats')
@professional_required
def pipeline_stats():
    lang = get_language()
    conn = None
    try:
        conn = models.get_db_connection()
        _, error = _get_approved_professional(conn, session['user_id'], lang)
        if error:
            return error
        stats = models.get_pipeline_stats(session['user_id'])
        return jsonify({'success': True, 'stats': stats})
    except Exception:
        logger.exception('Error en pipeline_stats')
        return jsonify({'success': False, 'error': t('prof.internal_error_short', lang)}), 500
    finally:
        if conn:
            conn.close()


