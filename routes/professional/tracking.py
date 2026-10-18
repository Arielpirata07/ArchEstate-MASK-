# noodle --uses-> services (export,pdf,xlsx)
# noodle --uses-> services (matching,coverage)
# noodle --queries-> database (sql,leads,professionals)
# noodle --renders-> templates (html,professional,lead_detail)
import csv
import io
import logging
import os
import re

from io import StringIO

import openpyxl
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side, numbers

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

@professional_bp.route('/api/lead/<int:lead_id>/toggle-status', methods=['POST'])
@professional_required
@rate_limit.check_rate_limit(limit=60, window=60)
def toggle_lead_status(lead_id):
    lang = get_language()
    conn = None
    try:
        conn = models.get_db_connection()

        user = conn.execute('SELECT username FROM users WHERE id = ?', (session['user_id'],)).fetchone()
        if not user:
            return jsonify({'error': t('prof.access_denied', lang)}), 403

        professional = conn.execute(
            'SELECT status FROM professionals WHERE name = ?',
            (user['username'],)
        ).fetchone()
        if not professional or professional['status'] != 'approved':
            return jsonify({'error': t('prof.account_pending', lang)}), 403

        lead = conn.execute('SELECT id FROM leads WHERE id = ?', (lead_id,)).fetchone()
        if not lead:
            return jsonify({'error': t('prof.lead_not_found', lang)}), 404

        data = request.get_json(silent=True) or {}
        status_type = data.get('status')

        if status_type not in ('seen', 'contacted'):
            return jsonify({'error': t('prof.invalid_status_type', lang)}), 400

        professional_id = session['user_id']
        # Convención de storage en UTC (utils.utc_now_str): las ventanas SQL
        # comparan contra datetime('now') y el display convierte a ART.
        now = utils.utc_now_str()

        # Flip atómico en una sola sentencia: sin ventana leer-y-escribir,
        # dos tabs del mismo profesional no pueden perderse un cambio.
        # (status_type/timestamp_col validados arriba contra allowlist.)
        timestamp_col = f'{status_type}_at'
        updated = conn.execute(
            f'UPDATE lead_tracking SET {status_type} = 1 - {status_type}, '
            f'{timestamp_col} = CASE WHEN {status_type} = 0 THEN ? ELSE NULL END '
            'WHERE professional_id = ? AND lead_id = ? '
            f'RETURNING {status_type}',
            (now, professional_id, lead_id)
        ).fetchone()

        if updated is None:
            seen_val = 1 if status_type == 'seen' else 0
            contacted_val = 1 if status_type == 'contacted' else 0
            seen_at = now if status_type == 'seen' else None
            contacted_at = now if status_type == 'contacted' else None

            try:
                conn.execute(
                    'INSERT INTO lead_tracking (professional_id, lead_id, seen, contacted, seen_at, contacted_at) VALUES (?, ?, ?, ?, ?, ?)',
                    (professional_id, lead_id, seen_val, contacted_val, seen_at, contacted_at)
                )
                new_value = 1
            except Exception as e:
                from services.database import is_integrity_error
                if not is_integrity_error(e):
                    raise
                # Carrera: otro request concurrente insertó la fila primero
                # (UNIQUE professional+lead). Se reintenta el flip atómico
                # en vez de devolver 500.
                conn.rollback()
                updated = conn.execute(
                    f'UPDATE lead_tracking SET {status_type} = 1 - {status_type}, '
                    f'{timestamp_col} = CASE WHEN {status_type} = 0 THEN ? ELSE NULL END '
                    'WHERE professional_id = ? AND lead_id = ? '
                    f'RETURNING {status_type}',
                    (now, professional_id, lead_id)
                ).fetchone()
                if updated is None:
                    raise
                new_value = updated[status_type]
        else:
            new_value = updated[status_type]

        conn.commit()

        if new_value:
            if status_type == 'contacted':
                try:
                    from services.sla import record_first_contact
                    record_first_contact(lead_id, professional_id, 'stage')
                except Exception:
                    logger.warning('record_first_contact (toggle) fallo para lead=%s', lead_id)
            from services.notifications import notify_lead_status_change
            try:
                notify_lead_status_change(lead_id, professional_id, status_type)
            except Exception:
                logger.warning('notify_lead_status_change falló para lead=%s', lead_id)

        return jsonify({
            'success': True,
            'status': status_type,
            'value': new_value,
            'timestamp': now if new_value else None
        })
    except Exception as e:
        logger.exception('Error en toggle_lead_status')
        return jsonify({'error': t('prof.internal_error_short', lang)}), 500
    finally:
        if conn:
            conn.close()


