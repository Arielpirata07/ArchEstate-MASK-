from flask import Blueprint, flash, jsonify, redirect, render_template, request, session, url_for

import models
import rate_limit
import utils
import validators
from decorators import login_required

client_bp = Blueprint('client', __name__, url_prefix='')


@client_bp.route('/usuario')
@login_required
def user_view():
    conn = None
    try:
        conn = models.get_db_connection()
        user = conn.execute('SELECT role FROM users WHERE id = ?', (session['user_id'],)).fetchone()
        lead_count = conn.execute('SELECT COUNT(*) FROM leads WHERE user_id = ?', (session['user_id'],)).fetchone()[0]
    finally:
        if conn:
            conn.close()

    if user and user['role'] == 'professional':
        flash('Acceso denegado. Los profesionales no pueden acceder a esta sección.', 'error')
        return redirect(url_for('public.index'))

    return render_template('user.html', is_first_lead=lead_count == 0)


@client_bp.route('/api/submit', methods=['POST'])
@rate_limit.check_rate_limit(limit=100, window=60)
def submit_lead():
    data = request.json
    user_id = session.get('user_id')

    if not user_id:
        return jsonify({
            "status": "error",
            "message": "Debes estar registrado para enviar solicitudes."
        }), 401

    conn = None
    try:
        conn = models.get_db_connection()
        user = conn.execute('SELECT id, username FROM users WHERE id = ?', (user_id,)).fetchone()

        if not user:
            return jsonify({"status": "error", "message": "Sesión no válida"}), 401

        email = session.get('email') or data.get('email', '')
        is_valid, error = validators.validate_email(email)
        if not is_valid:
            return jsonify({"status": "error", "message": error}), 400

        phone = data.get('phone', '').strip()

        phone_format_valid = 0
        if session.get('role') != 'admin':
            if not phone:
                return jsonify({"status": "error", "message": "Teléfono es obligatorio"}), 400
            is_valid, error = validators.validate_phone(phone)
            if not is_valid:
                return jsonify({"status": "error", "message": error}), 400
            phone_format_valid = 1

        budget = data.get('budget')
        if budget:
            is_valid, error = validators.validate_budget(budget)
            if not is_valid:
                return jsonify({"status": "error", "message": error}), 400

        zone = data.get('zone')
        if zone:
            is_valid, error = validators.validate_zone(zone)
            if not is_valid:
                return jsonify({"status": "error", "message": error}), 400

        lead_type = data.get('type')
        if not lead_type:
            return jsonify({"status": "error", "message": "El tipo de operación es requerido."}), 400

        zone = data.get('zone')
        if not zone:
            return jsonify({"status": "error", "message": "La zona es requerida."}), 400

        budget = data.get('budget')
        if not budget:
            return jsonify({"status": "error", "message": "El presupuesto es requerido."}), 400

        property_type = data.get('property_type', 'departamento')
        VALID_PROPERTY_TYPES = ['departamento', 'casa', 'duplex', 'penthouse', 'local_comercial']
        if property_type not in VALID_PROPERTY_TYPES:
            return jsonify({"status": "error", "message": "Tipo de propiedad no válido."}), 400

        VALID_CURRENCIES = ['ARG', 'USD', 'EUR']
        currency = data.get('currency', 'ARG')
        if currency not in VALID_CURRENCIES:
            return jsonify({"status": "error", "message": "Moneda no válida."}), 400

        VALID_LEAD_TYPES = ['Comprar Propiedad', 'Remodelación Integral', 'Construir desde Cero']
        if lead_type not in VALID_LEAD_TYPES:
            return jsonify({"status": "error", "message": "Tipo de operación no válido."}), 400

        try:
            land_area = int(data.get('land_area') or 0)
            built_area = int(data.get('built_area') or 0)
        except (ValueError, TypeError):
            land_area = 0
            built_area = 0

        if property_type == 'casa' and built_area > land_area:
            return jsonify({"status": "error", "message": "Los metros construidos no pueden ser mayores que los metros de terreno."}), 400

        province = data.get('province', '')

        conn.execute('''
            INSERT INTO leads (
                type, property_type, zone, province, budget, currency,
                phone, email, user_id, floor_block, usable_m2, elevator,
                land_area, built_area, pool, architectural_style,
                bedrooms, bathrooms, total_area, amenities,
                ambientes, parking, orientation, property_condition, property_age,
                phone_format_valid, community_pool, additional_features
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
        ))
        conn.commit()

        return jsonify({
            "status": "success",
            "message": "Solicitud enviada con éxito. Los profesionales se contactarán contigo."
        })

    except Exception as e:
        print(f"Error en BD: {e}")
        return jsonify({"status": "error", "message": "Error al procesar la solicitud."}), 500
    finally:
        if conn:
            conn.close()
