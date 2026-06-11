import uuid

from flask import g, request, session

import config
import models
import rate_limit
import utils


def security_headers(response):
    if not request.path.startswith('/static/'):
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        response.headers['Permissions-Policy'] = 'camera=(), microphone=(), geolocation=()'
    return rate_limit.add_rate_limit_headers(response)


def assign_request_id():
    g.request_id = uuid.uuid4().hex[:12]


def restore_session_from_remember_cookie():
    if session.get('user_id'):
        return None

    path = request.path or ''
    exempt_prefixes = ('/static/', '/login', '/register', '/logout', '/api/auth/', '/sitemap.xml', '/robots.txt')
    if any(path == p or path.startswith(p) for p in exempt_prefixes):
        return None

    raw_cookie = request.cookies.get(config.REMEMBER_COOKIE_NAME)
    if not raw_cookie or ':' not in raw_cookie:
        return None

    selector, _, validator = raw_cookie.partition(':')
    if not selector or not validator:
        return None

    user_id = utils.validate_remember_token(selector, validator)
    if not user_id:
        return None

    conn = None
    try:
        conn = models.get_db_connection()
        user = conn.execute(
            'SELECT id, username, email, phone, role, is_active FROM users WHERE id = ?',
            (user_id,)
        ).fetchone()
        if not user or not user['is_active']:
            utils.revoke_remember_token(selector)
            return None

        session.permanent = True
        session['user_id'] = user['id']
        session['username'] = user['username']
        session['email'] = user['email']
        session['role'] = user['role']
        session['phone'] = user['phone'] or ''
        g.restored_from_remember = True
        utils.log_event(
            user_id=user['id'], event='remember_session_restored',
            props={'selector_prefix': selector[:8]}
        )
    except Exception as e:
        print(f"Error al restaurar sesión desde remember token: {e}")
    finally:
        if conn:
            conn.close()
    return None


def inject_request_id():
    return dict(request_id=getattr(g, 'request_id', None))


def inject_theme():
    user_id = session.get('user_id')
    theme = 'light'
    if user_id:
        try:
            prefs = models.get_user_preferences(user_id)
            theme = prefs.get('theme', 'light')
        except Exception:
            pass
    return dict(user_theme=theme)


def register_middleware(app):
    app.after_request(security_headers)
    app.before_request(assign_request_id)
    app.before_request(restore_session_from_remember_cookie)
    app.context_processor(inject_request_id)
    app.context_processor(inject_theme)
