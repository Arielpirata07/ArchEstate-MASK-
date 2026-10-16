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

@professional_bp.route('/api/lead/<int:lead_id>/report', methods=['POST'])
@professional_required
def report_lead(lead_id):
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

        lead = conn.execute('SELECT id, type, phone FROM leads WHERE id = ?', (lead_id,)).fetchone()
        if not lead:
            return jsonify({'error': t('prof.lead_not_found', lang)}), 404

        data = request.get_json(silent=True) or {}
        notes = utils.safe_text(data.get('notes', ''))[:500]

        existing = conn.execute(
            'SELECT id FROM lead_reports WHERE lead_id = ? AND reported_by = ? AND status = ?',
            (lead_id, session['user_id'], 'pending')
        ).fetchone()
        if existing:
            return jsonify({'error': t('prof.already_reported', lang)}), 400

        try:
            conn.execute(
                'INSERT INTO lead_reports (lead_id, reported_by, reason, notes, status) VALUES (?, ?, ?, ?, ?)',
                (lead_id, session['user_id'], 'telefono_inexistente', notes, 'pending')
            )
            conn.commit()
        except Exception as e:
            from services.database import is_integrity_error
            conn.rollback()
            if is_integrity_error(e):
                # Carrera: otro request concurrente insertó el pending
                # primero (el índice único parcial lo rechazó).
                return jsonify({'error': t('prof.already_reported', lang)}), 400
            raise

        utils.log_action(
            "Reporte de Lead",
            f"Lead ID: {lead_id} (phone_hash={utils.hash_phone_digits(lead['phone'] or '')}) reportado por {user['username']}",
            session
        )

        return jsonify({
            'success': True,
            'message': t('prof.report_submitted', lang)
        })
    except Exception as e:
        logger.exception('Error en report_lead')
        return jsonify({'error': t('prof.internal_error_short', lang)}), 500
    finally:
        if conn:
            conn.close()


@professional_bp.route('/api/professional/doc-status', methods=['GET'])
@professional_required
def get_doc_status():
    lang = get_language()
    conn = None
    try:
        conn = models.get_db_connection()
        user = conn.execute('SELECT doc_path FROM users WHERE id = ?', (session['user_id'],)).fetchone()

        if not user:
            return jsonify({"success": False, "error": t('prof.user_not_found', lang)}), 404

        doc_path = user['doc_path']
        has_doc = bool(doc_path)

        if has_doc:
            from flask import current_app
            full_path = os.path.join(current_app.config['UPLOAD_FOLDER'], doc_path)
            has_doc = os.path.exists(full_path)

        return jsonify({
            "has_doc": has_doc,
            "filename": doc_path if has_doc else None,
            "display_name": re.sub(r'^user_\d+_', '', doc_path) if has_doc and doc_path else None,
        })
    except Exception as e:
        logger.exception('Error en get_doc_status')
        return jsonify({"success": False, "error": t('prof.internal_error_short', lang)}), 500
    finally:
        if conn:
            conn.close()


MAX_UPLOAD_BYTES = 10 * 1024 * 1024


@professional_bp.route('/api/professional/upload', methods=['POST'])
@rate_limit.check_rate_limit(limit=100, window=60)
@professional_required
def upload_professional_doc():
    from flask import current_app
    lang = get_language()

    if 'document' not in request.files:
        return jsonify({"success": False, "error": t('prof.no_file_included', lang)}), 400

    file = request.files['document']
    if not file or file.filename == '':
        return jsonify({"success": False, "error": t('prof.no_file_selected', lang)}), 400

    if not allowed_file(file.filename):
        return jsonify({
            "error": t('prof.invalid_file_type', lang)
        }), 415

    mime_valid, detected_ext, mime_error = utils.validate_mime_type(file, file.filename)
    if not mime_valid:
        return jsonify({"success": False, "error": mime_error}), 415

    file.seek(0, 2)
    size = file.tell()
    file.seek(0)
    if size > config.MAX_UPLOAD_SIZE:
        return jsonify({"success": False, "error": t('prof.file_too_large', lang)}), 413

    original_name = secure_filename(file.filename)
    filename = f"user_{session['user_id']}_{original_name}"
    upload_dir = current_app.config['UPLOAD_FOLDER']

    os.makedirs(upload_dir, exist_ok=True)

    conn = None
    try:
        conn = models.get_db_connection()
        prev_user = conn.execute('SELECT doc_path FROM users WHERE id = ?', (session['user_id'],)).fetchone()
        if prev_user and prev_user['doc_path']:
            prev_path = os.path.join(upload_dir, prev_user['doc_path'])
            if os.path.exists(prev_path):
                try:
                    os.remove(prev_path)
                except Exception:
                    logger.warning('No se pudo borrar doc previo: %s', prev_path)

        file.save(os.path.join(upload_dir, filename))

        conn.execute('UPDATE users SET doc_path = ? WHERE id = ?', (filename, session['user_id']))
        conn.commit()
    finally:
        if conn:
            conn.close()

    utils.log_action("Subida de Documento", f"Usuario ID: {session['user_id']}", session)

    return jsonify({
        "status": "success",
        "message": t('prof.doc_uploaded', lang),
        "filename": filename,
        "display_name": original_name,
    })


@professional_bp.route('/profesional/download_doc')
@professional_required
def download_own_doc():
    from flask import current_app

    lang = get_language()
    conn = None
    try:
        conn = models.get_db_connection()
        user = conn.execute('SELECT doc_path FROM users WHERE id = ?', (session['user_id'],)).fetchone()

        if not user or not user['doc_path']:
            flash(t('prof.no_doc_yet', lang), 'error')
            return redirect(url_for('professional.professional_view'))

        directory = current_app.config['UPLOAD_FOLDER']
        filename = user['doc_path']

        if not os.path.exists(os.path.join(directory, filename)):
            flash(t('prof.file_not_found_server', lang, filename=filename), 'error')
            return redirect(url_for('professional.professional_view'))

        from flask import send_from_directory
        return send_from_directory(directory, filename, as_attachment=True)

    except Exception as e:
        logger.exception('Error en download_professional_doc')
        flash(t('prof.internal_server_error', lang), 'error')
        return redirect(url_for('professional.professional_view'))
    finally:
        if conn:
            conn.close()
