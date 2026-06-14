from flask import g, jsonify, request, render_template


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

    @app.errorhandler(429)
    def _h_429(e):
        if _wants_json():
            return _err_response(429, 'Demasiadas solicitudes.', 'RATE_LIMITED')
        return render_template('errors/429.html'), 429

    @app.errorhandler(500)
    def _h_500(e):
        rid = getattr(g, 'request_id', None)
        print(f'[500] request_id={rid}: {e}')
        if _wants_json():
            return _err_response(500, 'Error interno del servidor.', 'INTERNAL')
        return render_template('errors/500.html'), 500
