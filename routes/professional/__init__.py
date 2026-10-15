from flask import Blueprint

professional_bp = Blueprint('professional', __name__, url_prefix='')

from routes.professional import leads, tracking, stats, exports, pipeline, calendar, dashboard, docs, helpers

__all__ = ["professional_bp"]
