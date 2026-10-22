from functools import wraps
from flask import g, jsonify, request, session, redirect, url_for, flash

from models import get_user_by_id
from i18n import t, get_language


def _get_current_user():
    """Get user from g (set by middleware) or fallback to DB query."""
    user = getattr(g, 'user', None)
    if user is not None:
        return user
    user_id = session.get('user_id')
    if user_id:
        return get_user_by_id(user_id)
    return None


def _wants_json():
    # Misma condición que login_required: JSON solo si se pide JSON.
    # Cliente plano (sin Accept) y navegadores siguen recibiendo redirect.
    return (request.is_json
            or request.accept_mimetypes.best_match(['application/json', 'text/html']) == 'application/json')


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            if _wants_json():
                return jsonify({'error': t('auth.unauthorized', get_language())}), 401
            return redirect(url_for('auth.login'))
        user = _get_current_user()
        if not user or not user.get('is_active'):
            session.clear()
            flash(t('auth.account_disabled', get_language()), 'error')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        lang = get_language()
        if 'user_id' not in session:
            if _wants_json():
                return jsonify({'error': t('auth.unauthorized', lang)}), 401
            return redirect(url_for('auth.login'))
        user = _get_current_user()
        if not user or not user.get('is_active'):
            session.clear()
            if _wants_json():
                return jsonify({'error': t('auth.unauthorized', lang)}), 401
            flash(t('auth.account_disabled', lang), 'error')
            return redirect(url_for('auth.login'))
        if user['role'] != 'admin':
            if _wants_json():
                return jsonify({'error': t('auth.admin_only', lang)}), 403
            flash(t('auth.admin_only', lang), 'error')
            return redirect(url_for('public.index'))
        return f(*args, **kwargs)
    return decorated_function


def professional_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        lang = get_language()
        if 'user_id' not in session:
            if _wants_json():
                return jsonify({'error': t('auth.unauthorized', lang)}), 401
            return redirect(url_for('auth.login'))
        user = _get_current_user()
        if not user or not user.get('is_active'):
            session.clear()
            if _wants_json():
                return jsonify({'error': t('auth.unauthorized', lang)}), 401
            flash(t('auth.account_disabled', lang), 'error')
            return redirect(url_for('auth.login'))
        if user['role'] != 'professional':
            if _wants_json():
                return jsonify({'error': t('auth.professional_only', lang)}), 403
            flash(t('auth.professional_only', lang), 'error')
            return redirect(url_for('public.index'))
        return f(*args, **kwargs)
    return decorated_function
