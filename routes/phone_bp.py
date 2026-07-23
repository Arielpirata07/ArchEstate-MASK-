import logging
import secrets

from datetime import datetime, timedelta, timezone
import datetime as dt_module

from flask import Blueprint, jsonify, request, session

logger = logging.getLogger(__name__)

import config
import models
import rate_limit
import utils
import validators
from decorators import login_required
from i18n import t, get_language

phone_bp = Blueprint('phone', __name__, url_prefix='')


@phone_bp.route('/api/user/update-phone', methods=['POST'])
@login_required
@rate_limit.check_rate_limit(limit=100, window=60)
def update_user_phone():
    lang = get_language()
    if 'user_id' not in session:
        return jsonify({"error": t('phone.unauthorized', lang)}), 401

    if not request.is_json:
        return jsonify({"error": t('phone.invalid_content_type', lang)}), 415

    data = request.json
    phone = (data.get('phone') or '').strip()

    if not phone:
        return jsonify({"error": t('phone.empty', lang)}), 400

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
                'UPDATE users SET phone = ?, phone_e164 = ?, phone_number_type = ? WHERE id = ?',
                (phone, e164, ntype, session['user_id'])
            )
        conn.commit()

        session['phone'] = phone

        return jsonify({
            "status": "success",
            "message": t('phone.updated', lang) if not invalidate_otp
                       else t('phone.updated_reverify', lang),
            "phone": phone,
            "phone_e164": e164,
            "phone_verified": 0 if invalidate_otp else (current['phone_verified'] if current else 0),
        })
    except Exception as e:
        logger.exception('Error en update_user_phone')
        return jsonify({"error": t('phone.update_error', lang)}), 500
    finally:
        if conn:
            conn.close()


@phone_bp.route('/api/phone/send-code', methods=['POST'])
@login_required
@rate_limit.check_rate_limit(limit=100, window=60)
def send_verification_code():
    lang = get_language()
    if 'user_id' not in session:
        return jsonify({"error": t('phone.unauthorized', lang)}), 401

    if not request.is_json:
        return jsonify({"error": t('phone.invalid_content_type', lang)}), 415

    user_id = session['user_id']
    conn = models.get_db_connection()
    try:
        user = conn.execute(
            'SELECT username, phone, phone_e164, phone_verified, phone_format_valid FROM users WHERE id = ?',
            (user_id,)
        ).fetchone()
        if not user:
            return jsonify({"error": t('phone.user_not_found', lang)}), 404

        phone = user['phone'] or ''
        if not phone:
            return jsonify({"error": t('phone.no_phone_registered', lang)}), 400

        if user['phone_verified'] == 1:
            return jsonify({"error": t('phone.already_verified', lang)}), 400

        if user['phone_format_valid'] != 1:
            is_valid_phone, phone_error = validators.validate_phone(phone)
            if not is_valid_phone:
                return jsonify({"error": phone_error}), 400

        phone_e164 = user['phone_e164'] or utils.normalize_phone_to_e164(phone)
        if not phone_e164:
            return jsonify({"error": t('phone.e164_normalize_error', lang)}), 400

        try:
            data = request.json or {}
            explicit_channel = (data.get('preferred_channel') or '').strip().lower()
            if explicit_channel in ('sms', 'whatsapp', 'auto'):
                preferred_channel = explicit_channel
            else:
                prefs = models.get_user_preferences(user_id)
                preferred_channel = (prefs.get('preferred_channel') or 'auto').lower()
        except Exception:
            preferred_channel = 'auto'

        code = f"{secrets.randbelow(999999) + 1:06d}"
        expires = datetime.now(timezone.utc) + timedelta(minutes=config.OTP_TTL_MINUTES)

        from services.verifier import get_default_router
        router = get_default_router()
        username = user['username'] if preferred_channel in ('whatsapp', 'auto') else None
        result = router.send_otp(phone_e164, code, preferred_channel=preferred_channel,
                                 ttl_minutes=config.OTP_TTL_MINUTES, username=username)

        if not result.ok:
            return jsonify({"error": result.message, "channel": result.channel}), 502

        conn.execute(
            'UPDATE users SET verification_code = ?, verification_expires = ?, failed_attempts = 0, '
            'phone_format_valid = 1, verification_channel = ? WHERE id = ?',
            (code, expires.isoformat(), result.channel, user_id)
        )

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
            "status": "success",
            "message": result.message,
            "channel": result.channel,
            "phone_e164": phone_e164,
            "deep_link": (result.meta or {}).get('deep_link'),
        })
    except Exception as e:
        logger.exception('Error en send_verification_code')
        return jsonify({"error": t('phone.send_code_error', lang)}), 500
    finally:
        if conn:
            conn.close()


@phone_bp.route('/api/phone/verify', methods=['POST'])
@login_required
@rate_limit.check_rate_limit(limit=100, window=60)
def verify_phone_code():
    lang = get_language()
    if 'user_id' not in session:
        return jsonify({"error": t('phone.unauthorized', lang)}), 401

    if not request.is_json:
        return jsonify({"error": t('phone.invalid_content_type', lang)}), 415

    data = request.json
    code = (data.get('code') or '').strip()

    if not code or not code.isdigit() or len(code) != 6:
        return jsonify({"error": t('phone.invalid_code', lang)}), 400

    user_id = session['user_id']
    conn = models.get_db_connection()
    try:
        user = conn.execute(
            'SELECT username, phone, phone_format_valid, verification_code, verification_expires, phone_verified, '
            'failed_attempts, verification_channel FROM users WHERE id = ?',
            (user_id,)
        ).fetchone()
        if not user:
            return jsonify({"error": t('phone.user_not_found', lang)}), 404

        if user['phone_verified'] == 1:
            return jsonify({"error": t('phone.already_verified', lang)}), 400

        if user['phone_format_valid'] != 1:
            return jsonify({"error": t('phone.invalid_format', lang)}), 400

        failed_attempts = user['failed_attempts'] or 0
        if failed_attempts >= config.OTP_MAX_ATTEMPTS:
            return jsonify({"error": t('phone.too_many_attempts', lang)}), 429

        stored_code = user['verification_code'] or ''
        expires_str = user['verification_expires'] or ''

        if not stored_code or not expires_str:
            return jsonify({"error": t('phone.no_pending_code', lang)}), 400

        try:
            expires = dt_module.datetime.fromisoformat(expires_str)
            now = dt_module.datetime.now(dt_module.timezone.utc) if expires.tzinfo else dt_module.datetime.now()
            if now > expires:
                utils.log_event(user_id=user_id, event='otp_expired', conn=conn)
                return jsonify({"error": t('phone.code_expired', lang)}), 410
        except ValueError:
            return jsonify({"error": t('phone.validation_error', lang)}), 400

        if not secrets.compare_digest(code, stored_code):
            new_attempts = failed_attempts + 1
            if new_attempts >= config.OTP_MAX_ATTEMPTS:
                conn.execute(
                    "UPDATE users SET failed_attempts = ?, verification_code = '', verification_expires = NULL WHERE id = ?",
                    (new_attempts, user_id)
                )
                conn.commit()
                utils.log_action(
                    "OTP bloqueado por intentos fallidos",
                    f"user={user['username']}, attempts={new_attempts}",
                    session,
                    conn=conn
                )
                utils.log_event(user_id=user_id, event='otp_locked_out',
                                props={'attempts': new_attempts}, conn=conn)
                return jsonify({"error": t('phone.code_locked', lang)}), 429
            else:
                conn.execute('UPDATE users SET failed_attempts = ? WHERE id = ?', (new_attempts, user_id))
                conn.commit()

            utils.log_action(
                "Intento fallido verificación teléfono",
                f"user={user['username']}, attempt=otp_code, attempts_left={config.OTP_MAX_ATTEMPTS - new_attempts}",
                session,
                conn=conn
            )
            utils.log_event(user_id=user_id, event='otp_verify_failed',
                            props={'attempts': new_attempts}, conn=conn)
            return jsonify({"error": t('phone.incorrect_code', lang)}), 400

        conn.execute(
            'UPDATE users SET phone_verified = 1, phone_format_valid = 1, verification_code = \'\', '
            'verification_expires = NULL, failed_attempts = 0 WHERE id = ?',
            (user_id,)
        )
        conn.commit()

        verified_channel = user['verification_channel'] or 'sms'

        utils.log_action(
            "Telefono verificado correctamente",
            f"user={user['username']}, phone_hash={utils.hash_phone_digits(user['phone'] or '')}",
            session,
            conn=conn
        )
        utils.log_event(user_id=user_id, event='otp_verified',
                        props={'channel': verified_channel}, conn=conn)

        return jsonify({"status": "success", "message": t('phone.verified', lang),
                        "channel": verified_channel})

    except Exception as e:
        logger.exception('Error en verify_phone_code')
        return jsonify({"error": t('phone.verify_error', lang)}), 500
    finally:
        if conn:
            conn.close()
