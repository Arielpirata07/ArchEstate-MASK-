"""
Rate limiting respaldado en archivos (JSON + escritura atómica).

LIMITACIÓN MULTI-WORKER: con gunicorn `--workers N` cada worker tiene su propio
`_rate_lock` en memoria, por lo que las escrituras al archivo compartido pueden
entrar en carrera y el límite efectivo se multiplica por N. Aceptable para el
despliegue actual; pendiente migrar a Redis (Render KV) cuando esté disponible.
"""

import json
import logging
import os
import tempfile
import threading
import time
from functools import wraps

from flask import jsonify, make_response, render_template, request

logger = logging.getLogger(__name__)


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
            logger.debug('No se pudo borrar tmp de rate-limit')


def get_client_ip():
    if request.headers.get('X-Forwarded-For'):
        return request.headers.get('X-Forwarded-For').split(',')[0].strip()
    return request.remote_addr or '127.0.0.1'


def _rate_limit_html_response():
    """Retorna la página de error 429 renderizada (i18n + estilos consistentes)."""
    return render_template('errors/429.html'), 429


def check_rate(key, limit, window=3600):
    """
    Sliding-window por clave arbitraria sobre el store compartido.
    Permite rate limiting por zona (usuario, IP, recurso) sin stores propios.
    """
    now = time.time()
    with _rate_lock:
        store = _load_store()
        bucket = [t for t in store.get(key, []) if now - t < window]
        if len(bucket) >= limit:
            store[key] = bucket
            _save_store(store)
            return False
        bucket.append(now)
        store[key] = bucket
        _save_store(store)
        return True


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
            # Bucket por (endpoint, IP): cada ruta decorada tiene su propio
            # limit/window. Antes la clave era solo la IP, así que tráfico de una
            # ruta alta (p. ej. /api/submit, limit=100) llenaba el bucket compartido
            # y disparaba 429 falsos en otra de límite bajo (OTP send-code, limit=5).
            bucket_key = f'{request.endpoint or request.path}:{client_ip}'

            with _rate_lock:
                store = _load_store()
                requests = store.get(bucket_key, [])
                requests = [t for t in requests if current_time - t < window]
                store[bucket_key] = requests

                if len(requests) >= limit:
                    _save_store(store)
                    retry_after = max(0, int(window - (current_time - (requests[0] if requests else current_time))))
                    rate_headers = {
                        'Retry-After': str(retry_after),
                        'X-RateLimit-Limit': str(limit),
                        'X-RateLimit-Remaining': '0',
                        'X-RateLimit-Reset': str(int(current_time + window)),
                    }
                    accept = request.headers.get('Accept', '')
                    if 'application/json' in accept or request.is_json:
                        try:
                            from i18n import t, get_language
                            error_msg = t('error.rate_limited', get_language())
                        except Exception:
                            error_msg = 'Demasiadas solicitudes. Espera unos minutos antes de intentar nuevamente.'
                        response = jsonify({
                            "success": False,
                            "error": error_msg,
                            "retry_after": retry_after
                        })
                        response.status_code = 429
                    else:
                        html, status = _rate_limit_html_response()
                        response = make_response(html, status)
                    response.headers.update(rate_headers)
                    return response

                requests.append(current_time)
                store[bucket_key] = requests
                _save_store(store)

            return f(*args, **kwargs)
        return decorated_function
    return decorator


def add_rate_limit_headers(response, limit=10, window=60):
    """Agrega headers de RateLimit a la respuesta"""
    client_ip = get_client_ip()
    current_time = time.time()
    # Misma clave que check_rate_limit: endpoint + IP.
    bucket_key = f'{request.endpoint or request.path}:{client_ip}'

    with _rate_lock:
        store = _load_store()
        if bucket_key in store:
            requests = [t for t in store[bucket_key] if current_time - t < window]
            remaining = max(0, limit - len(requests))
        else:
            remaining = limit

    response.headers['X-RateLimit-Limit'] = str(limit)
    response.headers['X-RateLimit-Remaining'] = str(remaining)
    response.headers['X-RateLimit-Reset'] = str(int(current_time + window))
    return response