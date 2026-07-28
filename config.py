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

DATABASE_URL = os.environ.get('DATABASE_URL', '')
SECRET_KEY = os.environ.get('SECRET_KEY')
SITE_URL = os.environ.get('SITE_URL', '')

if not SECRET_KEY:
    raise ValueError("SECRET_KEY must be set in .env file")

UPLOAD_FOLDER = os.path.join('static', 'uploads', 'docs')
AVATAR_FOLDER = os.path.join('static', 'uploads', 'avatars')

ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg', 'gif', 'webp'}

MAX_UPLOAD_SIZE = 16 * 1024 * 1024

SESSION_TIMEOUT = 3600

PAGINATION_DEFAULT = 50

PERMANENT_SESSION_LIFETIME = 3600

REMEMBER_TOKEN_DAYS = 30
REMEMBER_COOKIE_NAME = 'remember_token'
REMEMBER_COOKIE_SECURE = os.environ.get('PREFER_SECURE_COOKIES', '0') == '1'

OTP_TTL_MINUTES = 10
OTP_MAX_ATTEMPTS = 5

TWILIO_ACCOUNT_SID = os.environ.get('TWILIO_ACCOUNT_SID', '')
TWILIO_AUTH_TOKEN = os.environ.get('TWILIO_AUTH_TOKEN', '')
TWILIO_PHONE_NUMBER = os.environ.get('TWILIO_PHONE_NUMBER', '')
TWILIO_WHATSAPP_FROM = os.environ.get('TWILIO_WHATSAPP_FROM', '')
TWILIO_WHATSAPP_CONTENT_SID = os.environ.get('TWILIO_WHATSAPP_CONTENT_SID', '')
TWILIO_WHATSAPP_BUTTON_CONTENT_SID = os.environ.get('TWILIO_WHATSAPP_BUTTON_CONTENT_SID', '')
TWILIO_WHATSAPP_LEAD_CONTENT_SID = os.environ.get('TWILIO_WHATSAPP_LEAD_CONTENT_SID', '')
TWILIO_SIMULATE = os.environ.get('TWILIO_SIMULATE', 'false').lower() == 'true'

SMTP_HOST = os.environ.get('SMTP_HOST', '')
SMTP_PORT = int(os.environ.get('SMTP_PORT', '587'))
SMTP_USER = os.environ.get('SMTP_USER', '')
SMTP_PASS = os.environ.get('SMTP_PASS', '')
SMTP_FROM = os.environ.get('SMTP_FROM', '')

SENTRY_DSN = os.environ.get('SENTRY_DSN', '')

BACKUP_S3_BUCKET = os.environ.get('BACKUP_S3_BUCKET', '')
BACKUP_S3_ACCESS_KEY = os.environ.get('BACKUP_S3_ACCESS_KEY', '')
BACKUP_S3_SECRET_KEY = os.environ.get('BACKUP_S3_SECRET_KEY', '')
BACKUP_S3_REGION = os.environ.get('BACKUP_S3_REGION', 'us-east-1')

STAGING = os.environ.get('STAGING', 'false').lower() == 'true'