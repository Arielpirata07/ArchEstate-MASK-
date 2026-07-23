import logging
import traceback

from flask import g, jsonify, request, render_template
from i18n import t, get_language

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
        lang = get_language()
        if _wants_json():
            return _err_response(400, t('error.400', lang), 'BAD_REQUEST')
        return render_template('errors/400.html'), 400

    @app.errorhandler(403)
    def _h_403(e):
        logger.warning('403 %s %s', request.method, request.path)
        lang = get_language()
        if _wants_json():
            return _err_response(403, t('error.403', lang), 'FORBIDDEN')
        return render_template('errors/403.html'), 403

    @app.errorhandler(404)
    def _h_404(e):
        lang = get_language()
        if _wants_json():
            return _err_response(404, t('error.404', lang), 'NOT_FOUND')
        return render_template('errors/404.html'), 404

    @app.errorhandler(409)
    def _h_409(e):
        lang = get_language()
        if _wants_json():
            return _err_response(409, t('error.409', lang), 'CONFLICT')
        return render_template('errors/409.html'), 409

    @app.errorhandler(410)
    def _h_410(e):
        lang = get_language()
        if _wants_json():
            return _err_response(410, t('error.410', lang), 'GONE')
        return render_template('errors/410.html'), 410

    @app.errorhandler(413)
    def _h_413(e):
        logger.warning('413 %s %s — upload excedido', request.method, request.path)
        lang = get_language()
        if _wants_json():
            return _err_response(413, t('error.413', lang), 'PAYLOAD_TOO_LARGE')
        return render_template('errors/413.html'), 413

    @app.errorhandler(429)
    def _h_429(e):
        lang = get_language()
        if _wants_json():
            return _err_response(429, t('error.429', lang), 'RATE_LIMITED')
        return render_template('errors/429.html'), 429

    @app.errorhandler(500)
    def _h_500(e):
        rid = getattr(g, 'request_id', None)
        logger.error('500 request_id=%s: %s\n%s', rid, e, traceback.format_exc())
        lang = get_language()
        if _wants_json():
            return _err_response(500, t('error.500', lang), 'INTERNAL')
        return render_template('errors/500.html'), 500

    @app.errorhandler(502)
    def _h_502(e):
        logger.error('502 Bad Gateway: %s', e)
        lang = get_language()
        if _wants_json():
            return _err_response(502, t('error.502', lang), 'BAD_GATEWAY')
        return render_template('errors/502.html'), 502

    @app.errorhandler(503)
    def _h_503(e):
        logger.error('503 Servicio no disponible: %s', e)
        lang = get_language()
        if _wants_json():
            return _err_response(503, t('error.503', lang), 'SERVICE_UNAVAILABLE')
        return render_template('errors/503.html'), 503

    @app.errorhandler(504)
    def _h_504(e):
        logger.error('504 Gateway Timeout: %s', e)
        lang = get_language()
        if _wants_json():
            return _err_response(504, t('error.504', lang), 'GATEWAY_TIMEOUT')
        return render_template('errors/504.html'), 504
