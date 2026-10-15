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


