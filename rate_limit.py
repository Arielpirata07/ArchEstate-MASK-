"""
Rate limiting respaldado en archivos (JSON + escritura atómica).

LIMITACIÓN MULTI-WORKER: con gunicorn `--workers N` cada worker tiene su propio
`_rate_lock` en memoria, por lo que las escrituras al archivo compartido pueden
entrar en carrera y el límite efectivo se multiplica por N. Aceptable para el
despliegue actual; pendiente migrar a Redis (Render KV) cuando esté disponible.
"""

import json
import os
import tempfile
import threading
import time
from functools import wraps

from flask import jsonify, render_template, request


_rate_lock = threading.Lock()
_rate_file = os.path.join(tempfile.gettempdir(), 'archestate_rate_limits.json')


def _load_store():
    try:
        with open(_rate_file, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _save_store(store):
    dir_name = os.path.dirname(_rate_file)
    fd, tmp_path = tempfile.mkstemp(dir=dir_name, suffix='.json')
    try:
        with os.fdopen(fd, 'w') as f:
            json.dump(store, f)
        os.replace(tmp_path, _rate_file)
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass


def get_client_ip():
    if request.headers.get('X-Forwarded-For'):
        return request.headers.get('X-Forwarded-For').split(',')[0].strip()
    return request.remote_addr or '127.0.0.1'


def _rate_limit_html_response():
    """Retorna la página de error 429 renderizada (i18n + estilos consistentes)."""
    return render_template('errors/429.html'), 429


def check_rate_limit(limit=10, window=60):
    """
    Decorador para aplicar rate limiting con store persistente entre workers.
    limit: número máximo de requests permitidos
    window: ventana de tiempo en segundos
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            client_ip = get_client_ip()
            current_time = time.time()

            with _rate_lock:
                store = _load_store()
                requests = store.get(client_ip, [])
                requests = [t for t in requests if current_time - t < window]
                store[client_ip] = requests

                if len(requests) >= limit:
                    _save_store(store)
                    accept = request.headers.get('Accept', '')
                    if 'application/json' in accept or request.is_json:
                        return jsonify({
                            "status": "error",
                            "message": "Demasiadas solicitudes. Espera unos minutos antes de intentar nuevamente.",
                            "retry_after": int(window - (current_time - (requests[0] if requests else current_time)))
                        }), 429
                    else:
                        html, status = _rate_limit_html_response()
                        return html, status

                requests.append(current_time)
                store[client_ip] = requests
                _save_store(store)

            return f(*args, **kwargs)
        return decorated_function
    return decorator


def add_rate_limit_headers(response, limit=10, window=60):
    """Agrega headers de RateLimit a la respuesta"""
    client_ip = get_client_ip()
    current_time = time.time()

    with _rate_lock:
        store = _load_store()
        if client_ip in store:
            requests = [t for t in store[client_ip] if current_time - t < window]
            remaining = max(0, limit - len(requests))
        else:
            remaining = limit

    response.headers['X-RateLimit-Limit'] = str(limit)
    response.headers['X-RateLimit-Remaining'] = str(remaining)
    response.headers['X-RateLimit-Reset'] = str(int(current_time + window))
    return response