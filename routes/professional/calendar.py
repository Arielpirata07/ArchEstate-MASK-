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
@rate_limit.check_rate_limit(limit=60, window=60)
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
@rate_limit.check_rate_limit(limit=60, window=60)
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
@rate_limit.check_rate_limit(limit=60, window=60)
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
@rate_limit.check_rate_limit(limit=60, window=60)
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
@rate_limit.check_rate_limit(limit=60, window=60)
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


