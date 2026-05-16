from functools import wraps
from flask import session, redirect, url_for, flash

from models import get_user_by_id


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        user = get_user_by_id(session['user_id'])
        if not user or user['role'] != 'admin':
            flash('Acceso restringido: solo administradores pueden ingresar al panel de administración.', 'error')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function


def professional_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        user = get_user_by_id(session['user_id'])
        if not user or user['role'] != 'professional':
            flash('Acceso denegado. Esta sección es solo para profesionales.', 'error')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function