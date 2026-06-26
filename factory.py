import os

from flask import Flask

import config


def create_app():
    app = Flask(__name__)
    app.secret_key = config.SECRET_KEY
    app.config['UPLOAD_FOLDER'] = os.path.join(app.root_path, config.UPLOAD_FOLDER)
    app.config['AVATAR_FOLDER'] = os.path.join(app.root_path, config.AVATAR_FOLDER)
    app.config['PERMANENT_SESSION_LIFETIME'] = config.PERMANENT_SESSION_LIFETIME
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    is_dev = os.environ.get('FLASK_DEBUG', '0') == '1' or os.environ.get('PYTEST_CURRENT_TEST')
    app.config['SESSION_COOKIE_SECURE'] = not is_dev
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
    app.jinja_env.autoescape = True

    from middleware import register_middleware
    register_middleware(app)

    from errors import register_error_handlers
    register_error_handlers(app)

    from app_setup import init_db
    init_db(app)

    @app.context_processor
    def inject_form_options():
        from models import get_form_options
        options = get_form_options(active_only=True)
        grouped = {}
        for opt in options:
            grouped.setdefault(opt['category'], []).append(opt)
        return dict(form_options=grouped)

    from routes.auth_bp import auth_bp
    from routes.public_bp import public_bp
    from routes.client_bp import client_bp
    from routes.professional_bp import professional_bp
    from routes.admin_bp import admin_bp
    from routes.phone_bp import phone_bp
    from routes.lead_bp import lead_bp
    from routes.form_options_bp import form_options_bp
    from routes.whatsapp_bp import whatsapp_bp
    from routes_profile import profile_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(public_bp)
    app.register_blueprint(client_bp)
    app.register_blueprint(professional_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(phone_bp)
    app.register_blueprint(lead_bp)
    app.register_blueprint(form_options_bp)
    app.register_blueprint(whatsapp_bp)
    app.register_blueprint(profile_bp)

    return app
