import os

from datetime import datetime

import pytz

from flask import Blueprint, jsonify, redirect, render_template, request, send_from_directory, session, url_for
from werkzeug.security import generate_password_hash

import models
import rate_limit
import utils
from decorators import admin_required, login_required
from utils import convert_to_argentina_time

admin_bp = Blueprint('admin', __name__, url_prefix='')


@admin_bp.route('/admin')
@admin_required
def admin_view():
    conn = None
    try:
        conn = models.get_db_connection()
        audit_logs = conn.execute('SELECT * FROM audit_log ORDER BY timestamp DESC').fetchall()
    finally:
        if conn:
            conn.close()

    audit_log_converted = []
    for log in audit_logs:
        log_dict = dict(log)
        log_dict['timestamp'] = convert_to_argentina_time(log_dict['timestamp'])
        audit_log_converted.append(log_dict)

    return render_template('admin.html', audit_log=audit_log_converted)


@admin_bp.route('/api/professionals')
@admin_required
def get_professionals_api():
    conn = None
    try:
        conn = models.get_db_connection()

        search = request.args.get('search', '').strip()
        status_filter = request.args.get('status', '').strip()
        specialty_filter = request.args.get('specialty', '').strip()
        sort_by = request.args.get('sort', 'id')
        sort_order = request.args.get('order', 'desc')

        query = '''
            SELECT p.*,
                   u.doc_path,
                   u.id   AS user_id,
                   u.is_active
            FROM professionals p
            LEFT JOIN users u ON (
                (p.user_id IS NOT NULL AND p.user_id = u.id)
                OR
                (p.user_id IS NULL AND p.name = u.username)
            )
            WHERE 1=1
        '''
        params = []

        if search:
            query += ' AND (p.name LIKE ? OR p.license LIKE ? OR p.specialty LIKE ?)'
            search_param = f'%{search}%'
            params.extend([search_param, search_param, search_param])

        if status_filter:
            query += ' AND p.status = ?'
            params.append(status_filter)

        if specialty_filter:
            query += ' AND p.specialty LIKE ?'
            params.append(f'%{specialty_filter}%')

        valid_sort_fields = ['id', 'name', 'license', 'specialty', 'status']
        if sort_by not in valid_sort_fields:
            sort_by = 'id'

        order = 'DESC' if sort_order.lower() == 'desc' else 'ASC'
        if order not in ('ASC', 'DESC'):
            order = 'ASC'
        query += f' ORDER BY p.{sort_by} {order}'

        professionals = conn.execute(query, params).fetchall()

        pros_list = []
        for pro in professionals:
            pro_dict = dict(pro)
            pros_list.append(pro_dict)

        return jsonify({
            "success": True,
            "professionals": pros_list,
            "total": len(pros_list)
        })
    except Exception as e:
        print(f"Error en get_professionals_api: {e}")
        return jsonify({"status": "error", "message": "Error interno del servidor"}), 500
    finally:
        if conn:
            conn.close()


@admin_bp.route('/api/admin/professional/<int:pro_id>/status', methods=['POST'])
@rate_limit.check_rate_limit(limit=100, window=60)
@admin_required
def update_pro_status(pro_id):
    data = request.json
    new_status = data.get('status')

    if new_status not in ['approved', 'rejected']:
        return jsonify({"status": "error", "message": "Estado no válido"}), 400

    conn = None
    try:
        conn = models.get_db_connection()
        pro = conn.execute('SELECT name FROM professionals WHERE id = ?', (pro_id,)).fetchone()

        if pro:
            conn.execute('UPDATE professionals SET status = ? WHERE id = ?', (new_status, pro_id))
            conn.commit()

            action = "Aprobación" if new_status == 'approved' else "Rechazo"
            utils.log_action(action, pro['name'], session)
            return jsonify({"status": "success", "message": f"Profesional {action.lower()} correctamente"})

        return jsonify({"error": "Profesional no encontrado"}), 404
    finally:
        if conn:
            conn.close()


@admin_bp.route('/api/admin/stats')
@admin_required
def admin_stats():
    conn = None
    try:
        conn = models.get_db_connection()

        total_leads = conn.execute('SELECT COUNT(*) FROM leads').fetchone()[0]
        leads_by_type = conn.execute(
            'SELECT type, COUNT(*) as count FROM leads GROUP BY type ORDER BY count DESC'
        ).fetchall()
        leads_by_zone = conn.execute(
            'SELECT zone, COUNT(*) as count FROM leads GROUP BY zone ORDER BY count DESC LIMIT 5'
        ).fetchall()
        leads_by_budget = conn.execute(
            'SELECT budget, COUNT(*) as count FROM leads GROUP BY budget ORDER BY count DESC'
        ).fetchall()
        leads_by_month = conn.execute('''
            SELECT strftime('%Y-%m', timestamp) as month, COUNT(*) as count
            FROM leads
            GROUP BY month
            ORDER BY month DESC
            LIMIT 6
        ''').fetchall()
        pros_stats = conn.execute(
            'SELECT status, COUNT(*) as count FROM professionals GROUP BY status'
        ).fetchall()
        users_by_role = conn.execute(
            'SELECT role, COUNT(*) as count FROM users GROUP BY role'
        ).fetchall()
        audit_actions = conn.execute(
            'SELECT action, COUNT(*) as count FROM audit_log GROUP BY action ORDER BY count DESC'
        ).fetchall()
        pending_reports = conn.execute(
            "SELECT COUNT(*) FROM lead_reports WHERE status = 'pending'"
        ).fetchone()[0]

        return jsonify({
            'total_leads': total_leads,
            'leads_by_type': [{'label': r['type'], 'value': r['count']} for r in leads_by_type],
            'leads_by_zone': [{'label': r['zone'], 'value': r['count']} for r in leads_by_zone],
            'leads_by_budget': [{'label': r['budget'], 'value': r['count']} for r in leads_by_budget],
            'leads_by_month': [{'label': r['month'], 'value': r['count']} for r in reversed(leads_by_month)],
            'pros_stats': [{'label': r['status'], 'value': r['count']} for r in pros_stats],
            'users_by_role': [{'label': r['role'], 'value': r['count']} for r in users_by_role],
            'audit_actions': [{'label': r['action'], 'value': r['count']} for r in audit_actions],
            'pending_reports': pending_reports,
        })
    except Exception as e:
        print(f"Error en admin_stats: {e}")
        return jsonify({"error": "Error interno"}), 500
    finally:
        if conn:
            conn.close()


@admin_bp.route('/api/admin/lead/<int:lead_id>', methods=['GET'])
@admin_required
def admin_lead_detail(lead_id):
    conn = None
    try:
        conn = models.get_db_connection()
        lead = conn.execute('SELECT * FROM leads WHERE id = ?', (lead_id,)).fetchone()
        if not lead:
            return jsonify({'error': 'Lead no encontrado'}), 404

        lead_dict = dict(lead)
        lead_dict['timestamp'] = convert_to_argentina_time(lead_dict['timestamp'])

        return jsonify({
            'success': True,
            'lead': lead_dict
        })
    except Exception as e:
        print(f"Error en admin_lead_detail: {e}")
        return jsonify({'error': 'Error interno'}), 500
    finally:
        if conn:
            conn.close()


@admin_bp.route('/api/admin/reports', methods=['GET'])
@admin_required
def get_lead_reports():
    conn = None
    try:
        conn = models.get_db_connection()

        reports = conn.execute('''
            SELECT
                lr.id, lr.lead_id, lr.reason, lr.notes, lr.status,
                lr.reviewed_by, lr.reviewed_at, lr.created_at,
                u.username as reported_by_name,
                l.type as lead_type, l.zone as lead_zone,
                l.phone as lead_phone, l.budget as lead_budget,
                l.timestamp as lead_timestamp
            FROM lead_reports lr
            JOIN users u ON lr.reported_by = u.id
            LEFT JOIN leads l ON lr.lead_id = l.id
            ORDER BY lr.created_at DESC
        ''').fetchall()

        reports_list = []
        for r in reports:
            rd = dict(r)
            if rd['lead_timestamp']:
                rd['lead_timestamp'] = convert_to_argentina_time(rd['lead_timestamp'])
            rd['created_at'] = convert_to_argentina_time(rd['created_at'])
            reports_list.append(rd)

        status_counts = {}
        for r in conn.execute('SELECT status, COUNT(*) as c FROM lead_reports GROUP BY status').fetchall():
            status_counts[r['status']] = r['c']

        return jsonify({
            'success': True,
            'reports': reports_list,
            'total': len(reports_list),
            'status_counts': status_counts
        })
    except Exception as e:
        print(f"Error en get_lead_reports: {e}")
        return jsonify({'error': 'Error interno'}), 500
    finally:
        if conn:
            conn.close()


@admin_bp.route('/api/admin/telemetry', methods=['GET'])
@admin_required
def get_telemetry():
    conn = None
    try:
        conn = models.get_db_connection()

        period = request.args.get('period', '30d')
        days = {'7d': 7, '30d': 30, '90d': 90, '1y': 365}.get(period, 30)
        since_clause = f"datetime('now', '-{days} days')"

        event_counts = {}
        for row in conn.execute(
            f"SELECT event, COUNT(*) as c FROM events "
            f"WHERE ts >= {since_clause} GROUP BY event ORDER BY c DESC"
        ).fetchall():
            event_counts[row['event']] = row['c']

        wa_clicks = event_counts.get('wa_button_clicked', 0)
        wa_opens = event_counts.get('wa_link_generated', 0)
        wa_invalid = event_counts.get('wa_invalid_number', 0)
        sms_fallbacks = event_counts.get('sms_fallback_used', 0)
        otp_sent = event_counts.get('otp_sent', 0)
        otp_verified = event_counts.get('otp_verified', 0)
        otp_failed = event_counts.get('otp_verify_failed', 0)
        ctr = round(100 * wa_opens / wa_clicks, 1) if wa_clicks else 0.0

        consent_by_channel = {}
        for row in conn.execute(
            f"SELECT channel, COUNT(*) as c FROM consent_log "
            f"WHERE created_at >= {since_clause} GROUP BY channel"
        ).fetchall():
            consent_by_channel[row['channel']] = row['c']

        top_pros = []
        for row in conn.execute(
            f"SELECT u.username, COUNT(*) as clicks FROM events e "
            f"JOIN users u ON e.user_id = u.id "
            f"WHERE e.event = 'wa_link_generated' AND e.ts >= {since_clause} "
            f"GROUP BY u.username ORDER BY clicks DESC LIMIT 5"
        ).fetchall():
            top_pros.append({'username': row['username'], 'clicks': row['clicks']})

        return jsonify({
            'success': True,
            'period': period,
            'event_counts': event_counts,
            'metrics': {
                'wa_button_clicks': wa_clicks,
                'wa_links_generated': wa_opens,
                'wa_invalid_numbers': wa_invalid,
                'sms_fallbacks': sms_fallbacks,
                'wa_click_through_rate_pct': ctr,
                'otp_sent': otp_sent,
                'otp_verified': otp_verified,
                'otp_failed': otp_failed,
                'otp_success_rate_pct': round(100 * otp_verified / otp_sent, 1) if otp_sent else 0.0,
            },
            'consent_by_channel': consent_by_channel,
            'top_professionals': top_pros,
        })
    except Exception as e:
        print(f"Error en get_telemetry: {e}")
        return jsonify({'error': 'Error interno'}), 500
    finally:
        if conn:
            conn.close()


@admin_bp.route('/api/admin/report/<int:report_id>/delete', methods=['POST'])
@admin_required
def delete_reported_lead(report_id):
    conn = None
    try:
        conn = models.get_db_connection()

        report = conn.execute(
            'SELECT * FROM lead_reports WHERE id = ?', (report_id,)
        ).fetchone()
        if not report:
            return jsonify({'error': 'Reporte no encontrado'}), 404

        if report['status'] == 'deleted':
            return jsonify({'error': 'El reporte ya esta eliminado'}), 400

        lead_id = report['lead_id']
        argentina_tz = pytz.timezone('America/Argentina/Buenos_Aires')
        now = datetime.now(argentina_tz).strftime('%Y-%m-%d %H:%M:%S')

        conn.execute(
            'UPDATE lead_reports SET status = ?, reviewed_by = ?, reviewed_at = ? WHERE id = ?',
            ('deleted', session.get('username'), now, report_id)
        )
        conn.commit()
        utils.log_action("Eliminacion de Lead", f"Lead ID: {lead_id} eliminado tras reporte #{report_id} por {session.get('username')}", session)

        return jsonify({
            'success': True,
            'message': 'Lead eliminado correctamente'
        })
    except Exception as e:
        print(f"Error en delete_reported_lead: {e}")
        return jsonify({'error': 'Error interno'}), 500
    finally:
        if conn:
            conn.close()


@admin_bp.route('/api/admin/report/<int:report_id>/dismiss', methods=['POST'])
@admin_required
def dismiss_report(report_id):
    conn = None
    try:
        conn = models.get_db_connection()

        report = conn.execute(
            'SELECT * FROM lead_reports WHERE id = ?', (report_id,)
        ).fetchone()
        if not report:
            return jsonify({'error': 'Reporte no encontrado'}), 404

        argentina_tz = pytz.timezone('America/Argentina/Buenos_Aires')
        now = datetime.now(argentina_tz).strftime('%Y-%m-%d %H:%M:%S')

        conn.execute(
            'UPDATE lead_reports SET status = ?, reviewed_by = ?, reviewed_at = ? WHERE id = ?',
            ('dismissed', session.get('username'), now, report_id)
        )
        conn.commit()
        utils.log_action("Reporte Descartado", f"Reporte #{report_id} descartado por {session.get('username')}", session)

        return jsonify({
            'success': True,
            'message': 'Reporte descartado'
        })
    except Exception as e:
        print(f"Error en dismiss_report: {e}")
        return jsonify({'error': 'Error interno'}), 500
    finally:
        if conn:
            conn.close()


@admin_bp.route('/api/admin/report/<int:report_id>/restore', methods=['POST'])
@admin_required
def restore_report(report_id):
    conn = None
    try:
        conn = models.get_db_connection()

        report = conn.execute(
            'SELECT * FROM lead_reports WHERE id = ?', (report_id,)
        ).fetchone()
        if not report:
            return jsonify({'error': 'Reporte no encontrado'}), 404

        if report['status'] == 'pending':
            return jsonify({'error': 'El reporte ya esta pendiente'}), 400

        conn.execute(
            'UPDATE lead_reports SET status = ?, reviewed_by = NULL, reviewed_at = NULL WHERE id = ?',
            ('pending', report_id)
        )
        conn.commit()
        utils.log_action("Reporte Restaurado", f"Reporte #{report_id} restaurado a pendiente por {session.get('username')}", session)

        return jsonify({
            'success': True,
            'message': 'Reporte restaurado correctamente'
        })
    except Exception as e:
        print(f"Error en restore_report: {e}")
        return jsonify({'error': 'Error interno'}), 500
    finally:
        if conn:
            conn.close()


@admin_bp.route('/admin/download_doc/<int:user_id>')
@admin_required
def download_professional_doc(user_id):
    from flask import current_app

    conn = None
    try:
        conn = models.get_db_connection()
        user = conn.execute('SELECT doc_path FROM users WHERE id = ?', (user_id,)).fetchone()

        if not user or not user['doc_path']:
            return "El profesional no ha subido ningún documento aún.", 404

        directory = current_app.config['UPLOAD_FOLDER']
        filename = user['doc_path']

        if not os.path.exists(os.path.join(directory, filename)):
            return f"Error: El archivo {filename} no existe en el servidor.", 404

        return send_from_directory(directory, filename, as_attachment=True)

    except Exception as e:
        print(f"Error en download_professional_doc: {e}")
        return jsonify({"error": "Error interno del servidor"}), 500
    finally:
        if conn:
            conn.close()


@admin_bp.route('/admin/usuarios')
@admin_required
def user_management_view():
    return render_template('user_management.html')


@admin_bp.route('/api/admin/users', methods=['GET'])
@admin_required
def get_all_users():
    search = request.args.get('search', '').strip()
    role_filter = request.args.get('role', '').strip()
    active_filter = request.args.get('active', '').strip()

    conn = None
    try:
        conn = models.get_db_connection()
        query = 'SELECT id, username, email, phone, role, is_active FROM users WHERE 1=1'
        params = []

        if search:
            query += ' AND (username LIKE ? OR email LIKE ?)'
            params += [f'%{search}%', f'%{search}%']

        if role_filter:
            query += ' AND role = ?'
            params.append(role_filter)

        if active_filter in ('0', '1'):
            query += ' AND is_active = ?'
            params.append(int(active_filter))

        query += ' ORDER BY is_active DESC, id ASC'
        users = conn.execute(query, params).fetchall()

        return jsonify({
            'success': True,
            'users': [dict(u) for u in users],
            'total': len(users)
        })
    except Exception as e:
        print(f"Error en get_all_users: {e}")
        return jsonify({"error": "Error interno"}), 500
    finally:
        if conn:
            conn.close()


@admin_bp.route('/api/admin/user/<int:user_id>/reset-password', methods=['POST'])
@rate_limit.check_rate_limit(limit=100, window=60)
@admin_required
def admin_reset_password(user_id):
    data = request.json
    new_password = (data.get('password') or '').strip()

    if not new_password or len(new_password) < 6:
        return jsonify({"error": "La contraseña debe tener al menos 6 caracteres."}), 400

    conn = None
    try:
        conn = models.get_db_connection()
        user = conn.execute('SELECT username, role FROM users WHERE id = ?', (user_id,)).fetchone()

        if not user:
            return jsonify({"error": "Usuario no encontrado."}), 404

        if user['role'] == 'admin' and user_id != session.get('user_id'):
            return jsonify({"error": "No se puede resetear la contraseña de otro administrador."}), 403

        conn.execute('UPDATE users SET hash = ? WHERE id = ?',
                     (generate_password_hash(new_password), user_id))
        conn.commit()
    finally:
        if conn:
            conn.close()

    utils.log_action("Reset de Contraseña", f"Usuario: {user['username']} (ID: {user_id})", session)

    return jsonify({
        "status": "success",
        "message": f"Contraseña de '{user['username']}' actualizada correctamente."
    })


@admin_bp.route('/api/admin/user/<int:user_id>/set-active', methods=['POST'])
@rate_limit.check_rate_limit(limit=100, window=60)
@admin_required
def admin_set_user_active(user_id):
    data = request.json
    new_state = data.get('is_active')

    if new_state not in (True, False):
        return jsonify({"error": "Estado inválido."}), 400

    conn = None
    try:
        conn = models.get_db_connection()
        user = conn.execute('SELECT username, role FROM users WHERE id = ?', (user_id,)).fetchone()

        if not user:
            return jsonify({"error": "Usuario no encontrado."}), 404

        if user['role'] == 'admin':
            return jsonify({"error": "No se puede dar de baja a un administrador."}), 403

        if user_id == session.get('user_id'):
            return jsonify({"error": "No podés darte de baja a vos mismo."}), 403

        conn.execute('UPDATE users SET is_active = ? WHERE id = ?', (1 if new_state else 0, user_id))
        conn.commit()
    finally:
        if conn:
            conn.close()

    action = "Reactivación de Cuenta" if new_state else "Baja de Cuenta"
    reason = (data.get('reason') or '').strip()
    message = f"Usuario '{user['username']}' {'reactivado' if new_state else 'dado de baja'} correctamente."
    log_detail = f"Usuario: {user['username']} (ID: {user_id})"
    if not new_state and reason:
        log_detail += f" — Motivo: {reason}"
    utils.log_action(action, log_detail, session)

    return jsonify({"status": "success", "message": message, "is_active": new_state})
