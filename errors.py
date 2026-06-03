from flask import g, jsonify


def _err_response(status, message, code=None):
    body = {
        "error": message,
        "code": code or str(status),
        "request_id": getattr(g, 'request_id', None),
    }
    return jsonify(body), status


def register_error_handlers(app):
    @app.errorhandler(400)
    def _h_400(e):
        return _err_response(400, "Solicitud malformada.", "BAD_REQUEST")

    @app.errorhandler(404)
    def _h_404(e):
        return _err_response(404, "Recurso no encontrado.", "NOT_FOUND")

    @app.errorhandler(409)
    def _h_409(e):
        return _err_response(409, "Conflicto con el estado actual.", "CONFLICT")

    @app.errorhandler(410)
    def _h_410(e):
        return _err_response(410, "Recurso expirado.", "GONE")

    @app.errorhandler(429)
    def _h_429(e):
        return _err_response(429, "Demasiadas solicitudes.", "RATE_LIMITED")

    @app.errorhandler(500)
    def _h_500(e):
        rid = getattr(g, 'request_id', None)
        print(f"[500] request_id={rid}: {e}")
        return _err_response(500, "Error interno del servidor.", "INTERNAL")
