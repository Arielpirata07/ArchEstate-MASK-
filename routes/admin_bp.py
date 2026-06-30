import logging
import os

from datetime import datetime

import pytz

from flask import Blueprint, jsonify, redirect, render_template, request, send_from_directory, session, url_for

logger = logging.getLogger(__name__)
from werkzeug.security import generate_password_hash

import models
import rate_limit
import utils
from decorators import admin_required, login_required
from services.database import date_format_sql, now_sql
from utils import convert_to_argentina_time

admin_bp = Blueprint('admin', __name__, url_prefix='')


@admin_bp.route('/admin')
@admin_required
def admin_view():
    conn = None
    try:
        conn = models.get_db_connection()
        audit_logs = conn.execute('SELECT * FROM audit_log ORDER BY timestamp DESC LIMIT 200').fetchall()
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
        logger.exception('Error en get_professionals_api')
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

            from services.notifications import notify_professional_status_change
            try:
                notify_professional_status_change(pro_id, new_status)
            except Exception:
                pass

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

        period = request.args.get('period', '')
        days = None
        if period:
            try:
                days = int(period)
            except (ValueError, TypeError):
                pass

        leads_where = ''
        events_where = ''
        audit_where = ''
        if days:
            leads_where = f"WHERE timestamp >= datetime('now', '-{days} days')"
            events_where = f"AND ts >= datetime('now', '-{days} days')"
            audit_where = f"WHERE timestamp >= datetime('now', '-{days} days')"

        total_leads = conn.execute(
            f'SELECT COUNT(*) FROM leads {leads_where}'
        ).fetchone()[0]
        leads_by_type = conn.execute(
            f'SELECT type, COUNT(*) as count FROM leads {leads_where} GROUP BY type ORDER BY count DESC'
        ).fetchall()
        leads_by_zone = conn.execute(
            f'SELECT zone, COUNT(*) as count FROM leads {leads_where} GROUP BY zone ORDER BY count DESC LIMIT 5'
        ).fetchall()
        leads_by_budget = conn.execute(
            f'SELECT budget, COUNT(*) as count FROM leads {leads_where} GROUP BY budget ORDER BY count DESC'
        ).fetchall()
        leads_by_month = conn.execute(f'''
            SELECT {date_format_sql('timestamp', '%Y-%m')} as month, COUNT(*) as count
            FROM leads {leads_where}
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
            f'SELECT action, COUNT(*) as count FROM audit_log {audit_where} GROUP BY action ORDER BY count DESC'
        ).fetchall()
        pending_reports = conn.execute(
            "SELECT COUNT(*) FROM lead_reports WHERE status = 'pending'"
        ).fetchone()[0]
        phone_reveals = conn.execute(
            f"SELECT COUNT(*) FROM events WHERE event = 'phone_revealed' {events_where}"
        ).fetchone()[0]
        phone_clicks = conn.execute(
            f"SELECT COUNT(*) FROM events WHERE event = 'phone_button_clicked' {events_where}"
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
            'phone_reveals': phone_reveals,
            'phone_clicks': phone_clicks,
        })
    except Exception as e:
        logger.exception('Error en admin_stats')
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
        logger.exception('Error en admin_lead_detail')
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

        page = request.args.get('page', '1')
        per_page = request.args.get('per_page', '25')
        status_filter = request.args.get('status', '').strip()

        try:
            page = int(page)
            per_page = int(per_page)
        except (ValueError, TypeError):
            return jsonify({'error': 'page y per_page deben ser enteros'}), 400

        if page < 1:
            page = 1
        if per_page < 1 or per_page > 100:
            per_page = 25

        where_clause = ''
        params = []
        if status_filter in ('pending', 'dismissed', 'deleted'):
            where_clause = 'WHERE lr.status = ?'
            params.append(status_filter)

        total = conn.execute(
            f'SELECT COUNT(*) FROM lead_reports lr {where_clause}', params
        ).fetchone()[0]

        offset = (page - 1) * per_page

        reports = conn.execute(f'''
            SELECT
                lr.id, lr.lead_id, lr.reason, lr.notes, lr.status,
                lr.reviewed_by, lr.reviewed_at, lr.created_at,
                u.username as reported_by_name,
                l.type as lead_type, l.zone as lead_zone,
                l.phone as lead_phone, l.budget as lead_budget,
                l.currency as lead_currency, l.property_type as lead_property_type,
                l.timestamp as lead_timestamp
            FROM lead_reports lr
            JOIN users u ON lr.reported_by = u.id
            LEFT JOIN leads l ON lr.lead_id = l.id
            {where_clause}
            ORDER BY lr.created_at DESC
            LIMIT ? OFFSET ?
        ''', params + [per_page, offset]).fetchall()

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
            'total': total,
            'page': page,
            'per_page': per_page,
            'status_counts': status_counts
        })
    except Exception as e:
        logger.exception('Error en get_lead_reports')
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
        since_clause = None
        if period != '0':
            days = {'7d': 7, '30d': 30, '90d': 90, '1y': 365}.get(period, 30)
            since_clause = f"datetime('now', '-{days} days')"

        since_filter = f"AND ts >= {since_clause}" if since_clause else ""

        event_counts = {}
        for row in conn.execute(
            f"SELECT event, COUNT(*) as c FROM events "
            f"WHERE 1=1 {since_filter} GROUP BY event ORDER BY c DESC"
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

        phone_revealed = event_counts.get('phone_revealed', 0)
        phone_clicks = event_counts.get('phone_button_clicked', 0)
        tel_clicks = event_counts.get('tel_clicked', 0)
        phone_success_rate_pct = round(100 * phone_revealed / phone_clicks, 1) if phone_clicks else 0.0

        phone_daily = []
        for row in conn.execute(
            f"SELECT {date_format_sql('ts', '%Y-%m-%d')} as day, COUNT(*) as c "
            f"FROM events WHERE event = 'phone_revealed' {since_filter} "
            f"GROUP BY day ORDER BY day ASC"
        ).fetchall():
            phone_daily.append({'day': row['day'], 'count': row['c']})

        consent_since_filter = f"AND created_at >= {since_clause}" if since_clause else ""

        consent_by_channel = {}
        for row in conn.execute(
            f"SELECT channel, COUNT(*) as c FROM consent_log "
            f"WHERE 1=1 {consent_since_filter} GROUP BY channel"
        ).fetchall():
            consent_by_channel[row['channel']] = row['c']

        top_pros = []
        for row in conn.execute(
            f"SELECT u.username, COUNT(*) as clicks FROM events e "
            f"JOIN users u ON e.user_id = u.id "
            f"WHERE e.event = 'wa_link_generated' {since_filter} "
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
                'phone_revealed': phone_revealed,
                'phone_clicks': phone_clicks,
                'tel_clicks': tel_clicks,
                'phone_success_rate_pct': phone_success_rate_pct,
            },
            'phone_daily': phone_daily,
            'consent_by_channel': consent_by_channel,
            'top_professionals': top_pros,
        })
    except Exception as e:
        logger.exception('Error en get_telemetry')
        return jsonify({'error': 'Error interno'}), 500
    finally:
        if conn:
            conn.close()


@admin_bp.route('/api/admin/phone-audit', methods=['GET'])
@login_required
@admin_required
def admin_phone_audit():
    profesional = (request.args.get('profesional') or '').strip()
    evento = (request.args.get('evento') or '').strip()
    desde = (request.args.get('desde') or '').strip()
    hasta = (request.args.get('hasta') or '').strip()
    page = request.args.get('page', '1')
    per_page = request.args.get('per_page', '25')

    try:
        page = int(page)
        per_page = int(per_page)
    except (ValueError, TypeError):
        return jsonify({'error': 'page y per_page deben ser enteros'}), 400

    if page < 1:
        page = 1
    if per_page < 1 or per_page > 100:
        per_page = 25

    if desde:
        try:
            datetime.strptime(desde, '%Y-%m-%d')
        except ValueError:
            return jsonify({'error': 'desde debe tener formato YYYY-MM-DD'}), 400

    if hasta:
        try:
            datetime.strptime(hasta, '%Y-%m-%d')
        except ValueError:
            return jsonify({'error': 'hasta debe tener formato YYYY-MM-DD'}), 400

    conn = None
    try:
        conn = models.get_db_connection()

        where_clauses = ["e.event IN ('phone_revealed', 'wa_link_generated')"]
        params = []

        if profesional:
            where_clauses.append('u.username = ?')
            params.append(profesional)

        if evento in ('phone_revealed', 'wa_link_generated'):
            where_clauses.append('e.event = ?')
            params.append(evento)

        if desde:
            where_clauses.append("e.ts >= ? || ' 00:00:00'")
            params.append(desde)

        if hasta:
            where_clauses.append("e.ts <= ? || ' 23:59:59'")
            params.append(hasta)

        where_sql = ' AND '.join(where_clauses)

        total = conn.execute(
            f"SELECT COUNT(*) FROM events e "
            f"JOIN users u ON e.user_id = u.id "
            f"JOIN professionals p ON (p.user_id IS NOT NULL AND p.user_id = u.id) OR (p.user_id IS NULL AND p.name = u.username) "
            f"WHERE {where_sql}",
            params
        ).fetchone()[0]

        offset = (page - 1) * per_page

        rows = conn.execute(
            f"SELECT e.id, e.event, e.ts, "
            f"       u.username AS profesional, "
            f"       l.id AS lead_id, l.type AS lead_tipo, "
            f"       l.zone AS lead_zona, l.phone AS lead_telefono "
            f"FROM events e "
            f"JOIN users u ON e.user_id = u.id "
            f"JOIN professionals p ON (p.user_id IS NOT NULL AND p.user_id = u.id) OR (p.user_id IS NULL AND p.name = u.username) "
            f"LEFT JOIN leads l ON e.lead_id = l.id "
            f"WHERE {where_sql} "
            f"ORDER BY e.ts DESC "
            f"LIMIT ? OFFSET ?",
            params + [per_page, offset]
        ).fetchall()

        data = []
        for row in rows:
            entry = dict(row)
            if entry['ts']:
                entry['ts'] = convert_to_argentina_time(entry['ts'])
            data.append(entry)

        return jsonify({
            'success': True,
            'data': data,
            'total': total,
            'page': page,
            'per_page': per_page,
        })
    except Exception as e:
        logger.exception('Error en admin_phone_audit')
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

        from services.notifications import notify_report_deleted
        try:
            notify_report_deleted(lead_id, report['reported_by'])
        except Exception:
            pass

        return jsonify({
            'success': True,
            'message': 'Lead eliminado correctamente'
        })
    except Exception as e:
        logger.exception('Error en delete_reported_lead')
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
        logger.exception('Error en dismiss_report')
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
        logger.exception('Error en restore_report')
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
        logger.exception('Error en download_professional_doc')
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
    phone_verified_filter = request.args.get('phone_verified', '').strip()

    conn = None
    try:
        conn = models.get_db_connection()
        query = 'SELECT id, username, email, phone, phone_verified, role, is_active FROM users WHERE 1=1'
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

        if phone_verified_filter in ('0', '1'):
            query += ' AND phone_verified = ?'
            params.append(int(phone_verified_filter))

        query += ' ORDER BY is_active DESC, id ASC'
        users = conn.execute(query, params).fetchall()

        return jsonify({
            'success': True,
            'users': [dict(u) for u in users],
            'total': len(users)
        })
    except Exception:
        logger.exception('Error en get_all_users')
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
