import logging
import random
import re
import time as _time

from flask import Blueprint, flash, jsonify, redirect, render_template, request, session, url_for

logger = logging.getLogger(__name__)
from werkzeug.security import check_password_hash, generate_password_hash

import config
import models
import rate_limit
import utils
import validators
from i18n import t, get_language

auth_bp = Blueprint('auth', __name__, url_prefix='')


@auth_bp.route('/register', methods=['GET', 'POST'])
@rate_limit.check_rate_limit(limit=100, window=60)
def register():
    if request.method == 'POST':
        lang = get_language()
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        phone = request.form.get('phone', '').strip()
        password = request.form.get('password', '').strip()
        raw_role = request.form.get('role', 'client')
        license_number = request.form.get('license', '').strip()

        if not username or len(username) < 3 or len(username) > 30:
            flash(t('auth.username_length', lang), 'error')
            return redirect(url_for('auth.register'))

        if not re.match(r'^[a-zA-Z0-9_]+$', username):
            flash(t('auth.username_format', lang), 'error')
            return redirect(url_for('auth.register'))

        if not email:
            flash(t('auth.email_required', lang), 'error')
            return redirect(url_for('auth.register'))

        is_valid_email_result, email_error = validators.validate_email(email)
        if not is_valid_email_result:
            flash(email_error, 'error')
            return redirect(url_for('auth.register'))

        if not password or len(password) < 6:
            flash(t('auth.password_min_length', lang), 'error')
            return redirect(url_for('auth.register'))

        if not re.search(r'[A-Za-z]', password) or not re.search(r'[0-9]', password):
            flash(t('auth.password_format', lang), 'error')
            return redirect(url_for('auth.register'))

        if not phone:
            flash(t('auth.phone_required', lang), 'error')
            return redirect(url_for('auth.register'))
        is_valid_phone, phone_error = validators.validate_phone(phone)
        if not is_valid_phone:
            flash(phone_error, 'error')
            return redirect(url_for('auth.register'))

        if raw_role == 'admin':
            logger.warning('Intento de registro ilegal como admin por %s', username)
            flash(t('auth.admin_role_denied', lang), 'error')
            return redirect(url_for('auth.register'))

        if raw_role in ['client', 'professional']:
            role = raw_role
        else:
            role = 'client'

        if role == 'professional' and not license_number:
            flash(t('auth.license_required', lang), 'error')
            return redirect(url_for('auth.register'))

        if role == 'professional' and (len(license_number) < 3 or len(license_number) > 50):
            flash(t('auth.license_length', lang), 'error')
            return redirect(url_for('auth.register'))

        if role == 'professional' and not re.match(r'^[a-zA-Z0-9\-]+$', license_number):
            flash(t('auth.license_format', lang), 'error')
            return redirect(url_for('auth.register'))

        conn = models.get_db_connection()
        try:
            cursor = conn.execute('INSERT INTO users (username, email, hash, role, phone, phone_format_valid) VALUES (?, ?, ?, ?, ?, 1)',
                                 (username, email, generate_password_hash(password), role, phone))

            if role == 'professional':
                new_user_id = cursor.lastrowid
                conn.execute('INSERT INTO professionals (user_id, name, license, specialty, status) VALUES (?, ?, ?, ?, ?)',
                             (new_user_id, username, license_number, 'General', 'pending'))

            conn.commit()
            flash(t('auth.register_success', lang), 'success')
            return redirect(url_for('auth.login'))

        except Exception as exc:
            from services.database import is_integrity_error
            if is_integrity_error(exc):
                flash(t('auth.username_taken', lang), 'error')
            else:
                logger.exception('Error al registrar usuario')
                flash(t('auth.register_error', lang), 'error')
            return redirect(url_for('auth.register'))
        finally:
            conn.close()

    return render_template('register.html')


@auth_bp.route('/login', methods=['GET', 'POST'])
@rate_limit.check_rate_limit(limit=100, window=60)
def login():
    if request.method == 'POST':
        lang = get_language()
        username = request.form.get('username')
        password = request.form.get('password')

        conn = None
        try:
            conn = models.get_db_connection()
            user = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
        finally:
            if conn:
                conn.close()

        if user and check_password_hash(user['hash'], password):
            if not user['is_active']:
                flash(t('auth.account_disabled', lang), 'error')
                return redirect(url_for('auth.login'))

            session.clear()
            session.modified = True
            session.permanent = True
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['email'] = user['email']
            session['role'] = user['role']
            session['phone'] = user['phone'] or ''

            try:
                conn2 = models.get_db_connection()
                conn2.execute(
                    'INSERT INTO user_login_history (user_id, ip_address, user_agent) VALUES (?, ?, ?)',
                    (user['id'], request.remote_addr or '', request.user_agent.string[:255] if request.user_agent else '')
                )
                conn2.commit()
                conn2.close()
            except Exception:
                pass

            remember_response = None
            if request.form.get('remember') == 'on':
                try:
                    selector, validator, validator_hash = utils.generate_remember_token()
                    conn3 = models.get_db_connection()
                    conn3.execute(
                        'INSERT INTO remember_tokens (user_id, selector, validator_hash, expires_at, ip_address, user_agent) '
                        'VALUES (?, ?, ?, ?, ?, ?)',
                        (
                            user['id'],
                            selector,
                            validator_hash,
                            utils.remember_expires_at().isoformat(),
                            request.remote_addr or '',
                            request.user_agent.string[:255] if request.user_agent else '',
                        )
                    )
                    conn3.commit()
                    conn3.close()
                    remember_response = redirect(url_for(
                        'admin.admin_view' if user['role'] == 'admin' else
                        'professional.professional_view' if user['role'] == 'professional' else
                        'client.user_view'
                    ))
                    remember_response.set_cookie(
                        config.REMEMBER_COOKIE_NAME,
                        f'{selector}:{validator}',
                        max_age=utils.remember_cookie_max_age(),
                        httponly=True,
                        secure=config.REMEMBER_COOKIE_SECURE,
                        samesite='Lax',
                        path='/',
                    )
                    utils.log_action(
                        "Remember me activado",
                        f"user_id={user['id']}, selector={selector[:8]}...",
                        session
                    )
                except Exception:
                    logger.exception('Error al crear remember token')
                    remember_response = None

            if user['role'] == 'admin':
                target = url_for('admin.admin_view')
            elif user['role'] == 'professional':
                target = url_for('professional.professional_view')
            else:
                target = url_for('client.user_view')

            if remember_response is not None:
                return remember_response
            return redirect(target)

        flash(t('auth.invalid_credentials', lang), 'error')
        return redirect(url_for('auth.login'))

    return render_template('login.html')


@auth_bp.route('/logout')
def logout():
    raw_cookie = request.cookies.get(config.REMEMBER_COOKIE_NAME)
    if raw_cookie and ':' in raw_cookie:
        selector = raw_cookie.split(':', 1)[0]
        if selector:
            utils.revoke_remember_token(selector)
    session.clear()
    response = redirect(url_for('public.index'))
    response.delete_cookie(config.REMEMBER_COOKIE_NAME, path='/')
    return response


@auth_bp.route('/api/auth/check-username', methods=['GET'])
@rate_limit.check_rate_limit(limit=100, window=60)
def api_check_username():
    q = (request.args.get('q') or '').strip()
    if not (3 <= len(q) <= 30) or not re.match(r'^[a-zA-Z0-9_]+$', q):
        result = {"available": False, "reason": "invalid"}
    else:
        conn = None
        try:
            conn = models.get_db_connection()
            row = conn.execute('SELECT 1 FROM users WHERE username = ?', (q,)).fetchone()
            result = {"available": row is None, "reason": "ok" if row is None else "taken"}
        except Exception:
            logger.exception('Error en check-username')
            result = {"available": False, "reason": "invalid"}
        finally:
            if conn:
                conn.close()

    _time.sleep(random.uniform(0.02, 0.08))
    return jsonify(result)
