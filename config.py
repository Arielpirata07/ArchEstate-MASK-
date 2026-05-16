import os

env_file = os.path.join(os.path.dirname(__file__), '.env')
if os.path.exists(env_file):
    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ.setdefault(key, value)

DATABASE = os.path.join(os.path.dirname(__file__), 'database.db')

SECRET_KEY = os.environ.get('SECRET_KEY')

if not SECRET_KEY:
    raise ValueError("SECRET_KEY must be set in .env file")

UPLOAD_FOLDER = os.path.join('static', 'uploads', 'docs')

ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg'}

MAX_UPLOAD_SIZE = 16 * 1024 * 1024

SESSION_TIMEOUT = 3600

PAGINATION_DEFAULT = 50