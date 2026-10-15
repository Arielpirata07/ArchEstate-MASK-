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
    lang = get_language()
    conn = None
    try:
        conn = models.get_db_connection()

        user = conn.execute('SELECT username FROM users WHERE id = ?', (session['user_id'],)).fetchone()
        if not user:
            return jsonify({"success": False, "error": t('prof.access_denied', lang)}), 403

        professional = conn.execute('SELECT status FROM professionals WHERE name = ?', (user['username'],)).fetchone()
        if not professional or professional['status'] != 'approved':
            return jsonify({"success": False, "error": t('prof.account_pending', lang)}), 403

        my_leads = request.args.get('my_leads', '1').strip() == '1'
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
        time_range = request.args.get('time_range', '').strip()
        try:
            page = max(1, int(request.args.get('page', '1')))
        except ValueError:
            page = 1
        try:
            per_page = max(5, min(100, int(request.args.get('per_page', '25'))))
        except ValueError:
            per_page = 25
        offset = (page - 1) * per_page

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

        if my_leads:
            conds, geo_params = _get_pro_geo_filter(conn, session['user_id'])
            for c in conds:
                query += f' AND {c}'
            params.extend(geo_params)

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
                logger.debug('min_budget inválido: %r', min_budget)

        if max_budget:
            try:
                max_val = float(max_budget)
                query += " AND CAST(REPLACE(REPLACE(budget, '.', ''), ',', '') AS REAL) <= ?"
                params.append(max_val)
            except ValueError:
                logger.debug('max_budget inválido: %r', max_budget)

        if currency_filter:
            query += ' AND currency = ?'
            params.append(currency_filter)

        valid_sort_fields = ['id', 'type', 'zone', 'budget', 'timestamp', 'email']
        if sort_by not in valid_sort_fields:
            sort_by = 'timestamp'

        order = 'DESC' if sort_order.lower() == 'desc' else 'ASC'
        if order not in ('ASC', 'DESC'):
            order = 'ASC'

        if time_range:
            try:
                tr = int(time_range)
                if tr > 0:
                    query += " AND timestamp >= datetime('now', ?)"
                    params.append(f'-{tr} days')
            except ValueError:
                logger.debug('time_range inválido: %r', time_range)

        count_query = f'SELECT COUNT(*) as total FROM ({query}) AS sub'
        total = conn.execute(count_query, params).fetchone()['total']

        kpi_row = conn.execute(f'''
            SELECT
                SUM(CASE WHEN lt.seen IS NULL OR lt.seen = 0 THEN 1 ELSE 0 END) as unseen,
                SUM(CASE WHEN lt.contacted = 1 THEN 1 ELSE 0 END) as contacted
            FROM ({query}) l
            LEFT JOIN lead_tracking lt ON lt.lead_id = l.id AND lt.professional_id = ?
        ''', params + [session['user_id']]).fetchone()
        kpi_total = total
        kpi_unseen = kpi_row['unseen'] or 0
        kpi_contacted = kpi_row['contacted'] or 0

        query += f' ORDER BY {sort_by} {order}, id DESC LIMIT ? OFFSET ?'
        params.extend([per_page, offset])

        leads = conn.execute(query, params).fetchall()

        pro_row = conn.execute(
            'SELECT province FROM professionals WHERE user_id = ?', (session['user_id'],)
        ).fetchone()
        pro_province = pro_row['province'] if pro_row else ''
        coverage = models.get_professional_coverage(session['user_id'])

        leads_list = []
        for lead in leads:
            lead_dict = dict(lead)
            lead_dict['timestamp'] = convert_to_argentina_time(lead_dict['timestamp'])
            phone_raw = lead_dict.get('phone') or ''
            phone_e164 = utils.normalize_phone_to_e164(phone_raw)
            lead_dict['phone_e164'] = phone_e164
            lead_dict['phone_is_mobile'] = bool(phone_e164 and utils.is_whatsapp_capable(phone_e164))
            lead_dict['matches_coverage'] = lead_matches_coverage(lead_dict, coverage, pro_province)
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

        total_pages = max(1, (total + per_page - 1) // per_page)

        return jsonify({
            "success": True,
            "leads": leads_list,
            "total": total,
            "page": page,
            "per_page": per_page,
            "total_pages": total_pages,
            "kpi_total": kpi_total,
            "kpi_unseen": kpi_unseen,
            "kpi_contacted": kpi_contacted
        })
    except Exception as e:
        logger.exception('Error en get_leads_api')
        return jsonify({"success": False, "error": t('prof.internal_error', lang)}), 500
    finally:
        if conn:
            conn.close()


@professional_bp.route('/api/leads/filter-options')
@professional_required
def get_leads_filter_options():
    lang = get_language()
    conn = None
    try:
        conn = models.get_db_connection()
        user = conn.execute('SELECT username FROM users WHERE id = ?', (session['user_id'],)).fetchone()
        if user:
            professional = conn.execute('SELECT status FROM professionals WHERE name = ?', (user['username'],)).fetchone()
            if not professional or professional['status'] != 'approved':
                return jsonify({"success": False, "error": t('prof.approval_required', lang)}), 403
    finally:
        if conn:
            conn.close()

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


@professional_bp.route('/api/leads/panorama')
@professional_required
def get_leads_panorama():
    lang = get_language()
    conn = None
    try:
        conn = models.get_db_connection()
        _, error = _get_approved_professional(conn, session['user_id'], lang)
        if error:
            return error
        total = conn.execute('SELECT COUNT(*) AS n FROM leads').fetchone()['n']

        def top(column):
            if column not in ('zone', 'province', 'country', 'type', 'property_type'):
                raise ValueError(f'Columna no permitida en top(): {column!r}')
            return [dict(r) for r in conn.execute(
                f"SELECT {column} AS label, COUNT(*) AS value FROM leads "
                f"WHERE {column} IS NOT NULL AND {column} != '' "
                f'GROUP BY {column} ORDER BY value DESC LIMIT 8'
            ).fetchall()]

        my_total = None
        try:
            conds, geo_params = _get_pro_geo_filter(conn, session['user_id'])
            where = ' AND '.join(conds) if conds else '1=1'
            my_total = conn.execute(
                f'SELECT COUNT(*) AS n FROM leads WHERE {where}', geo_params
            ).fetchone()['n']
        except Exception:
            logger.debug('my_total falló, se omite')
        return jsonify({
            'success': True,
            'panorama': {
                'total': total,
                'my_total': my_total,
                'by_zone': top('zone'),
                'by_province': top('province'),
                'by_country': top('country'),
            }
        })
    except Exception:
        logger.exception('Error en get_leads_panorama')
        return jsonify({'success': False, 'error': t('prof.internal_error_short', lang)}), 500
    finally:
        if conn:
            conn.close()


@professional_bp.route('/api/professional/my-org')
@professional_required
def get_my_org():
    lang = get_language()
    conn = None
    try:
        conn = models.get_db_connection()
        _, error = _get_approved_professional(conn, session['user_id'], lang)
        if error:
            return error
        org = models.get_my_org(session['user_id'])
        if not org:
            return jsonify({'success': True, 'org': None, 'message': t('org.no_org', lang)})
        members = models.get_org_members(org['id'])
        return jsonify({'success': True, 'org': org, 'members': members})
    except Exception:
        logger.exception('Error en get_my_org')
        return jsonify({'success': False, 'error': t('prof.internal_error_short', lang)}), 500
    finally:
        if conn:
            conn.close()


@professional_bp.route('/api/professional/org-leads')
@professional_required
def get_org_leads():
    lang = get_language()
    conn = None
    try:
        conn = models.get_db_connection()
        _, error = _get_approved_professional(conn, session['user_id'], lang)
        if error:
            return error
        org = models.get_my_org(session['user_id'])
        if not org:
            return jsonify({'success': True, 'leads': [], 'total': 0, 'message': t('org.no_org', lang)})
        rows = conn.execute(
            'SELECT * FROM leads WHERE org_id = ? ORDER BY timestamp DESC LIMIT 100',
            (org['id'],)
        ).fetchall()
        return jsonify({'success': True, 'org_id': org['id'], 'leads': [dict(r) for r in rows], 'total': len(rows)})
    except Exception:
        logger.exception('Error en get_org_leads')
        return jsonify({'success': False, 'error': t('prof.internal_error_short', lang)}), 500
    finally:
        if conn:
            conn.close()


def _get_pro_geo_filter(conn, user_id):
    """Condiciones SQL que acotan los leads a los que 'coinciden' con la zona
    del profesional (provincia/pais de su perfil + zonas configuradas).
    Usado para el filtro 'my_leads=1'. Si el profesional pertenece a una
    organización, ve los leads de esa organización (pool compartido) — el
    matching por zona/especialidad se ignora como filtro duro para esos leads,
    pero matches_coverage se sigue calculando igual como señal informativa.
    La especialidad NO entra en este filtro duro — es solo un plus para el badge
    matches_coverage, para no ocultarle al profesional leads de su zona con otro
    tipo de propiedad."""
    pro_data = conn.execute(
        'SELECT province, country, org_id FROM professionals WHERE user_id = ?',
        (user_id,)
    ).fetchone()
    coverage = models.get_professional_coverage(user_id)

    conditions = []
    params = []

    if pro_data and pro_data['org_id']:
        conditions.append('leads.org_id = ?')
        params.append(pro_data['org_id'])
        return conditions, params

    if pro_data:
        pro_country = (pro_data['country'] or '').strip()
        pro_province = (pro_data['province'] or '').strip()
        if pro_country:
            conditions.append('country = ?')
            params.append(pro_country)
        if pro_province:
            conditions.append('province = ?')
            params.append(pro_province)

    zones = [z for z in coverage.get('zones', []) if z]
    if zones:
        or_parts = []
        or_params = []
        for z in zones:
            or_parts.append('zone LIKE ?')
            or_params.append(f'%{z}%')
        conditions.append('(' + ' OR '.join(or_parts) + ')')
        params.extend(or_params)

    return conditions, params


def _query_leads_stats(conn, user_id, my_leads, month):
    """Helper: build stats data dict. conn must be open, caller owns close."""
    where_clauses = ['1=1']
    params = []

    if my_leads:
        conds, geo_params = _get_pro_geo_filter(conn, user_id)
        where_clauses.extend(conds)
        params.extend(geo_params)

    where_sql = ' AND '.join(where_clauses)

    cur_params = params + [month]
    cur_stats = conn.execute(f'''
        SELECT
            COUNT(*) as total,
            AVG(CAST(SUBSTR(budget, 1, INSTR(budget, ' ') - 1) AS REAL)) as avg_budget
        FROM leads WHERE {where_sql} AND {date_format_sql('timestamp', '%Y-%m')} = ?
    ''', cur_params).fetchone()

    cur_year, cur_mon = month.split('-')
    mon_int = int(cur_mon)
    prev_year = str(int(cur_year) - 1) if mon_int == 1 else cur_year
    prev_mon = f'12' if mon_int == 1 else f'{mon_int - 1:02d}'
    prev_month = f'{prev_year}-{prev_mon}'
    prev_params = params + [prev_month]
    prev_stats = conn.execute(f'''
        SELECT COUNT(*) as total FROM leads
        WHERE {where_sql} AND {date_format_sql('timestamp', '%Y-%m')} = ?
    ''', prev_params).fetchone()

    pt_params = params + [month]
    by_property_type = conn.execute(f'''
        SELECT property_type, COUNT(*) as count
        FROM leads WHERE {where_sql} AND {date_format_sql('timestamp', '%Y-%m')} = ?
        GROUP BY property_type ORDER BY count DESC
    ''', pt_params).fetchall()

    z_params = params + [month]
    by_zone = conn.execute(f'''
        SELECT zone, COUNT(*) as count
        FROM leads WHERE {where_sql} AND {date_format_sql('timestamp', '%Y-%m')} = ?
        GROUP BY zone ORDER BY count DESC LIMIT 10
    ''', z_params).fetchall()

    ot_params = params + [month]
    by_operation_type = conn.execute(f'''
        SELECT type, COUNT(*) as count
        FROM leads WHERE {where_sql} AND {date_format_sql('timestamp', '%Y-%m')} = ?
        GROUP BY type ORDER BY count DESC
    ''', ot_params).fetchall()

    trend = conn.execute(f'''
        SELECT {date_format_sql('timestamp', '%Y-%m')} as month, COUNT(*) as count
        FROM leads WHERE {where_sql}
        GROUP BY month ORDER BY month DESC LIMIT 6
    ''', params).fetchall()

    active_zone_count = conn.execute(f'''
        SELECT COUNT(DISTINCT zone) as cnt
        FROM leads WHERE {where_sql} AND {date_format_sql('timestamp', '%Y-%m')} = ? AND zone != ''
    ''', params + [month]).fetchone()[0]

    return {
        'total': cur_stats['total'] or 0,
        'avg_budget': round(cur_stats['avg_budget'] or 0, 0),
        'by_property_type': [{'label': r['property_type'], 'value': r['count']} for r in by_property_type],
        'by_zone': [{'label': r['zone'], 'value': r['count']} for r in by_zone],
        'by_operation_type': [{'label': r['type'], 'value': r['count']} for r in by_operation_type],
        'trend': [{'label': r['month'], 'value': r['count']} for r in reversed(trend)],
        'previous_month': {'total': prev_stats['total'] or 0},
        'active_zones': active_zone_count,
        'month': month,
    }


@professional_bp.route('/api/leads/stats')
@professional_required
def get_leads_stats():
    lang = get_language()
    conn = None
    try:
        conn = models.get_db_connection()
        user = conn.execute('SELECT username FROM users WHERE id = ?', (session['user_id'],)).fetchone()
        if not user:
            return jsonify({"success": False, "error": t('prof.access_denied', lang)}), 403

        professional = conn.execute('SELECT status FROM professionals WHERE name = ?', (user['username'],)).fetchone()
        if not professional or professional['status'] != 'approved':
            return jsonify({"success": False, "error": t('prof.account_pending', lang)}), 403

        my_leads = request.args.get('my_leads', '1').strip() == '1'
        month = request.args.get('month', '').strip()
        if not month or not re.match(r'^\d{4}-\d{2}$', month):
            month = datetime.now().strftime('%Y-%m')

        stats = _query_leads_stats(conn, session['user_id'], my_leads, month)
        return jsonify({"success": True, "stats": stats, "month": month})
    except Exception as e:
        logger.exception('Error en get_leads_stats')
        return jsonify({"success": False, "error": t('prof.internal_error', lang)}), 500
    finally:
        if conn:
            conn.close()


@professional_bp.route('/api/leads/stats/export')
@professional_required
def export_stats_csv():
    lang = get_language()
    conn = None
    try:
        conn = models.get_db_connection()
        user = conn.execute('SELECT username FROM users WHERE id = ?', (session['user_id'],)).fetchone()
        if not user:
            return t('prof.access_denied', lang), 403

        professional = conn.execute('SELECT status FROM professionals WHERE name = ?', (user['username'],)).fetchone()
        if not professional or professional['status'] != 'approved':
            return t('prof.account_pending', lang), 403

        my_leads = request.args.get('my_leads', '1').strip() == '1'
        month = request.args.get('month', '').strip()
        if not month or not re.match(r'^\d{4}-\d{2}$', month):
            month = datetime.now().strftime('%Y-%m')

        stats = _query_leads_stats(conn, session['user_id'], my_leads, month)

        def generate():
            data = StringIO()
            writer = csv.writer(data)

            # Summary section
            writer.writerow([t('prof.export_summary', lang)])
            writer.writerow([t('prof.export_month', lang), stats.get('month', month)])
            writer.writerow(['Total Leads', stats['total']])
            writer.writerow([t('prof.export_avg_budget', lang), f"${stats['avg_budget']:,.0f}"])
            writer.writerow([t('prof.export_vs_prev_month', lang), stats['previous_month']['total']])
            writer.writerow([t('prof.export_active_zones', lang), stats['active_zones']])
            writer.writerow([])

            # Property type section
            writer.writerow([t('prof.export_property_type_section', lang)])
            writer.writerow([t('prof.export_type', lang), t('prof.export_count', lang)])
            for pt in stats['by_property_type']:
                writer.writerow([pt['label'], pt['value']])
            writer.writerow([])

            # Zone section
            writer.writerow([t('prof.export_zones_section', lang)])
            writer.writerow([t('prof.export_zone', lang), t('prof.export_count', lang)])
            for z in stats['by_zone']:
                writer.writerow([z['label'], z['value']])
            writer.writerow([])

            # Operation type section
            writer.writerow([t('prof.export_operation_type_section', lang)])
            writer.writerow([t('prof.export_operation', lang), t('prof.export_count', lang)])
            for ot in stats['by_operation_type']:
                writer.writerow([ot['label'], ot['value']])
            writer.writerow([])

            # Trend section
            writer.writerow([t('prof.export_trend_section', lang)])
            writer.writerow([t('prof.export_month', lang), 'Leads'])
            for trend in stats['trend']:
                writer.writerow([trend['label'], trend['value']])

            yield data.getvalue()
            data.seek(0)
            data.truncate(0)

        filename = f'estadisticas_{month}_{datetime.now().strftime("%Y%m%d_%H%M")}.csv'
        return Response(
            generate(),
            mimetype='text/csv',
            headers={'Content-Disposition': f'attachment; filename="{filename}"'}
        )
    except Exception as e:
        logger.exception('Error en export_stats_csv')
        return t('prof.internal_error', lang), 500
    finally:
        if conn:
            conn.close()


@professional_bp.route('/api/leads/stats/export/xlsx')
@professional_required
def export_stats_xlsx():
    lang = get_language()
    conn = None
    try:
        conn = models.get_db_connection()
        user = conn.execute('SELECT username FROM users WHERE id = ?', (session['user_id'],)).fetchone()
        if not user:
            return t('prof.access_denied', lang), 403

        professional = conn.execute('SELECT status FROM professionals WHERE name = ?', (user['username'],)).fetchone()
        if not professional or professional['status'] != 'approved':
            return t('prof.account_pending', lang), 403

        my_leads = request.args.get('my_leads', '1').strip() == '1'
        month = request.args.get('month', '').strip()
        if not month or not re.match(r'^\d{4}-\d{2}$', month):
            month = datetime.now().strftime('%Y-%m')

        stats = _query_leads_stats(conn, session['user_id'], my_leads, month)

        wb = openpyxl.Workbook()

        # Shared data font
        data_font = Font(name='Manrope', size=10, color='000410')
        label_font = Font(name='Manrope', size=10, bold=True, color='735A3A')
        title_font = Font(name='Manrope', size=10, bold=True, color='000410')

        # ─── Sheet 1: Resumen ───
        ws_resumen = wb.active
        ws_resumen.title = t('prof.export_summary_sheet', lang)
        resumen_data = [
            [t('prof.export_month', lang), stats.get('month', month)],
            ['Total Leads', stats['total']],
            [t('prof.export_avg_budget', lang), stats['avg_budget']],
            [t('prof.export_vs_prev_month', lang), stats['previous_month']['total']],
            [t('prof.export_active_zones', lang), stats['active_zones']],
        ]
        for col, h in enumerate([t('prof.export_metric', lang), t('prof.export_value', lang)], 1):
            cell = ws_resumen.cell(row=1, column=col, value=h)
        _style_header_row(ws_resumen, 2)
        ws_resumen.column_dimensions['A'].width = 28
        ws_resumen.column_dimensions['B'].width = 18

        for row_idx, row_data in enumerate(resumen_data, 2):
            for col, val in enumerate(row_data, 1):
                cell = ws_resumen.cell(row=row_idx, column=col, value=val)
                cell.font = data_font
                cell.alignment = Alignment(horizontal='center', vertical='center')
                if col == 1:
                    cell.font = label_font
            _apply_data_border(ws_resumen, row_idx, 2)

        # Separator + note rows
        note_row = len(resumen_data) + 3
        ws_resumen.cell(row=note_row, column=1, value=t('prof.export_generated_by', lang)).font = Font(
            name='Manrope', size=8, italic=True, color='A68A64'
        )

        # ─── Sheet 2: Tipo de Propiedad ───
        ws_pt = wb.create_sheet(t('prof.export_property_type_sheet', lang))
        for col, h in enumerate([t('prof.export_type', lang), t('prof.export_count', lang)], 1):
            ws_pt.cell(row=1, column=col, value=h)
        _style_header_row(ws_pt, 2)
        ws_pt.column_dimensions['A'].width = 32
        ws_pt.column_dimensions['B'].width = 14
        ws_pt.auto_filter.ref = f'A1:B{len(stats["by_property_type"]) + 1}'
        for row_idx, pt in enumerate(stats['by_property_type'], 2):
            c1 = ws_pt.cell(row=row_idx, column=1, value=pt['label'])
            c1.font = label_font
            c1.alignment = Alignment(horizontal='left', vertical='center')
            c2 = ws_pt.cell(row=row_idx, column=2, value=pt['value'])
            c2.font = data_font
            c2.alignment = Alignment(horizontal='center', vertical='center')
            _apply_data_border(ws_pt, row_idx, 2)

        # ─── Sheet 3: Zonas ───
        ws_z = wb.create_sheet(t('prof.export_zones_sheet', lang))
        for col, h in enumerate([t('prof.export_zone', lang), t('prof.export_count', lang)], 1):
            ws_z.cell(row=1, column=col, value=h)
        _style_header_row(ws_z, 2)
        ws_z.column_dimensions['A'].width = 34
        ws_z.column_dimensions['B'].width = 14
        ws_z.auto_filter.ref = f'A1:B{len(stats["by_zone"]) + 1}'
        for row_idx, z in enumerate(stats['by_zone'], 2):
            c1 = ws_z.cell(row=row_idx, column=1, value=z['label'])
            c1.font = label_font
            c1.alignment = Alignment(horizontal='left', vertical='center')
            c2 = ws_z.cell(row=row_idx, column=2, value=z['value'])
            c2.font = data_font
            c2.alignment = Alignment(horizontal='center', vertical='center')
            _apply_data_border(ws_z, row_idx, 2)

        # ─── Sheet 4: Tipo de Operación ───
        ws_ot = wb.create_sheet(t('prof.export_operation_type_sheet', lang))
        for col, h in enumerate([t('prof.export_operation', lang), t('prof.export_count', lang)], 1):
            ws_ot.cell(row=1, column=col, value=h)
        _style_header_row(ws_ot, 2)
        ws_ot.column_dimensions['A'].width = 34
        ws_ot.column_dimensions['B'].width = 14
        ws_ot.auto_filter.ref = f'A1:B{len(stats["by_operation_type"]) + 1}'
        for row_idx, ot in enumerate(stats['by_operation_type'], 2):
            c1 = ws_ot.cell(row=row_idx, column=1, value=ot['label'])
            c1.font = label_font
            c1.alignment = Alignment(horizontal='left', vertical='center')
            c2 = ws_ot.cell(row=row_idx, column=2, value=ot['value'])
            c2.font = data_font
            c2.alignment = Alignment(horizontal='center', vertical='center')
            _apply_data_border(ws_ot, row_idx, 2)

        # ─── Sheet 5: Tendencia Mensual ───
        ws_t = wb.create_sheet(t('prof.export_trend_sheet', lang))
        for col, h in enumerate([t('prof.export_month', lang), 'Leads'], 1):
            ws_t.cell(row=1, column=col, value=h)
        _style_header_row(ws_t, 2)
        ws_t.column_dimensions['A'].width = 28
        ws_t.column_dimensions['B'].width = 14
        ws_t.auto_filter.ref = f'A1:B{len(stats["trend"]) + 1}'
        for row_idx, trend in enumerate(stats['trend'], 2):
            c1 = ws_t.cell(row=row_idx, column=1, value=trend['label'])
            c1.font = label_font
            c1.alignment = Alignment(horizontal='left', vertical='center')
            c2 = ws_t.cell(row=row_idx, column=2, value=trend['value'])
            c2.font = data_font
            c2.alignment = Alignment(horizontal='center', vertical='center')
            _apply_data_border(ws_t, row_idx, 2)

        buffer = io.BytesIO()
        wb.save(buffer)
        buffer.seek(0)

        filename = f'estadisticas_{month}_{datetime.now().strftime("%Y%m%d_%H%M")}.xlsx'
        return send_file(
            buffer,
            as_attachment=True,
            download_name=filename,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
    except Exception as e:
        logger.exception('Error en export_stats_xlsx')
        return t('prof.internal_error', lang), 500
    finally:
        if conn:
            conn.close()


@professional_bp.route('/api/leads/filter-options/invalidate', methods=['POST'])
@professional_required
def invalidate_filter_cache():
    from app_setup import filter_cache
    lang = get_language()
    filter_cache.invalidate()
    return jsonify({"success": True, "message": t('prof.cache_invalidated', lang)})


@professional_bp.route('/api/leads/export')
@professional_required
def export_leads_csv():
    conn = None
    leads = []
    try:
        conn = models.get_db_connection()
        lang = get_language()
        user = conn.execute('SELECT username FROM users WHERE id = ?', (session['user_id'],)).fetchone()
        if not user:
            return t('prof.access_denied', lang), 403

        professional = conn.execute('SELECT status FROM professionals WHERE name = ?', (user['username'],)).fetchone()
        if not professional or professional['status'] != 'approved':
            return t('prof.account_pending', lang), 403

        conds, geo_params = _get_pro_geo_filter(conn, session['user_id'])
        query = 'SELECT id, type, zone, budget, currency, timestamp FROM leads WHERE 1=1'
        params = []
        for c in conds:
            query += f' AND {c}'
        params.extend(geo_params)
        query += ' ORDER BY timestamp DESC'
        leads = conn.execute(query, params).fetchall()
    finally:
        if conn:
            conn.close()

    def generate():
        data = StringIO()
        writer = csv.writer(data)
        writer.writerow(t('prof.export_csv_headers', lang).split(','))
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
        lang = get_language()
        user = conn.execute('SELECT username FROM users WHERE id = ?', (session['user_id'],)).fetchone()
        if not user:
            return t('prof.access_denied', lang), 403

        professional = conn.execute('SELECT status FROM professionals WHERE name = ?', (user['username'],)).fetchone()
        if not professional or professional['status'] != 'approved':
            return t('prof.account_pending', lang), 403

        conds, geo_params = _get_pro_geo_filter(conn, session['user_id'])
        query = 'SELECT id, type, zone, budget, currency, timestamp FROM leads WHERE 1=1'
        params = []
        for c in conds:
            query += f' AND {c}'
        params.extend(geo_params)
        query += ' ORDER BY timestamp DESC'
        leads = conn.execute(query, params).fetchall()
    finally:
        if conn:
            conn.close()

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = t('prof.export_leads_sheet', lang)

    headers = t('prof.export_leads_headers', lang).split(',')
    for col_num, header in enumerate(headers, 1):
        ws.cell(row=1, column=col_num, value=header)
    _style_header_row(ws, len(headers))

    col_widths = [10, 30, 28, 18, 12, 24]
    for i, w in enumerate(col_widths, 1):
        ws.column_dimensions[chr(64 + i)].width = w

    data_font = Font(name='Manrope', size=10, color='000410')
    data_align = Alignment(horizontal='center', vertical='center')
    date_font = Font(name='Manrope', size=10, color='A68A64')

    for row_num, lead in enumerate(leads, 2):
        timestamp_argentina = convert_to_argentina_time(lead['timestamp'])
        vals = [lead['id'], lead['type'], lead['zone'], lead['budget'], lead['currency'], timestamp_argentina]
        for col_num, val in enumerate(vals, 1):
            cell = ws.cell(row=row_num, column=col_num, value=val)
            cell.font = data_font
            cell.alignment = data_align
            if col_num == len(vals):
                cell.font = date_font
        _apply_data_border(ws, row_num, len(headers))

    ws.auto_filter.ref = f'A1:F{len(leads) + 1}'

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
    lang = get_language()
    conn = None
    try:
        conn = models.get_db_connection()
        user = conn.execute('SELECT username FROM users WHERE id = ?', (session['user_id'],)).fetchone()
        if not user:
            return t('prof.access_denied', lang), 403

        professional = conn.execute('SELECT status FROM professionals WHERE name = ?', (user['username'],)).fetchone()
        if not professional or professional['status'] != 'approved':
            return t('prof.account_pending', lang), 403

        lead = conn.execute('SELECT * FROM leads WHERE id = ?', (lead_id,)).fetchone()
    finally:
        if conn:
            conn.close()

    if not lead:
        return jsonify({"success": False, "error": t('prof.lead_not_found', lang)}), 404

    lead = dict(lead)

    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)

    midnight = (0, 4, 16)
    gold = (115, 90, 58)

    pdf.set_font('Times', 'BI', 20)
    pdf.set_text_color(*midnight)
    pdf.cell(0, 15, t('prof.pdf_title', lang), ln=True, align='C')
    pdf.ln(5)

    pdf.set_font('Helvetica', '', 10)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 8, t('prof.pdf_subtitle', lang, lead_id=lead['id']), ln=True, align='C')
    pdf.ln(10)

    def section_header(title):
        pdf.set_fill_color(*gold)
        pdf.set_text_color(255, 255, 255)
        pdf.set_font('Helvetica', 'B', 12)
        pdf.cell(0, 8, title.upper(), ln=True, fill=True)
        pdf.set_text_color(*midnight)
        pdf.set_font('Helvetica', '', 10)
        pdf.ln(2)

    section_header(t('prof.pdf_operation_type', lang))
    pdf.cell(0, 6, pdf_val(lead['type']), ln=True)

    prop_type = pdf_safe(lead.get('property_type', '')).lower()
    prop_type_label = {'departamento': 'Departamento', 'casa': 'Casa', 'duplex': 'Duplex',
                       'penthouse': 'Penthouse', 'local_comercial': 'Local Comercial'}.get(prop_type, prop_type)
    section_header(t('prof.pdf_property_type', lang))
    pdf.cell(0, 6, pdf_val(prop_type_label, t('prof.not_specified', lang)), ln=True)

    section_header(t('prof.pdf_geographic_zone', lang))
    pdf.cell(0, 6, f"{t('prof.pdf_zone_prefix', lang)}{pdf_val(lead['zone'])}", ln=True)
    pdf.cell(0, 6, f"{t('prof.pdf_province_prefix', lang)}{pdf_val(lead.get('province'), t('prof.not_specified_fem', lang))}", ln=True)

    section_header(t('prof.pdf_budget', lang))
    budget_symbol = 'USD' if lead['currency'] == 'USD' else 'EUR' if lead['currency'] == 'EUR' else '$'
    pdf.cell(0, 6, f"{budget_symbol} {pdf_val(lead['budget'])}", ln=True)

    section_header(t('prof.pdf_architectural_style', lang))
    pdf.cell(0, 6, pdf_val(lead.get('architectural_style'), t('prof.not_specified', lang)), ln=True)

    section_header(t('prof.pdf_direct_contact', lang))
    pdf.cell(0, 6, f"Email: {pdf_val(lead['email'])}", ln=True)
    pdf.cell(0, 6, f"Telefono: {pdf_val(lead['phone'])}", ln=True)

    section_header(t('prof.pdf_registered', lang))
    pdf.cell(0, 6, pdf_val(convert_to_argentina_time(lead['timestamp'])), ln=True)
    pdf.ln(5)

    section_header(t('prof.pdf_tech_specs', lang))

    pdf.set_font('Helvetica', 'B', 10)
    pdf.cell(60, 8, t('prof.pdf_rooms', lang), border=1)
    pdf.cell(0, 8, pdf_val(lead.get('ambientes')), ln=True, border=1)

    pdf.cell(60, 8, t('prof.pdf_bedrooms', lang), border=1)
    pdf.cell(0, 8, pdf_val(lead['bedrooms']), ln=True, border=1)

    pdf.cell(60, 8, t('prof.pdf_bathrooms', lang), border=1)
    pdf.cell(0, 8, pdf_val(lead['bathrooms']), ln=True, border=1)

    pdf.cell(60, 8, t('prof.pdf_parking', lang), border=1)
    pdf.cell(0, 8, pdf_val(lead.get('parking'), t('prof.not_specified', lang)), ln=True, border=1)

    pdf.cell(60, 8, t('prof.pdf_orientation', lang), border=1)
    pdf.cell(0, 8, pdf_val(lead.get('orientation'), t('prof.not_specified_fem', lang)), ln=True, border=1)

    pdf.ln(2)

    pdf.cell(60, 8, t('prof.pdf_usable_m2', lang), border=1)
    pdf.cell(0, 8, f"{pdf_val(lead.get('usable_m2'))} m2" if lead.get('usable_m2') else '-', ln=True, border=1)

    pdf.cell(60, 8, t('prof.pdf_total_area', lang), border=1)
    pdf.cell(0, 8, f"{pdf_val(lead.get('total_area'))} m2" if lead.get('total_area') else '-', ln=True, border=1)

    pdf.cell(60, 8, t('prof.pdf_land_area', lang), border=1)
    pdf.cell(0, 8, f"{pdf_val(lead.get('land_area'))} m2" if lead.get('land_area') else '-', ln=True, border=1)

    pdf.cell(60, 8, t('prof.pdf_built_area', lang), border=1)
    pdf.cell(0, 8, f"{pdf_val(lead.get('built_area'))} m2" if lead.get('built_area') else '-', ln=True, border=1)

    pdf.ln(5)

    section_header(t('prof.pdf_condition_age', lang))
    pdf.set_font('Helvetica', 'B', 10)
    pdf.cell(60, 8, t('prof.pdf_condition', lang), border=1)
    pdf.cell(0, 8, pdf_val(lead.get('property_condition'), t('prof.not_specified', lang)), ln=True, border=1)

    pdf.cell(60, 8, t('prof.pdf_age', lang), border=1)
    pdf.cell(0, 8, pdf_val(lead.get('property_age'), t('prof.not_specified_fem', lang)), ln=True, border=1)

    pdf.ln(5)

    section_header(t('prof.pdf_amenities', lang))
    amenities = lead.get('amenities', '')
    if amenities and str(amenities).strip():
        for amenity in pdf_safe(amenities).split(','):
            stripped = amenity.strip()
            if stripped:
                pdf.cell(0, 6, f"- {stripped}", ln=True)
    else:
        pdf.cell(0, 6, t('prof.not_specified_fem_pl', lang), ln=True)

    section_header(t('prof.pdf_property_details', lang))
    if prop_type == 'departamento':
        pdf.cell(0, 6, f"{t('prof.pdf_floor_block', lang)}{pdf_val(lead.get('floor_block'), t('prof.not_specified', lang))}", ln=True)
    pdf.cell(0, 6, f"{t('prof.pdf_pool', lang)}{pdf_val(lead.get('pool'), t('prof.not_specified_fem', lang))}", ln=True)
    pdf.cell(0, 6, f"{t('prof.pdf_elevator', lang)}{pdf_val(lead.get('elevator'), t('prof.not_specified', lang))}", ln=True)

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

        if new_value:
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


def _get_approved_professional(conn, user_id, lang):
    '''Devuelve (username, None) si el profesional está aprobado, o (None, response_403).'''
    user = conn.execute('SELECT username FROM users WHERE id = ?', (user_id,)).fetchone()
    if not user:
        return None, (jsonify({'success': False, 'error': t('prof.access_denied', lang)}), 403)
    professional = conn.execute(
        'SELECT status FROM professionals WHERE name = ?', (user['username'],)
    ).fetchone()
    if not professional or professional['status'] != 'approved':
        return None, (jsonify({'success': False, 'error': t('prof.account_pending', lang)}), 403)
    return user['username'], None


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
        now = _dt.now()
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
        moved = 0
        for lid in lead_ids:
            if conn.execute('SELECT id FROM leads WHERE id = ?', (lid,)).fetchone():
                if models.move_lead_stage(session['user_id'], lid, to_stage, now):
                    moved += 1
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


def _dashboard_leads_where(conn, user_id, my_leads):
    '''Devuelve (where_sql, params) sobre la tabla leads para el dashboard.'''
    where = '1=1'
    params = []
    if my_leads:
        conds, geo_params = _get_pro_geo_filter(conn, user_id)
        for c in conds:
            where += f' AND {c}'
        params.extend(geo_params)
    return where, params


def _valid_cal_date(value):
    import re as _re
    from datetime import datetime as _dt
    if not value or not _re.match(r'^\d{4}-\d{2}-\d{2}$', value):
        return False
    try:
        _dt.strptime(value, '%Y-%m-%d')
        return True
    except ValueError:
        return False


def _valid_cal_time(value):
    import re as _re
    return not value or bool(_re.match(r'^\d{2}:\d{2}$', value))


@professional_bp.route('/api/calendar/events')
@professional_required
def calendar_list_events():
    lang = get_language()
    conn = None
    try:
        conn = models.get_db_connection()
        _, error = _get_approved_professional(conn, session['user_id'], lang)
        if error:
            return error
        import calendar as _cal
        from datetime import date as _date
        month = request.args.get('month', '').strip()
        start = request.args.get('start', '').strip()
        end = request.args.get('end', '').strip()
        if start or end:
            if (start and not _valid_cal_date(start)) or (end and not _valid_cal_date(end)):
                return jsonify({'success': False, 'error': t('cal.invalid_date', lang)}), 400
        else:
            if month and not re.match(r'^\d{4}-\d{2}$', month):
                return jsonify({'success': False, 'error': t('cal.invalid_date', lang)}), 400
            if not month:
                month = _date.today().strftime('%Y-%m')
            year, mon = int(month[:4]), int(month[5:7])
            if mon < 1 or mon > 12:
                return jsonify({'success': False, 'error': t('cal.invalid_date', lang)}), 400
            last_day = _cal.monthrange(year, mon)[1]
            start, end = f'{month}-01', f'{month}-{last_day:02d}'
        events = models.get_calendar_events(session['user_id'], start, end)
        return jsonify({'success': True, 'events': events, 'start': start, 'end': end})
    except Exception:
        logger.exception('Error en calendar_list_events')
        return jsonify({'success': False, 'error': t('prof.internal_error_short', lang)}), 500
    finally:
        if conn:
            conn.close()


@professional_bp.route('/api/calendar/events', methods=['POST'])
@professional_required
def calendar_create_event():
    lang = get_language()
    conn = None
    try:
        conn = models.get_db_connection()
        _, error = _get_approved_professional(conn, session['user_id'], lang)
        if error:
            return error
        data = request.get_json(silent=True) or {}
        title = (data.get('title') or '').strip()
        event_date = (data.get('date') or data.get('event_date') or '').strip()
        event_type = (data.get('type') or data.get('event_type') or 'visit').strip()
        if not title:
            return jsonify({'success': False, 'error': t('cal.title_required', lang)}), 400
        if not _valid_cal_date(event_date):
            return jsonify({'success': False, 'error': t('cal.invalid_date', lang)}), 400
        if event_type not in models.CALENDAR_EVENT_TYPES:
            return jsonify({'success': False, 'error': t('cal.invalid_type', lang)}), 400
        start_time = (data.get('start_time') or '').strip()
        end_time = (data.get('end_time') or '').strip()
        if not _valid_cal_time(start_time) or not _valid_cal_time(end_time):
            return jsonify({'success': False, 'error': t('cal.invalid_date', lang)}), 400
        if start_time and end_time and end_time <= start_time:
            return jsonify({'success': False, 'error': t('cal.invalid_range', lang)}), 400
        lead_id = data.get('lead_id')
        if lead_id is not None:
            try:
                lead_id = int(lead_id)
            except (ValueError, TypeError):
                return jsonify({'success': False, 'error': t('cal.invalid_lead', lang)}), 400
        event_id = models.create_calendar_event(
            session['user_id'], title, event_date, event_type,
            description=(data.get('description') or '').strip()[:2000],
            start_time=start_time, end_time=end_time,
            location=(data.get('location') or '').strip()[:500],
            color=(data.get('color') or '').strip(),
            all_day=bool(data.get('all_day')), lead_id=lead_id)
        if not event_id:
            return jsonify({'success': False, 'error': t('cal.invalid_lead', lang)}), 400
        return jsonify({'success': True, 'id': event_id, 'message': t('cal.created', lang)})
    except Exception:
        logger.exception('Error en calendar_create_event')
        return jsonify({'success': False, 'error': t('prof.internal_error_short', lang)}), 500
    finally:
        if conn:
            conn.close()


@professional_bp.route('/api/calendar/events/<int:event_id>', methods=['PUT'])
@professional_required
def calendar_update_event(event_id):
    lang = get_language()
    conn = None
    try:
        conn = models.get_db_connection()
        _, error = _get_approved_professional(conn, session['user_id'], lang)
        if error:
            return error
        data = request.get_json(silent=True) or {}
        payload = {}
        for key in ('title', 'description', 'event_date', 'date', 'start_time', 'end_time',
                    'event_type', 'type', 'location', 'color', 'all_day', 'lead_id'):
            if key in data:
                payload[key] = data[key]
        if 'date' in payload and 'event_date' not in payload:
            payload['event_date'] = payload.pop('date')
        if 'type' in payload and 'event_type' not in payload:
            payload['event_type'] = payload.pop('type')
        if 'title' in payload:
            payload['title'] = (payload['title'] or '').strip()
            if not payload['title']:
                return jsonify({'success': False, 'error': t('cal.title_required', lang)}), 400
        if 'event_date' in payload and not _valid_cal_date((payload['event_date'] or '').strip()):
            return jsonify({'success': False, 'error': t('cal.invalid_date', lang)}), 400
        if 'event_type' in payload and payload['event_type'] not in models.CALENDAR_EVENT_TYPES:
            return jsonify({'success': False, 'error': t('cal.invalid_type', lang)}), 400
        for tk in ('start_time', 'end_time'):
            if tk in payload and not _valid_cal_time((payload[tk] or '').strip()):
                return jsonify({'success': False, 'error': t('cal.invalid_date', lang)}), 400
        if payload.get('start_time') and payload.get('end_time'):
            if payload['end_time'] <= payload['start_time']:
                return jsonify({'success': False, 'error': t('cal.invalid_range', lang)}), 400
        if 'lead_id' in payload and payload['lead_id'] is not None:
            try:
                payload['lead_id'] = int(payload['lead_id'])
            except (ValueError, TypeError):
                return jsonify({'success': False, 'error': t('cal.invalid_lead', lang)}), 400
        if not models.update_calendar_event(session['user_id'], event_id, payload):
            return jsonify({'success': False, 'error': t('cal.not_found', lang)}), 404
        return jsonify({'success': True, 'message': t('cal.updated', lang)})
    except Exception:
        logger.exception('Error en calendar_update_event')
        return jsonify({'success': False, 'error': t('prof.internal_error_short', lang)}), 500
    finally:
        if conn:
            conn.close()


@professional_bp.route('/api/calendar/events/<int:event_id>', methods=['DELETE'])
@professional_required
def calendar_delete_event(event_id):
    lang = get_language()
    conn = None
    try:
        conn = models.get_db_connection()
        _, error = _get_approved_professional(conn, session['user_id'], lang)
        if error:
            return error
        if not models.delete_calendar_event(session['user_id'], event_id):
            return jsonify({'success': False, 'error': t('cal.not_found', lang)}), 404
        return jsonify({'success': True, 'message': t('cal.deleted', lang)})
    except Exception:
        logger.exception('Error en calendar_delete_event')
        return jsonify({'success': False, 'error': t('prof.internal_error_short', lang)}), 500
    finally:
        if conn:
            conn.close()


@professional_bp.route('/api/calendar/events/<int:event_id>/move', methods=['POST'])
@professional_required
def calendar_move_event(event_id):
    lang = get_language()
    conn = None
    try:
        conn = models.get_db_connection()
        _, error = _get_approved_professional(conn, session['user_id'], lang)
        if error:
            return error
        data = request.get_json(silent=True) or {}
        event_date = (data.get('date') or data.get('event_date') or '').strip()
        if not _valid_cal_date(event_date):
            return jsonify({'success': False, 'error': t('cal.invalid_date', lang)}), 400
        payload = {'event_date': event_date}
        for tk in ('start_time', 'end_time'):
            if tk in data:
                if not _valid_cal_time((data[tk] or '').strip()):
                    return jsonify({'success': False, 'error': t('cal.invalid_date', lang)}), 400
                payload[tk] = (data[tk] or '').strip()
        if not models.update_calendar_event(session['user_id'], event_id, payload):
            return jsonify({'success': False, 'error': t('cal.not_found', lang)}), 404
        return jsonify({'success': True, 'message': t('cal.moved', lang)})
    except Exception:
        logger.exception('Error en calendar_move_event')
        return jsonify({'success': False, 'error': t('prof.internal_error_short', lang)}), 500
    finally:
        if conn:
            conn.close()


@professional_bp.route('/api/calendar/events/<int:event_id>/complete', methods=['POST'])
@professional_required
def calendar_complete_event(event_id):
    lang = get_language()
    conn = None
    try:
        conn = models.get_db_connection()
        _, error = _get_approved_professional(conn, session['user_id'], lang)
        if error:
            return error
        data = request.get_json(silent=True) or {}
        completed = bool(data.get('completed', True))
        if not models.complete_calendar_event(session['user_id'], event_id, completed):
            return jsonify({'success': False, 'error': t('cal.not_found', lang)}), 404
        return jsonify({'success': True, 'completed': completed})
    except Exception:
        logger.exception('Error en calendar_complete_event')
        return jsonify({'success': False, 'error': t('prof.internal_error_short', lang)}), 500
    finally:
        if conn:
            conn.close()


@professional_bp.route('/api/calendar/events/upcoming')
@professional_required
def calendar_upcoming_events():
    lang = get_language()
    conn = None
    try:
        conn = models.get_db_connection()
        _, error = _get_approved_professional(conn, session['user_id'], lang)
        if error:
            return error
        try:
            days = max(1, min(90, int(request.args.get('days', '7'))))
        except ValueError:
            days = 7
        try:
            limit = max(1, min(50, int(request.args.get('limit', '20'))))
        except ValueError:
            limit = 20
        events = models.get_upcoming_events(session['user_id'], days, limit)
        return jsonify({'success': True, 'events': events})
    except Exception:
        logger.exception('Error en calendar_upcoming_events')
        return jsonify({'success': False, 'error': t('prof.internal_error_short', lang)}), 500
    finally:
        if conn:
            conn.close()
    '''Devuelve (where_sql, params) sobre la tabla leads para el dashboard.'''
    where = '1=1'
    params = []
    if my_leads:
        conds, geo_params = _get_pro_geo_filter(conn, user_id)
        for c in conds:
            where += f' AND {c}'
        params.extend(geo_params)
    return where, params


def geo_counts_filter(conn, user_id, my_leads):
    '''Devuelve (extra_where, extra_params) para models.get_pipeline_counts().'''
    if not my_leads:
        return '', ()
    conds, geo_params = _get_pro_geo_filter(conn, user_id)
    if not conds:
        return '', ()
    return ' AND '.join(conds), tuple(geo_params)


@professional_bp.route('/api/dashboard/summary')
@professional_required
def dashboard_summary():
    lang = get_language()
    conn = None
    try:
        conn = models.get_db_connection()
        _, error = _get_approved_professional(conn, session['user_id'], lang)
        if error:
            return error
        user_id = session['user_id']
        my_leads = request.args.get('my_leads', '1').strip() == '1'
        where, params = _dashboard_leads_where(conn, user_id, my_leads)
        # En joins con alias l (leads) + lt (lead_tracking): solo leads tiene
        # country/province/zone/timestamp, solo lt tiene seen/contacted/*_at.
        where_alias = where.replace('leads.', 'l.')

        total = conn.execute(f'SELECT COUNT(*) AS n FROM leads WHERE {where}', params).fetchone()['n']
        new_today = conn.execute(
            f"SELECT COUNT(*) AS n FROM leads WHERE {where} AND date(timestamp) = date('now', 'localtime')", params
        ).fetchone()['n']
        new_this_week = conn.execute(
            f"SELECT COUNT(*) AS n FROM leads WHERE {where} AND timestamp >= datetime('now', '-7 days')", params
        ).fetchone()['n']
        prev_week = conn.execute(
            f"SELECT COUNT(*) AS n FROM leads WHERE {where} AND timestamp >= datetime('now', '-14 days') AND timestamp < datetime('now', '-7 days')",
            params
        ).fetchone()['n']

        track = conn.execute(f'''
            SELECT
                SUM(CASE WHEN lt.seen = 1 THEN 1 ELSE 0 END) AS seen,
                SUM(CASE WHEN lt.contacted = 1 THEN 1 ELSE 0 END) AS contacted
            FROM leads l LEFT JOIN lead_tracking lt
              ON lt.lead_id = l.id AND lt.professional_id = ?
            WHERE {where_alias}
        ''', [user_id] + params).fetchone()
        seen = track['seen'] or 0
        contacted = track['contacted'] or 0
        contact_rate = round(contacted / seen, 3) if seen else 0.0

        contacted_week = conn.execute(f'''
            SELECT COUNT(*) AS n FROM leads l JOIN lead_tracking lt
              ON lt.lead_id = l.id AND lt.professional_id = ?
            WHERE {where_alias} AND lt.contacted_at >= datetime('now', '-7 days')
        ''', [user_id] + params).fetchone()['n']
        contacted_prev = conn.execute(f'''
            SELECT COUNT(*) AS n FROM leads l JOIN lead_tracking lt
              ON lt.lead_id = l.id AND lt.professional_id = ?
            WHERE {where_alias}
              AND lt.contacted_at >= datetime('now', '-14 days') AND lt.contacted_at < datetime('now', '-7 days')
        ''', [user_id] + params).fetchone()['n']

        counts = models.get_pipeline_counts(user_id, *geo_counts_filter(conn, user_id, my_leads))
        closed = counts.get('closed_won', 0) + counts.get('closed_lost', 0) + counts.get('archived', 0)
        pipeline_active = max(0, total - closed)

        avg_row = conn.execute(
            f"SELECT AVG(CAST(REPLACE(REPLACE(budget, '.', ''), ',', '') AS REAL)) AS avg_b FROM leads WHERE {where}",
            params
        ).fetchone()
        avg_budget = round(avg_row['avg_b'] or 0.0, 0)

        top_zone_row = conn.execute(
            f"SELECT zone, COUNT(*) AS n FROM leads WHERE {where} AND zone != '' GROUP BY zone ORDER BY n DESC LIMIT 1",
            params
        ).fetchone()
        top_prop_row = conn.execute(
            f"SELECT property_type, COUNT(*) AS n FROM leads WHERE {where} AND property_type != '' GROUP BY property_type ORDER BY n DESC LIMIT 1",
            params
        ).fetchone()

        return jsonify({
            'success': True,
            'summary': {
                'total_leads': total,
                'new_today': new_today,
                'new_this_week': new_this_week,
                'contacted_this_week': contacted_week,
                'contact_rate': contact_rate,
                'pipeline_active': pipeline_active,
                'avg_budget': avg_budget,
                'vs_last_week': {'leads': new_this_week - prev_week, 'contacted': contacted_week - contacted_prev},
                'top_zone': top_zone_row['zone'] if top_zone_row else '',
                'top_property_type': top_prop_row['property_type'] if top_prop_row else ''
            }
        })
    except Exception:
        logger.exception('Error en dashboard_summary')
        return jsonify({'success': False, 'error': t('prof.internal_error_short', lang)}), 500
    finally:
        if conn:
            conn.close()


@professional_bp.route('/api/dashboard/trends')
@professional_required
def dashboard_trends():
    lang = get_language()
    conn = None
    try:
        conn = models.get_db_connection()
        _, error = _get_approved_professional(conn, session['user_id'], lang)
        if error:
            return error
        user_id = session['user_id']
        my_leads = request.args.get('my_leads', '1').strip() == '1'
        try:
            days = max(1, min(90, int(request.args.get('days', '30'))))
        except ValueError:
            days = 30
        where, params = _dashboard_leads_where(conn, user_id, my_leads)

        rows = conn.execute(f'''
            SELECT date(timestamp, 'localtime') AS day, COUNT(*) AS n FROM leads
            WHERE {where} AND timestamp >= datetime('now', ?)
            GROUP BY day ORDER BY day
        ''', params + [f'-{days} days']).fetchall()
        by_day = {r['day']: r['n'] for r in rows}

        from datetime import date as _date, timedelta as _td
        today = _date.today()
        trends = []
        for i in range(days - 1, -1, -1):
            day = (today - _td(days=i)).isoformat()
            trends.append({'day': day, 'count': by_day.get(day, 0)})
        return jsonify({'success': True, 'days': days, 'trends': trends})
    except Exception:
        logger.exception('Error en dashboard_trends')
        return jsonify({'success': False, 'error': t('prof.internal_error_short', lang)}), 500
    finally:
        if conn:
            conn.close()


@professional_bp.route('/api/dashboard/pipeline')
@professional_required
def dashboard_pipeline():
    lang = get_language()
    conn = None
    try:
        conn = models.get_db_connection()
        _, error = _get_approved_professional(conn, session['user_id'], lang)
        if error:
            return error
        my_leads = request.args.get('my_leads', '1').strip() == '1'
        counts = models.get_pipeline_counts(
            session['user_id'], *geo_counts_filter(conn, session['user_id'], my_leads))
        return jsonify({
            'success': True,
            'funnel': [{'stage': stage, 'count': counts.get(stage, 0)} for stage in models.PIPELINE_STAGES]
        })
    except Exception:
        logger.exception('Error en dashboard_pipeline')
        return jsonify({'success': False, 'error': t('prof.internal_error_short', lang)}), 500
    finally:
        if conn:
            conn.close()


@professional_bp.route('/api/dashboard/activity')
@professional_required
def dashboard_activity():
    lang = get_language()
    conn = None
    try:
        conn = models.get_db_connection()
        _, error = _get_approved_professional(conn, session['user_id'], lang)
        if error:
            return error
        user_id = session['user_id']
        try:
            limit = max(1, min(50, int(request.args.get('limit', '20'))))
        except ValueError:
            limit = 20

        moves = conn.execute('''
            SELECT h.from_stage, h.to_stage, h.changed_at AS at, h.lead_id, l.type AS lead_type, l.zone
            FROM lead_stage_history h JOIN leads l ON l.id = h.lead_id
            WHERE h.professional_id = ? ORDER BY h.changed_at DESC, h.id DESC LIMIT ?
        ''', (user_id, limit)).fetchall()
        tracked = conn.execute('''
            SELECT lt.seen, lt.contacted, lt.seen_at, lt.contacted_at, lt.lead_id, l.type AS lead_type, l.zone
            FROM lead_tracking lt JOIN leads l ON l.id = lt.lead_id
            WHERE lt.professional_id = ? AND (lt.seen_at IS NOT NULL OR lt.contacted_at IS NOT NULL)
            ORDER BY COALESCE(lt.contacted_at, lt.seen_at) DESC LIMIT ?
        ''', (user_id, limit)).fetchall()

        events = []
        for m in moves:
            events.append({
                'kind': 'stage_move', 'lead_id': m['lead_id'], 'from_stage': m['from_stage'],
                'to_stage': m['to_stage'], 'at': m['at'], 'lead_type': m['lead_type'], 'zone': m['zone']
            })
        contacted_stages = set(models.PIPELINE_STAGES[models.PIPELINE_STAGES.index('contacted'):])
        move_keys = {(m['lead_id'], m['to_stage'], m['at']) for m in moves
                     if m['to_stage'] in contacted_stages}
        for row in tracked:
            if row['contacted_at']:
                # El move a etapa de contacto ya setea contacted_at con el mismo
                # timestamp: no duplicar el mismo hecho en el feed.
                if not any(k[0] == row['lead_id'] and k[2] == row['contacted_at'] for k in move_keys):
                    events.append({
                        'kind': 'contacted', 'lead_id': row['lead_id'], 'from_stage': None,
                        'to_stage': None, 'at': row['contacted_at'], 'lead_type': row['lead_type'], 'zone': row['zone']
                    })
            if row['seen_at']:
                events.append({
                    'kind': 'seen', 'lead_id': row['lead_id'], 'from_stage': None,
                    'to_stage': None, 'at': row['seen_at'], 'lead_type': row['lead_type'], 'zone': row['zone']
                })
        seen_keys = set()
        deduped = []
        for e in sorted(events, key=lambda e: (e['at'] or ''), reverse=True):
            key = (e['kind'], e['lead_id'], e.get('to_stage'), e['at'])
            if key in seen_keys:
                continue
            seen_keys.add(key)
            deduped.append(e)
        return jsonify({'success': True, 'activity': deduped[:limit]})
    except Exception:
        logger.exception('Error en dashboard_activity')
        return jsonify({'success': False, 'error': t('prof.internal_error_short', lang)}), 500
    finally:
        if conn:
            conn.close()


@professional_bp.route('/api/dashboard/top-metrics')
@professional_required
def dashboard_top_metrics():
    lang = get_language()
    conn = None
    try:
        conn = models.get_db_connection()
        _, error = _get_approved_professional(conn, session['user_id'], lang)
        if error:
            return error
        user_id = session['user_id']
        my_leads = request.args.get('my_leads', '1').strip() == '1'
        where, params = _dashboard_leads_where(conn, user_id, my_leads)

        zones = conn.execute(
            f"SELECT zone AS label, COUNT(*) AS value FROM leads WHERE {where} AND zone != '' GROUP BY zone ORDER BY value DESC LIMIT 5",
            params
        ).fetchall()
        prop_types = conn.execute(
            f"SELECT property_type AS label, COUNT(*) AS value FROM leads WHERE {where} AND property_type != '' GROUP BY property_type ORDER BY value DESC LIMIT 5",
            params
        ).fetchall()
        op_types = conn.execute(
            f"SELECT type AS label, COUNT(*) AS value FROM leads WHERE {where} AND type != '' GROUP BY type ORDER BY value DESC LIMIT 5",
            params
        ).fetchall()
        return jsonify({
            'success': True,
            'top_zones': [dict(r) for r in zones],
            'top_property_types': [dict(r) for r in prop_types],
            'top_operation_types': [dict(r) for r in op_types]
        })
    except Exception:
        logger.exception('Error en dashboard_top_metrics')
        return jsonify({'success': False, 'error': t('prof.internal_error_short', lang)}), 500
    finally:
        if conn:
            conn.close()


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
