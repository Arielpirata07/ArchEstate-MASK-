from functools import wraps
from flask import jsonify, request
import time


rate_limit_store = {}


def get_client_ip():
    """Obtiene la IP del cliente considerando proxies"""
    if request.headers.get('X-Forwarded-For'):
        return request.headers.get('X-Forwarded-For').split(',')[0].strip()
    return request.remote_addr or '127.0.0.1'


def _rate_limit_html_response(endpoint_name):
    """Retorna una página HTML estilizada para rate limit en formularios"""
    labels = {
        'login': 'Inicio de Sesión',
        'register': 'Registro de Cuenta',
    }
    label = labels.get(endpoint_name, 'Acceso')
    return f'''<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Demasiados Intentos | ArchEstate</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="/static/js/tailwind-config.js"></script>
    <link href="https://fonts.googleapis.com/css2?family=Newsreader:ital,opsz,wght@0,6..72,200..800;1,6..72,200..800&family=Manrope:wght@200..800&display=swap" rel="stylesheet">
    <script src="https://unpkg.com/lucide@latest"></script>
</head>
<body class="min-h-screen flex items-center justify-center bg-gradient-to-br from-[#000410] via-[#101E33] to-[#000410]">
    <div class="max-w-md w-full mx-4">
        <div class="bg-white rounded-lg shadow-2xl border-t-4 border-amber-500 overflow-hidden">
            <div class="px-8 pt-8 pb-4 text-center">
                <div class="w-16 h-16 mx-auto mb-4 rounded-full bg-amber-50 flex items-center justify-center">
                    <i data-lucide="shield-alert" class="w-8 h-8 text-amber-600"></i>
                </div>
                <h2 class="text-3xl font-serif text-[#000410]">Demasiados <span class="serif-italic">Intentos</span></h2>
                <p class="text-sm text-[#000410]/50 mt-2">Has excedido el número máximo de solicitudes para <strong>{label}</strong>.</p>
            </div>
            <div class="mx-8 mb-6 p-3 bg-amber-50 border border-amber-100 rounded">
                <p class="text-[10px] text-amber-700 font-bold uppercase tracking-wider leading-relaxed">
                    Por seguridad, esta acción está limitada temporalmente. Espera unos minutos antes de intentar nuevamente.
                </p>
            </div>
            <div class="px-8 pb-8 text-center">
                <a href="/" class="inline-flex items-center gap-2 px-6 py-3 bg-[#000410] text-white rounded text-[10px] font-bold uppercase tracking-widest hover:bg-[#735A3A] transition-all">
                    <i data-lucide="home" class="w-4 h-4"></i> Volver al Inicio
                </a>
            </div>
        </div>
    </div>
    <script>if(window.lucide) lucide.createIcons();</script>
</body>
</html>''', 429


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
                accept = request.headers.get('Accept', '')
                if 'application/json' in accept or request.is_json:
                    return jsonify({
                        "status": "error",
                        "message": "Demasiadas solicitudes. Espera unos minutos antes de intentar nuevamente.",
                        "retry_after": int(window - (current_time - (requests[0] if requests else current_time)))
                    }), 429
                else:
                    endpoint = f.__name__
                    html, status = _rate_limit_html_response(endpoint)
                    return html, status

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