from functools import wraps
from flask import jsonify, request
import time


rate_limit_store = {}


def get_client_ip():
    """Obtiene la IP del cliente considerando proxies"""
    if request.headers.get('X-Forwarded-For'):
        return request.headers.get('X-Forwarded-For').split(',')[0].strip()
    return request.remote_addr or '127.0.0.1'


def check_rate_limit(limit=10, window=60):
    """
    Decorador para aplicar rate limiting.
    limit: número máximo de requests permitidos
    window: ventana de tiempo en segundos
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            client_ip = get_client_ip()
            current_time = time.time()

            if client_ip not in rate_limit_store:
                rate_limit_store[client_ip] = []

            requests = rate_limit_store[client_ip]
            requests = [t for t in requests if current_time - t < window]
            rate_limit_store[client_ip] = requests

            if len(requests) >= limit:
                return jsonify({
                    "status": "error",
                    "message": "Demasiadas solicitudes. Intenta más tarde."
                }), 429

            requests.append(current_time)
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def add_rate_limit_headers(response, limit=10, window=60):
    """Agrega headers de RateLimit a la respuesta"""
    client_ip = get_client_ip()
    current_time = time.time()

    if client_ip in rate_limit_store:
        requests = [t for t in rate_limit_store[client_ip] if current_time - t < window]
        remaining = max(0, limit - len(requests))
    else:
        remaining = limit

    response.headers['X-RateLimit-Limit'] = str(limit)
    response.headers['X-RateLimit-Remaining'] = str(remaining)
    response.headers['X-RateLimit-Reset'] = str(int(current_time + window))
    return response