from flask import Blueprint

profile_bp = Blueprint('profile', __name__, url_prefix='')

from routes.profile import core, uploads, professional, notifications, exports, exports_pdf

__all__ = ["profile_bp"]
