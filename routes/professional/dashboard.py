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


