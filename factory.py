import os

from flask import Flask

import config


def create_app():
    app = Flask(__name__)
    app.secret_key = config.SECRET_KEY
    app.config['UPLOAD_FOLDER'] = os.path.join(app.root_path, config.UPLOAD_FOLDER)
    app.config['AVATAR_FOLDER'] = os.path.join(app.root_path, config.AVATAR_FOLDER)
    app.config['PERMANENT_SESSION_LIFETIME'] = config.PERMANENT_SESSION_LIFETIME
    app.jinja_env.autoescape = True

    from middleware import register_middleware
    register_middleware(app)

    from errors import register_error_handlers
    register_error_handlers(app)

    from app_setup import init_db
    init_db(app)

    from routes.auth_bp import auth_bp
    from routes.public_bp import public_bp
    from routes.client_bp import client_bp
    from routes.professional_bp import professional_bp
    from routes.admin_bp import admin_bp
    from routes.phone_bp import phone_bp
    from routes.lead_bp import lead_bp
    from routes_profile import profile_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(public_bp)
    app.register_blueprint(client_bp)
    app.register_blueprint(professional_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(phone_bp)
    app.register_blueprint(lead_bp)
    app.register_blueprint(profile_bp)

    return app
