import logging
import traceback

from flask import g, jsonify, request, render_template

logger = logging.getLogger(__name__)


def _err_response(status, message, code=None):
    body = {
        'error': message,
        'code': code or str(status),
        'request_id': getattr(g, 'request_id', None),
    }
    return jsonify(body), status


def _wants_json():
    return request.accept_mimetypes.best_match(['application/json', 'text/html']) == 'application/json'


def register_error_handlers(app):
    @app.errorhandler(400)
    def _h_400(e):
        if _wants_json():
            return _err_response(400, 'Solicitud malformada.', 'BAD_REQUEST')
        return render_template('errors/400.html'), 400

    @app.errorhandler(403)
    def _h_403(e):
        logger.warning('403 %s %s', request.method, request.path)
        if _wants_json():
            return _err_response(403, 'Acceso denegado.', 'FORBIDDEN')
        return render_template('errors/403.html'), 403

    @app.errorhandler(404)
    def _h_404(e):
        if _wants_json():
            return _err_response(404, 'Recurso no encontrado.', 'NOT_FOUND')
        return render_template('errors/404.html'), 404

    @app.errorhandler(409)
    def _h_409(e):
        if _wants_json():
            return _err_response(409, 'Conflicto con el estado actual.', 'CONFLICT')
        return render_template('errors/409.html'), 409

    @app.errorhandler(410)
    def _h_410(e):
        if _wants_json():
            return _err_response(410, 'Recurso expirado.', 'GONE')
        return render_template('errors/410.html'), 410

    @app.errorhandler(413)
    def _h_413(e):
        logger.warning('413 %s %s — upload excedido', request.method, request.path)
        if _wants_json():
            return _err_response(413, 'El archivo excede el tamaño máximo permitido.', 'PAYLOAD_TOO_LARGE')
        return render_template('errors/413.html'), 413

    @app.errorhandler(429)
    def _h_429(e):
        if _wants_json():
            return _err_response(429, 'Demasiadas solicitudes.', 'RATE_LIMITED')
        return render_template('errors/429.html'), 429

    @app.errorhandler(500)
    def _h_500(e):
        rid = getattr(g, 'request_id', None)
        logger.error('500 request_id=%s: %s\n%s', rid, e, traceback.format_exc())
        if _wants_json():
            return _err_response(500, 'Error interno del servidor.', 'INTERNAL')
        return render_template('errors/500.html'), 500

    @app.errorhandler(502)
    def _h_502(e):
        logger.error('502 Bad Gateway: %s', e)
        if _wants_json():
            return _err_response(502, 'Servicio temporalmente no disponible.', 'BAD_GATEWAY')
        return render_template('errors/502.html'), 502

    @app.errorhandler(503)
    def _h_503(e):
        logger.error('503 Servicio no disponible: %s', e)
        if _wants_json():
            return _err_response(503, 'Servicio no disponible. Intentá de nuevo en unos segundos.', 'SERVICE_UNAVAILABLE')
        return render_template('errors/503.html'), 503

    @app.errorhandler(504)
    def _h_504(e):
        logger.error('504 Gateway Timeout: %s', e)
        if _wants_json():
            return _err_response(504, 'Tiempo de espera agotado.', 'GATEWAY_TIMEOUT')
        return render_template('errors/504.html'), 504
