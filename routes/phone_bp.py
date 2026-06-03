import secrets

from datetime import datetime, timedelta

from flask import Blueprint, jsonify, request, session

import config
import models
import rate_limit
import utils
import validators

phone_bp = Blueprint('phone', __name__, url_prefix='')


@phone_bp.route('/api/user/update-phone', methods=['POST'])
@rate_limit.check_rate_limit(limit=10, window=60)
def update_user_phone():
    if 'user_id' not in session:
        return jsonify({"error": "No autorizado"}), 401

    data = request.json
    phone = (data.get('phone') or '').strip()

    if not phone:
        return jsonify({"error": "El teléfono no puede estar vacío."}), 400

    is_valid, error = validators.validate_phone(phone)
    if not is_valid:
        return jsonify({"error": error}), 400

    conn = None
    try:
        conn = models.get_db_connection()
        current = conn.execute('SELECT phone, phone_verified FROM users WHERE id = ?',
                               (session['user_id'],)).fetchone()
        old_phone = current['phone'] if current else ''

        e164 = utils.normalize_phone_to_e164(phone)
        ntype = utils.classify_phone_type(e164) if e164 else ''

        old_e164 = utils.normalize_phone_to_e164(old_phone) if old_phone else ''
        invalidate_otp = bool(e164) and (old_e164 != e164)

        if invalidate_otp:
            conn.execute(
                'UPDATE users SET phone = ?, phone_e164 = ?, phone_number_type = ?, '
                'phone_format_valid = 1, phone_verified = 0, verification_code = \'\', verification_expires = NULL '
                'WHERE id = ?',
                (phone, e164, ntype, session['user_id'])
            )
            utils.log_event(user_id=session['user_id'], event='phone_changed',
                            props={'old_hash': utils.hash_phone_digits(old_phone),
                                   'new_hash': utils.hash_phone_digits(phone),
                                   'e164': bool(e164)}, conn=conn)
        else:
            conn.execute(
                'UPDATE users SET phone_e164 = ?, phone_number_type = ? WHERE id = ?',
                (e164, ntype, session['user_id'])
            )
        conn.commit()

        return jsonify({
            "status": "success",
            "message": "Teléfono actualizado correctamente." if not invalidate_otp
                       else "Teléfono actualizado. Vuelve a verificarlo.",
            "phone": phone,
            "phone_e164": e164,
            "phone_verified": 0 if invalidate_otp else (current['phone_verified'] if current else 0),
        })
    except Exception as e:
        print(f"Error en update_user_phone: {e}")
        return jsonify({"error": "Error al actualizar el teléfono."}), 500
    finally:
        if conn:
            conn.close()


@phone_bp.route('/api/phone/send-code', methods=['POST'])
@rate_limit.check_rate_limit(limit=3, window=60)
def send_verification_code():
    if 'user_id' not in session:
        return jsonify({"error": "No autorizado"}), 401

    user_id = session['user_id']
    conn = models.get_db_connection()
    try:
        user = conn.execute(
            'SELECT username, phone, phone_e164, phone_verified FROM users WHERE id = ?',
            (user_id,)
        ).fetchone()
        if not user:
            return jsonify({"error": "Usuario no encontrado"}), 404

        phone = user['phone'] or ''
        if not phone:
            return jsonify({"error": "No tenés teléfono registrado. Guardalo en tu perfil primero."}), 400

        if user['phone_verified'] == 1:
            return jsonify({"error": "El teléfono ya está verificado."}), 400

        is_valid_phone, phone_error = validators.validate_phone(phone)
        if not is_valid_phone:
            return jsonify({"error": phone_error}), 400

        phone_e164 = user['phone_e164'] or utils.normalize_phone_to_e164(phone)
        if not phone_e164:
            return jsonify({"error": "No se pudo normalizar el teléfono a E.164."}), 400

        try:
            prefs = models.get_user_preferences(user_id)
            preferred_channel = (prefs.get('preferred_channel') or 'auto').lower()
        except Exception:
            preferred_channel = 'auto'

        code = f"{secrets.randbelow(999999) + 1:06d}"
        expires = datetime.now() + timedelta(minutes=config.OTP_TTL_MINUTES)

        conn.execute(
            'UPDATE users SET verification_code = ?, verification_expires = ? WHERE id = ?',
            (code, expires.isoformat(), user_id)
        )
        conn.commit()

        from services.verifier import get_default_router
        router = get_default_router()
        result = router.send_otp(phone_e164, code, preferred_channel=preferred_channel, ttl_minutes=config.OTP_TTL_MINUTES)

        conn.execute(
            'INSERT INTO consent_log (user_id, channel, ip, user_agent) VALUES (?, ?, ?, ?)',
            (user_id, result.channel, rate_limit.get_client_ip(), request.headers.get('User-Agent', '')[:255])
        )
        conn.commit()

        utils.log_action(
            f"Envío código verificación teléfono ({result.channel})",
            f"user={user['username']}, channel={result.channel}, phone_hash={utils.hash_phone_digits(phone_e164)}",
            session,
            conn=conn
        )
        utils.log_event(user_id=user_id, event='otp_sent',
                        props={'channel': result.channel, 'preferred': preferred_channel,
                               'phone_hash': utils.hash_phone_digits(phone_e164)},
                        conn=conn)

        return jsonify({
            "status": "success" if result.ok else "error",
            "message": result.message,
            "channel": result.channel,
            "phone_e164": phone_e164,
            "deep_link": (result.meta or {}).get('deep_link') if result.ok else None,
        })
    except Exception as e:
        print(f"Error en send_verification_code: {e}")
        return jsonify({"error": "Error al enviar el código."}), 500
    finally:
        if conn:
            conn.close()


@phone_bp.route('/api/phone/verify', methods=['POST'])
@rate_limit.check_rate_limit(limit=5, window=60)
def verify_phone_code():
    if 'user_id' not in session:
        return jsonify({"error": "No autorizado"}), 401

    data = request.json
    code = (data.get('code') or '').strip()

    if not code or not code.isdigit() or len(code) != 6:
        return jsonify({"error": "Código inválido. Debe ser de 6 dígitos."}), 400

    user_id = session['user_id']
    conn = models.get_db_connection()
    try:
        user = conn.execute(
            'SELECT username, phone, phone_format_valid, verification_code, verification_expires, phone_verified FROM users WHERE id = ?',
            (user_id,)
        ).fetchone()
        if not user:
            return jsonify({"error": "Usuario no encontrado"}), 404

        if user['phone_verified'] == 1:
            return jsonify({"error": "El teléfono ya está verificado."}), 400

        if user['phone_format_valid'] != 1:
            return jsonify({"error": "El teléfono no tiene un formato válido. Actualizá tu perfil."}), 400

        stored_code = user['verification_code'] or ''
        expires_str = user['verification_expires'] or ''

        if not stored_code or not expires_str:
            return jsonify({"error": "No hay código pendiente. Solicitá uno nuevo."}), 400

        import datetime as dt_module
        try:
            expires = dt_module.datetime.fromisoformat(expires_str)
            if dt_module.datetime.now() > expires:
                utils.log_event(user_id=user_id, event='otp_expired', conn=conn)
                return jsonify({"error": "Código expirado. Solicitá uno nuevo."}), 410
        except ValueError:
            return jsonify({"error": "Error de validación. Solicitá un nuevo código."}), 400

        if code != stored_code:
            utils.log_action(
                "Intento fallido verificación teléfono",
                f"user={user['username']}, code_ingresado={code}",
                session,
                conn=conn
            )
            utils.log_event(user_id=user_id, event='otp_verify_failed', conn=conn)
            return jsonify({"error": "Código incorrecto."}), 400

        conn.execute(
            'UPDATE users SET phone_verified = 1, phone_format_valid = 1, verification_code = \'\', verification_expires = NULL WHERE id = ?',
            (user_id,)
        )
        conn.commit()

        utils.log_action(
            "Telefono verificado correctamente",
            f"user={user['username']}, phone_hash={utils.hash_phone_digits(user['phone'] or '')}",
            session,
            conn=conn
        )
        utils.log_event(user_id=user_id, event='otp_verified', conn=conn)

        return jsonify({"status": "success", "message": "Teléfono verificado correctamente."})

    except Exception as e:
        print(f"Error en verify_phone_code: {e}")
        return jsonify({"error": "Error al verificar el código."}), 500
    finally:
        if conn:
            conn.close()
