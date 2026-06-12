import csv
import io
import os
import re

from datetime import datetime
from io import StringIO

import openpyxl
import pytz

from flask import Blueprint, flash, jsonify, redirect, render_template, request, Response, send_file, session, url_for
from fpdf import FPDF
from werkzeug.utils import secure_filename

import config
import models
import rate_limit
import utils
from decorators import login_required, professional_required
from utils import allowed_file, convert_to_argentina_time

professional_bp = Blueprint('professional', __name__, url_prefix='')


@professional_bp.route('/profesional')
@professional_required
def professional_view():
    conn = None
    try:
        conn = models.get_db_connection()
        user = conn.execute('SELECT username, doc_path FROM users WHERE id = ?', (session['user_id'],)).fetchone()
        if not user:
            return redirect(url_for('public.index'))

        professional = conn.execute('SELECT status FROM professionals WHERE name = ?', (user['username'],)).fetchone()
        if not professional or professional['status'] != 'approved':
            return render_template('professional.html', pending=True, doc_path=user['doc_path'])

        return render_template('professional.html', pending=False, doc_path=user['doc_path'])
    finally:
        if conn:
            conn.close()


@professional_bp.route('/profesional/lead/<int:lead_id>')
@professional_required
def lead_detail(lead_id):
    conn = None
    try:
        conn = models.get_db_connection()
        user = conn.execute('SELECT username FROM users WHERE id = ?', (session['user_id'],)).fetchone()
        if not user:
            return redirect(url_for('public.index'))

        professional = conn.execute('SELECT status FROM professionals WHERE name = ?', (user['username'],)).fetchone()
        if not professional or professional['status'] != 'approved':
            return render_template('professional.html', pending=True)

        lead = conn.execute('SELECT * FROM leads WHERE id = ?', (lead_id,)).fetchone()
    finally:
        if conn:
            conn.close()

    if not lead:
        return redirect(url_for('professional.professional_view'))

    lead_dict = dict(lead)
    lead_dict['timestamp'] = convert_to_argentina_time(lead_dict['timestamp'])
    phone_raw = lead_dict.get('phone') or ''
    lead_dict['phone_e164'] = utils.normalize_phone_to_e164(phone_raw)
    lead_dict['phone_is_mobile'] = bool(lead_dict['phone_e164'] and utils.is_whatsapp_capable(lead_dict['phone_e164']))
    return render_template('lead_detail.html', lead=lead_dict)


@professional_bp.route('/api/leads')
@professional_required
def get_leads_api():
    conn = None
    try:
        conn = models.get_db_connection()

        user = conn.execute('SELECT username FROM users WHERE id = ?', (session['user_id'],)).fetchone()
        if not user:
            return jsonify({"status": "error", "message": "Acceso denegado"}), 403

        professional = conn.execute('SELECT status FROM professionals WHERE name = ?', (user['username'],)).fetchone()
        if not professional or professional['status'] != 'approved':
            return jsonify({"status": "error", "message": "Cuenta pendiente de aprobación"}), 403

        search = request.args.get('search', '').strip()
        type_filter = request.args.get('type', '').strip()
        prop_type = request.args.get('property_type', '').strip()
        zone_filter = request.args.get('zone', '').strip()
        min_budget = request.args.get('min_budget', '').strip()
        max_budget = request.args.get('max_budget', '').strip()
        budget_range = request.args.get('budget_range', '').strip()
        currency_filter = request.args.get('currency', '').strip()
        sort_by = request.args.get('sort', 'timestamp')
        sort_order = request.args.get('order', 'desc')

        BUDGET_RANGES = {
            'hasta_200k': (0, 200000),
            '200k_500k': (200000, 500000),
            '500k_1m': (500000, 1000000),
            '1m_2m': (1000000, 2000000),
            'mas_2m': (2000000, None),
        }
        if budget_range and budget_range in BUDGET_RANGES:
            rng = BUDGET_RANGES[budget_range]
            min_budget = str(rng[0]) if rng[0] else ''
            max_budget = str(rng[1]) if rng[1] else ''

        query = 'SELECT * FROM leads WHERE 1=1'
        params = []

        if search:
            query += ' AND (zone LIKE ? OR email LIKE ? OR type LIKE ? OR budget LIKE ?)'
            search_param = f'%{search}%'
            params.extend([search_param, search_param, search_param, search_param])

        if type_filter:
            query += ' AND type = ?'
            params.append(type_filter)

        if prop_type:
            query += ' AND property_type = ?'
            params.append(prop_type)

        if zone_filter:
            query += ' AND zone LIKE ?'
            params.append(f'%{zone_filter}%')

        if min_budget:
            try:
                min_val = float(min_budget)
                query += " AND CAST(REPLACE(REPLACE(budget, '.', ''), ',', '') AS REAL) >= ?"
                params.append(min_val)
            except ValueError:
                pass

        if max_budget:
            try:
                max_val = float(max_budget)
                query += " AND CAST(REPLACE(REPLACE(budget, '.', ''), ',', '') AS REAL) <= ?"
                params.append(max_val)
            except ValueError:
                pass

        if currency_filter:
            query += ' AND currency = ?'
            params.append(currency_filter)

        valid_sort_fields = ['id', 'type', 'zone', 'budget', 'timestamp', 'email']
        if sort_by not in valid_sort_fields:
            sort_by = 'timestamp'

        order = 'DESC' if sort_order.lower() == 'desc' else 'ASC'
        if order not in ('ASC', 'DESC'):
            order = 'ASC'
        query += f' ORDER BY {sort_by} {order}, id DESC'

        leads = conn.execute(query, params).fetchall()

        leads_list = []
        for lead in leads:
            lead_dict = dict(lead)
            lead_dict['timestamp'] = convert_to_argentina_time(lead_dict['timestamp'])
            phone_raw = lead_dict.get('phone') or ''
            phone_e164 = utils.normalize_phone_to_e164(phone_raw)
            lead_dict['phone_e164'] = phone_e164
            lead_dict['phone_is_mobile'] = bool(phone_e164 and utils.is_whatsapp_capable(phone_e164))
            leads_list.append(lead_dict)

        professional_id = session['user_id']
        lead_ids = [lead['id'] for lead in leads_list]

        tracking_map = {}
        if lead_ids:
            placeholders = ','.join(['?'] * len(lead_ids))
            tracking_rows = conn.execute(
                f'SELECT lead_id, seen, contacted FROM lead_tracking WHERE professional_id = ? AND lead_id IN ({placeholders})',
                [professional_id] + lead_ids
            ).fetchall()
            for row in tracking_rows:
                tracking_map[row['lead_id']] = {
                    'seen': bool(row['seen']),
                    'contacted': bool(row['contacted'])
                }

        for lead in leads_list:
            tracking = tracking_map.get(lead['id'], {'seen': False, 'contacted': False})
            lead['tracking'] = tracking

        return jsonify({
            "success": True,
            "leads": leads_list,
            "total": len(leads_list)
        })
    except Exception as e:
        print(f"Error en get_leads_api: {e}")
        return jsonify({"status": "error", "message": "Error interno del servidor"}), 500
    finally:
        if conn:
            conn.close()


@professional_bp.route('/api/leads/filter-options')
@professional_required
def get_leads_filter_options():
    from app_setup import filter_cache
    cached = filter_cache.get('filter_options')
    if cached:
        return jsonify(cached)

    conn = None
    try:
        conn = models.get_db_connection()
        types = [r[0] for r in conn.execute('SELECT DISTINCT type FROM leads WHERE type IS NOT NULL ORDER BY type').fetchall()]
        prop_types = [r[0] for r in conn.execute('SELECT DISTINCT property_type FROM leads WHERE property_type IS NOT NULL ORDER BY property_type').fetchall()]
        currencies = [r[0] for r in conn.execute('SELECT DISTINCT currency FROM leads WHERE currency IS NOT NULL ORDER BY currency').fetchall()]
        zones = [r[0] for r in conn.execute('SELECT DISTINCT zone FROM leads WHERE zone IS NOT NULL ORDER BY zone').fetchall()]

        result = {
            'types': types,
            'property_types': prop_types,
            'currencies': currencies,
            'zones': zones,
        }
        filter_cache.set('filter_options', result)
        return jsonify(result)
    finally:
        if conn:
            conn.close()


@professional_bp.route('/api/leads/filter-options/invalidate', methods=['POST'])
@login_required
def invalidate_filter_cache():
    from app_setup import filter_cache
    filter_cache.invalidate()
    return jsonify({"status": "success", "message": "Caché invalidada"})


@professional_bp.route('/api/leads/export')
@professional_required
def export_leads_csv():
    conn = None
    leads = []
    try:
        conn = models.get_db_connection()
        user = conn.execute('SELECT username FROM users WHERE id = ?', (session['user_id'],)).fetchone()
        if not user:
            return "Acceso denegado", 403

        professional = conn.execute('SELECT status FROM professionals WHERE name = ?', (user['username'],)).fetchone()
        if not professional or professional['status'] != 'approved':
            return "Cuenta pendiente de aprobación", 403

        leads = conn.execute('SELECT id, type, zone, budget, currency, timestamp FROM leads ORDER BY timestamp DESC').fetchall()
    finally:
        if conn:
            conn.close()

    def generate():
        data = StringIO()
        writer = csv.writer(data)
        writer.writerow(['ID', 'Tipo Operacion', 'Zona', 'Presupuesto', 'Moneda', 'Fecha Registro (Argentina)'])
        yield data.getvalue()
        data.seek(0)
        data.truncate(0)

        for lead in leads:
            timestamp_argentina = convert_to_argentina_time(lead['timestamp'])
            writer.writerow([lead['id'], lead['type'], lead['zone'], lead['budget'], lead['currency'], timestamp_argentina])
            yield data.getvalue()
            data.seek(0)
            data.truncate(0)

    filename = f"leads_archestate_{datetime.now().strftime('%Y%m%d_%H%M')}.csv"
    return Response(
        generate(),
        mimetype='text/csv',
        headers={
            'Content-Disposition': f'attachment; filename="{filename}"'
        }
    )


@professional_bp.route('/api/leads/export/xlsx')
@professional_required
def export_leads_xlsx():
    conn = None
    leads = []
    try:
        conn = models.get_db_connection()
        user = conn.execute('SELECT username FROM users WHERE id = ?', (session['user_id'],)).fetchone()
        if not user:
            return "Acceso denegado", 403

        professional = conn.execute('SELECT status FROM professionals WHERE name = ?', (user['username'],)).fetchone()
        if not professional or professional['status'] != 'approved':
            return "Cuenta pendiente de aprobación", 403

        leads = conn.execute('SELECT id, type, zone, budget, currency, timestamp FROM leads ORDER BY timestamp DESC').fetchall()
    finally:
        if conn:
            conn.close()

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Leads"

    headers = ['ID', 'Tipo Operacion', 'Zona', 'Presupuesto', 'Moneda', 'Fecha Registro (Argentina)']
    for col_num, header in enumerate(headers, 1):
        ws.cell(row=1, column=col_num, value=header)

    for row_num, lead in enumerate(leads, 2):
        timestamp_argentina = convert_to_argentina_time(lead['timestamp'])
        ws.cell(row=row_num, column=1, value=lead['id'])
        ws.cell(row=row_num, column=2, value=lead['type'])
        ws.cell(row=row_num, column=3, value=lead['zone'])
        ws.cell(row=row_num, column=4, value=lead['budget'])
        ws.cell(row=row_num, column=5, value=lead['currency'])
        ws.cell(row=row_num, column=6, value=timestamp_argentina)

    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)

    filename = f"leads_archestate_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
    return send_file(
        buffer,
        as_attachment=True,
        download_name=filename,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )


@professional_bp.route('/api/lead/<int:lead_id>/download')
@professional_required
def download_lead_pdf(lead_id):
    conn = None
    try:
        conn = models.get_db_connection()
        user = conn.execute('SELECT username FROM users WHERE id = ?', (session['user_id'],)).fetchone()
        if not user:
            return "Acceso denegado", 403

        professional = conn.execute('SELECT status FROM professionals WHERE name = ?', (user['username'],)).fetchone()
        if not professional or professional['status'] != 'approved':
            return "Cuenta pendiente de aprobación", 403

        lead = conn.execute('SELECT * FROM leads WHERE id = ?', (lead_id,)).fetchone()
    finally:
        if conn:
            conn.close()

    if not lead:
        return jsonify({"status": "error", "message": "Lead no encontrado"}), 404

    lead = dict(lead)

    def pdf_safe(value):
        if value is None:
            return ''
        text = str(value)
        replacements = {
            '\u20ac': 'EUR', '\u00a3': 'GBP', '\u00a5': 'JPY',
            '\u2014': '-', '\u2013': '-', '\u2022': '-',
            '\u221a': 'sqrt', '\u00d7': 'x', '\u00f7': '/',
            '\u2122': 'TM', '\u00a9': '(c)', '\u00ae': '(R)',
            '\u2026': '...', '\u00b2': '2', '\u00b3': '3', '\u00b0': 'deg',
        }
        for old, new in replacements.items():
            text = text.replace(old, new)
        accents = {
            '\u00e1': 'a', '\u00e9': 'e', '\u00ed': 'i', '\u00f3': 'o', '\u00fa': 'u',
            '\u00e0': 'a', '\u00e8': 'e', '\u00ec': 'i', '\u00f2': 'o', '\u00f9': 'u',
            '\u00e4': 'a', '\u00eb': 'e', '\u00ef': 'i', '\u00f6': 'o', '\u00fc': 'u',
            '\u00e3': 'a', '\u00f5': 'o', '\u00f1': 'n',
            '\u00c1': 'A', '\u00c9': 'E', '\u00cd': 'I', '\u00d3': 'O', '\u00da': 'U',
            '\u00c0': 'A', '\u00c8': 'E', '\u00cc': 'I', '\u00d2': 'O', '\u00d9': 'U',
            '\u00c4': 'A', '\u00cb': 'E', '\u00cf': 'I', '\u00d6': 'O', '\u00dc': 'U',
            '\u00c3': 'A', '\u00d5': 'O', '\u00d1': 'N',
            '\u00e7': 'c', '\u00c7': 'C', '\u00df': 'ss',
        }
        for old, new in accents.items():
            text = text.replace(old, new)
        return ''.join(c if ord(c) < 128 else '?' for c in text)

    def pdf_val(value, default='-'):
        text = pdf_safe(value)
        return text if text else default

    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)

    midnight = (0, 4, 16)
    gold = (115, 90, 58)

    pdf.set_font('Times', 'BI', 20)
    pdf.set_text_color(*midnight)
    pdf.cell(0, 15, 'ArchEstate - Detalle de Lead', ln=True, align='C')
    pdf.ln(5)

    pdf.set_font('Helvetica', '', 10)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 8, f'Lead #{lead["id"]} - Informacion completa enviada por el cliente', ln=True, align='C')
    pdf.ln(10)

    def section_header(title):
        pdf.set_fill_color(*gold)
        pdf.set_text_color(255, 255, 255)
        pdf.set_font('Helvetica', 'B', 12)
        pdf.cell(0, 8, title.upper(), ln=True, fill=True)
        pdf.set_text_color(*midnight)
        pdf.set_font('Helvetica', '', 10)
        pdf.ln(2)

    section_header('Tipo de Operacion')
    pdf.cell(0, 6, pdf_val(lead['type']), ln=True)

    section_header('Zona Geografica')
    pdf.cell(0, 6, pdf_val(lead['zone']), ln=True)

    section_header('Presupuesto')
    budget_symbol = 'USD' if lead['currency'] == 'USD' else 'EUR' if lead['currency'] == 'EUR' else '$'
    pdf.cell(0, 6, f"{budget_symbol} {pdf_val(lead['budget'])}", ln=True)

    section_header('Estilo Arquitectonico')
    pdf.cell(0, 6, pdf_val(lead.get('architectural_style'), 'No especificado'), ln=True)

    section_header('Contacto Directo')
    pdf.cell(0, 6, f"Email: {pdf_val(lead['email'])}", ln=True)
    pdf.cell(0, 6, f"Telefono: {pdf_val(lead['phone'])}", ln=True)

    section_header('Registrado')
    pdf.cell(0, 6, pdf_val(convert_to_argentina_time(lead['timestamp'])), ln=True)
    pdf.ln(5)

    section_header('Especificaciones Tecnicas')

    pdf.set_font('Helvetica', 'B', 10)
    pdf.cell(60, 8, 'Habitaciones:', border=1)
    pdf.cell(0, 8, pdf_val(lead['bedrooms']), ln=True, border=1)

    pdf.cell(60, 8, 'Banios:', border=1)
    pdf.cell(0, 8, pdf_val(lead['bathrooms']), ln=True, border=1)

    prop_type = pdf_safe(lead.get('property_type', '')).lower()
    if prop_type == 'casa':
        pdf.cell(60, 8, 'Metros de Terreno:', border=1)
        pdf.cell(0, 8, f"{pdf_val(lead['land_area'])} m2" if lead.get('land_area') else '-', ln=True, border=1)
    else:
        pdf.cell(60, 8, 'Metros Utiles:', border=1)
        pdf.cell(0, 8, f"{pdf_val(lead['usable_m2'])} m2" if lead.get('usable_m2') else '-', ln=True, border=1)

    pdf.ln(5)

    section_header('Extras y Comodidades')
    amenities = lead.get('amenities', '')
    if amenities and str(amenities).strip():
        for amenity in pdf_safe(amenities).split(','):
            stripped = amenity.strip()
            if stripped:
                pdf.cell(0, 6, f"- {stripped}", ln=True)
    else:
        pdf.cell(0, 6, 'No especificadas', ln=True)

    if prop_type == 'departamento':
        section_header('Detalles del Departamento')
        pdf.cell(0, 6, f"Piso / Bloque: {pdf_val(lead.get('floor_block'), 'No especificado')}", ln=True)
        pdf.cell(0, 6, f"Metros Utiles: {pdf_val(lead.get('usable_m2'), 'No especificado')} m2", ln=True)
        pdf.cell(0, 6, f"Ascensor: {pdf_val(lead.get('elevator'), 'No especificado')}", ln=True)
    else:
        section_header('Detalles de la Propiedad')
        pdf.cell(0, 6, f"Superficie de Terreno: {pdf_val(lead.get('land_area'), 'No especificado')} m2", ln=True)
        pdf.cell(0, 6, f"Superficie Construida: {pdf_val(lead.get('built_area'), 'No especificado')} m2", ln=True)
        pdf.cell(0, 6, f"Piscina: {pdf_val(lead.get('pool'), 'No especificado')}", ln=True)

    pdf_output = pdf.output(dest='S')
    if isinstance(pdf_output, str):
        pdf_output = pdf_output.encode('latin-1')

    buffer = io.BytesIO(pdf_output)
    buffer.seek(0)

    filename = f"lead_{lead['id']}.pdf"

    return send_file(
        buffer,
        as_attachment=True,
        download_name=filename,
        mimetype='application/pdf'
    )


@professional_bp.route('/api/lead/<int:lead_id>/toggle-status', methods=['POST'])
@professional_required
def toggle_lead_status(lead_id):
    conn = None
    try:
        conn = models.get_db_connection()

        user = conn.execute('SELECT username FROM users WHERE id = ?', (session['user_id'],)).fetchone()
        if not user:
            return jsonify({'error': 'Acceso denegado'}), 403

        professional = conn.execute(
            'SELECT status FROM professionals WHERE name = ?',
            (user['username'],)
        ).fetchone()
        if not professional or professional['status'] != 'approved':
            return jsonify({'error': 'Cuenta pendiente de aprobacion'}), 403

        lead = conn.execute('SELECT id FROM leads WHERE id = ?', (lead_id,)).fetchone()
        if not lead:
            return jsonify({'error': 'Lead no encontrado'}), 404

        data = request.get_json()
        status_type = data.get('status')

        if status_type not in ('seen', 'contacted'):
            return jsonify({'error': 'Tipo de estado invalido'}), 400

        professional_id = session['user_id']
        argentina_tz = pytz.timezone('America/Argentina/Buenos_Aires')
        now = datetime.now(argentina_tz).strftime('%Y-%m-%d %H:%M:%S')

        tracking = conn.execute(
            'SELECT * FROM lead_tracking WHERE professional_id = ? AND lead_id = ?',
            (professional_id, lead_id)
        ).fetchone()

        if tracking:
            current_value = tracking[status_type]
            new_value = 0 if current_value else 1
            timestamp_col = f'{status_type}_at'
            timestamp_value = now if new_value else None

            conn.execute(
                f'UPDATE lead_tracking SET {status_type} = ?, {timestamp_col} = ? WHERE professional_id = ? AND lead_id = ?',
                (new_value, timestamp_value, professional_id, lead_id)
            )
        else:
            seen_val = 1 if status_type == 'seen' else 0
            contacted_val = 1 if status_type == 'contacted' else 0
            seen_at = now if status_type == 'seen' else None
            contacted_at = now if status_type == 'contacted' else None

            conn.execute(
                'INSERT INTO lead_tracking (professional_id, lead_id, seen, contacted, seen_at, contacted_at) VALUES (?, ?, ?, ?, ?, ?)',
                (professional_id, lead_id, seen_val, contacted_val, seen_at, contacted_at)
            )
            new_value = 1

        conn.commit()

        return jsonify({
            'success': True,
            'status': status_type,
            'value': new_value,
            'timestamp': now if new_value else None
        })
    except Exception as e:
        print(f"Error en toggle_lead_status: {e}")
        return jsonify({'error': 'Error interno'}), 500
    finally:
        if conn:
            conn.close()


@professional_bp.route('/api/lead/<int:lead_id>/report', methods=['POST'])
@professional_required
def report_lead(lead_id):
    conn = None
    try:
        conn = models.get_db_connection()

        user = conn.execute('SELECT username FROM users WHERE id = ?', (session['user_id'],)).fetchone()
        if not user:
            return jsonify({'error': 'Acceso denegado'}), 403

        professional = conn.execute(
            'SELECT status FROM professionals WHERE name = ?',
            (user['username'],)
        ).fetchone()
        if not professional or professional['status'] != 'approved':
            return jsonify({'error': 'Cuenta pendiente de aprobacion'}), 403

        lead = conn.execute('SELECT id, type, phone FROM leads WHERE id = ?', (lead_id,)).fetchone()
        if not lead:
            return jsonify({'error': 'Lead no encontrado'}), 404

        data = request.get_json() or {}
        notes = utils.safe_text(data.get('notes', ''))[:500]

        existing = conn.execute(
            'SELECT id FROM lead_reports WHERE lead_id = ? AND reported_by = ? AND status = ?',
            (lead_id, session['user_id'], 'pending')
        ).fetchone()
        if existing:
            return jsonify({'error': 'Ya reportaste este pedido anteriormente'}), 400

        conn.execute(
            'INSERT INTO lead_reports (lead_id, reported_by, reason, notes, status) VALUES (?, ?, ?, ?, ?)',
            (lead_id, session['user_id'], 'telefono_inexistente', notes, 'pending')
        )
        conn.commit()

        utils.log_action(
            "Reporte de Lead",
            f"Lead ID: {lead_id} (phone_hash={utils.hash_phone_digits(lead['phone'] or '')}) reportado por {user['username']}",
            session
        )

        return jsonify({
            'success': True,
            'message': 'Pedido reportado correctamente'
        })
    except Exception as e:
        print(f"Error en report_lead: {e}")
        return jsonify({'error': 'Error interno'}), 500
    finally:
        if conn:
            conn.close()


@professional_bp.route('/api/professional/doc-status', methods=['GET'])
@professional_required
def get_doc_status():
    conn = None
    try:
        conn = models.get_db_connection()
        user = conn.execute('SELECT doc_path FROM users WHERE id = ?', (session['user_id'],)).fetchone()

        if not user:
            return jsonify({"error": "Usuario no encontrado"}), 404

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
        print(f"Error en get_doc_status: {e}")
        return jsonify({"error": "Error interno"}), 500
    finally:
        if conn:
            conn.close()


MAX_UPLOAD_BYTES = 10 * 1024 * 1024


@professional_bp.route('/api/professional/upload', methods=['POST'])
@rate_limit.check_rate_limit(limit=100, window=60)
@professional_required
def upload_professional_doc():
    from flask import current_app

    if 'document' not in request.files:
        return jsonify({"error": "No se incluyó ningún archivo en la solicitud."}), 400

    file = request.files['document']
    if not file or file.filename == '':
        return jsonify({"error": "No se seleccionó ningún archivo."}), 400

    if not allowed_file(file.filename):
        return jsonify({
            "error": "Tipo de archivo no permitido. Usá PDF, JPG o PNG."
        }), 415

    mime_valid, detected_ext, mime_error = utils.validate_mime_type(file, file.filename)
    if not mime_valid:
        return jsonify({"error": mime_error}), 415

    file.seek(0, 2)
    size = file.tell()
    file.seek(0)
    if size > config.MAX_UPLOAD_SIZE:
        return jsonify({"error": "El archivo supera el límite de 10 MB."}), 413

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
                    pass

        file.save(os.path.join(upload_dir, filename))

        conn.execute('UPDATE users SET doc_path = ? WHERE id = ?', (filename, session['user_id']))
        conn.commit()
    finally:
        if conn:
            conn.close()

    utils.log_action("Subida de Documento", f"Usuario ID: {session['user_id']}", session)

    return jsonify({
        "status": "success",
        "message": "Documento subido correctamente.",
        "filename": filename,
        "display_name": original_name,
    })


@professional_bp.route('/profesional/download_doc')
@professional_required
def download_own_doc():
    from flask import current_app

    conn = None
    try:
        conn = models.get_db_connection()
        user = conn.execute('SELECT doc_path FROM users WHERE id = ?', (session['user_id'],)).fetchone()

        if not user or not user['doc_path']:
            flash('No has subido ningún documento aún.', 'error')
            return redirect(url_for('professional.professional_view'))

        directory = current_app.config['UPLOAD_FOLDER']
        filename = user['doc_path']

        if not os.path.exists(os.path.join(directory, filename)):
            flash(f'Error: El archivo {filename} no existe en el servidor.', 'error')
            return redirect(url_for('professional.professional_view'))

        from flask import send_from_directory
        return send_from_directory(directory, filename, as_attachment=True)

    except Exception as e:
        print(f"Error en download_professional_doc: {e}")
        flash('Error interno del servidor.', 'error')
        return redirect(url_for('professional.professional_view'))
    finally:
        if conn:
            conn.close()
