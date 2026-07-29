from functools import wraps
from flask import g, jsonify, request, session, redirect, url_for, flash

from models import get_user_by_id


def _get_current_user():
    """Get user from g (set by middleware) or fallback to DB query."""
    user = getattr(g, 'user', None)
    if user is not None:
        return user
    user_id = session.get('user_id')
    if user_id:
        return get_user_by_id(user_id)
    return None


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            if request.is_json or request.accept_mimetypes.best_match(['application/json', 'text/html']) == 'application/json':
                return jsonify({"error": "No autorizado"}), 401
            return redirect(url_for('auth.login'))
        user = _get_current_user()
        if not user or not user.get('is_active'):
            session.clear()
            flash('Tu cuenta ha sido deshabilitada. Contactá al administrador.', 'error')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('auth.login'))
        user = _get_current_user()
        if not user or not user.get('is_active'):
            session.clear()
            flash('Tu cuenta ha sido deshabilitada. Contactá al administrador.', 'error')
            return redirect(url_for('auth.login'))
        if user['role'] != 'admin':
            flash('Acceso restringido: solo administradores pueden ingresar al panel de administración.', 'error')
            return redirect(url_for('public.index'))
        return f(*args, **kwargs)
    return decorated_function


def professional_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('auth.login'))
        user = _get_current_user()
        if not user or not user.get('is_active'):
            session.clear()
            flash('Tu cuenta ha sido deshabilitada. Contactá al administrador.', 'error')
            return redirect(url_for('auth.login'))
        if user['role'] != 'professional':
            flash('Acceso denegado. Esta sección es solo para profesionales.', 'error')
            return redirect(url_for('public.index'))
        return f(*args, **kwargs)
    return decorated_function