# noodle --queries-> database (sql,leads)
# noodle --notifies-> services (async,notifications)
# noodle --renders-> templates (html,user)
import logging

from flask import Blueprint, flash, jsonify, redirect, render_template, request, session, url_for

import models
import rate_limit
import utils
import validators
from decorators import login_required
from i18n import t, get_language

logger = logging.getLogger(__name__)

client_bp = Blueprint('client', __name__, url_prefix='')


@client_bp.route('/usuario')
@login_required
def user_view():
    lang = get_language()
    conn = None
    try:
        conn = models.get_db_connection()
        user = conn.execute('SELECT id, role, phone_verified, email FROM users WHERE id = ?', (session['user_id'],)).fetchone()
        lead_count = conn.execute('SELECT COUNT(*) FROM leads WHERE user_id = ?', (session['user_id'],)).fetchone()[0]
    finally:
        if conn:
            conn.close()

    if user and user['role'] == 'professional':
        flash(t('client.professional_denied', lang), 'error')
        return redirect(url_for('public.index'))

    user_dict = dict(user) if user else None

    if user_dict and not user_dict.get('email'):
        conn2 = None
        try:
            conn2 = models.get_db_connection()
            last_lead = conn2.execute(
                'SELECT email FROM leads WHERE user_id = ? ORDER BY id DESC LIMIT 1',
                (session['user_id'],)
            ).fetchone()
            if last_lead and last_lead['email']:
                user_dict['email'] = last_lead['email']
        finally:
            if conn2:
                conn2.close()

    if user_dict and user_dict.get('email'):
        session['email'] = user_dict['email']

    return render_template('user.html', is_first_lead=lead_count == 0, user=user_dict)


def _reject(error):
    logger.warning('submit_lead 400: %s', error)
    return jsonify({'success': False, 'error': error}), 400


@client_bp.route('/api/submit', methods=['POST'])
@login_required
@rate_limit.check_rate_limit(limit=100, window=60)
def submit_lead():
    lang = get_language()
    data = request.json or {}
    user_id = session.get('user_id')

    if not user_id:
        return jsonify({
            "success": False,
            "error": t('client.auth_required', lang)
        }), 401

    # Clave de idempotencia: el frontend genera un UUID por formulario y lo
    # reenvía en reintentos. Mismo (key, user) → no se inserta otro lead.
    idem_key = (request.headers.get('X-Idempotency-Key') or data.get('idempotency_key') or '').strip()[:64]
    if idem_key and not all(c.isalnum() or c in ('-', '_') for c in idem_key):
        idem_key = ''

    conn = None
    try:
        conn = models.get_db_connection()
        user = conn.execute('SELECT id, username FROM users WHERE id = ?', (user_id,)).fetchone()

        if not user:
            return jsonify({"success": False, "error": t('client.invalid_session', lang)}), 401

        if idem_key:
            # INSERT OR IGNORE es atómico: si dos requests concurrentes traen
            # la misma key, solo uno gana; el otro ve lead_id NULL o existente
            # y retorna éxito sin insertar un lead duplicado.
            conn.execute(
                'INSERT OR IGNORE INTO idempotency_keys (key, user_id, lead_id) VALUES (?, ?, NULL)',
                (idem_key, user_id)
            )
            # Poda: placeholders huérfanos (validación fallida) >1h y keys >30d.
            from datetime import datetime, timedelta, timezone
            _now = datetime.now(timezone.utc)
            conn.execute(
                'DELETE FROM idempotency_keys WHERE created_at < ?'
                ' OR (lead_id IS NULL AND created_at < ?)',
                ((_now - timedelta(days=30)).strftime('%Y-%m-%d %H:%M:%S'),
                 (_now - timedelta(hours=1)).strftime('%Y-%m-%d %H:%M:%S'))
            )
            conn.commit()
            existing = conn.execute(
                'SELECT lead_id FROM idempotency_keys WHERE key = ? AND user_id = ?',
                (idem_key, user_id)
            ).fetchone()
            if existing and existing['lead_id']:
                return jsonify({
                    "success": True,
                    "message": t('client.lead_submitted', lang),
                    "lead_id": existing['lead_id'],
                    "deduplicated": True
                })

        email = session.get('email') or data.get('email', '')
        is_valid, error = validators.validate_email(email)
        if not is_valid:
            return _reject(error)

        phone = data.get('phone', '').strip()

        phone_format_valid = 0
        if session.get('role') != 'admin':
            if not phone:
                return _reject(t('client.phone_required', lang))
            is_valid, error = validators.validate_phone(phone)
            if not is_valid:
                return _reject(error)
            phone_format_valid = 1

        budget = data.get('budget')
        if budget:
            is_valid, error = validators.validate_budget(budget)
            if not is_valid:
                return _reject(error)

        zone = data.get('zone')
        if zone:
            is_valid, error = validators.validate_zone(zone)
            if not is_valid:
                return _reject(error)

        lead_type = data.get('type')
        if not lead_type:
            return _reject(t('client.operation_type_required', lang))

        zone = data.get('zone')
        if not zone:
            return _reject(t('client.zone_required', lang))

        budget = data.get('budget')
        if not budget:
            return _reject(t('client.budget_required', lang))

        property_type = data.get('property_type', 'departamento')
        valid_property_types = models.get_form_options_by_category('property_type')
        if property_type not in valid_property_types:
            return _reject(t('client.invalid_property_type', lang))

        valid_currencies = models.get_form_options_by_category('currency')
        currency = data.get('currency', 'ARG')
        if currency not in valid_currencies:
            return _reject(t('client.invalid_currency', lang))

        valid_lead_types = models.get_form_options_by_category('operation_type')
        if lead_type not in valid_lead_types:
            return _reject(t('client.invalid_operation_type', lang))

        try:
            land_area = int(data.get('land_area') or 0)
            built_area = int(data.get('built_area') or 0)
        except (ValueError, TypeError):
            land_area = 0
            built_area = 0

        if property_type == 'casa' and built_area > land_area:
            return _reject(t('client.built_area_exceeds_land', lang))

        province = data.get('province', '')
        country = data.get('country', '')

        valid_countries = models.get_form_options_by_category('country')
        if country and country not in valid_countries:
            return _reject(t('client.invalid_country', lang))

        cursor = conn.execute('''
            INSERT INTO leads (
                type, property_type, zone, province, budget, currency,
                phone, email, user_id, floor_block, usable_m2, elevator,
                land_area, built_area, pool, architectural_style,
                bedrooms, bathrooms, total_area, amenities,
                ambientes, parking, orientation, property_condition, property_age,
                phone_format_valid, community_pool, additional_features, country
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            data.get('type'),
            property_type,
            zone,
            province,
            budget,
            currency,
            data.get('phone'),
            email,
            user_id,
            data.get('floor_block', ''),
            data.get('usable_m2', 0),
            data.get('elevator', ''),
            data.get('land_area', 0),
            data.get('built_area', 0),
            data.get('pool', ''),
            data.get('architectural_style', ''),
            data.get('bedrooms', 0),
            data.get('bathrooms', 0),
            data.get('total_area', 0),
            data.get('amenities', ''),
            data.get('ambientes', 0),
            data.get('parking', ''),
            data.get('orientation', ''),
            data.get('property_condition', ''),
            data.get('property_age', ''),
            phone_format_valid,
            data.get('community_pool', ''),
            data.get('additional_features', ''),
            country,
        ))
        conn.commit()

        if idem_key:
            # Solo el primer request que complete marca la key (UPDATE
            # condicional atómico). Si otro request concurrente con la misma
            # key terminó antes, se elimina el lead duplicado recién creado
            # y se retorna el lead ganador sin notificar de nuevo.
            claimed = conn.execute(
                'UPDATE idempotency_keys SET lead_id = ? WHERE key = ? AND user_id = ? AND lead_id IS NULL',
                (cursor.lastrowid, idem_key, user_id)
            )
            if claimed.rowcount == 0:
                dup_id = cursor.lastrowid
                conn.execute('DELETE FROM leads WHERE id = ?', (dup_id,))
                conn.commit()
                winner = conn.execute(
                    'SELECT lead_id FROM idempotency_keys WHERE key = ? AND user_id = ?',
                    (idem_key, user_id)
                ).fetchone()
                return jsonify({
                    "success": True,
                    "message": t('client.lead_submitted', lang),
                    "lead_id": winner['lead_id'] if winner else None,
                    "deduplicated": True
                })
            conn.commit()

        from services.notifications import notify_lead_created
        try:
            if cursor.lastrowid:
                import threading
                threading.Thread(target=notify_lead_created, args=(cursor.lastrowid,), daemon=True).start()
        except Exception:
            logger.exception('No se pudo lanzar hilo de notify_lead_created')

        return jsonify({
            "success": True,
            "message": t('client.lead_submitted', lang),
            "lead_id": cursor.lastrowid
        })

    except Exception as e:
        logger.exception('Error en BD')
        return jsonify({"success": False, "error": t('client.lead_error', lang)}), 500
    finally:
        if conn:
            conn.close()
