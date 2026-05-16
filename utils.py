from datetime import datetime
import pytz

import config


def convert_to_argentina_time(timestamp_str):
    if not timestamp_str:
        return timestamp_str
    try:
        utc_time = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        if utc_time.tzinfo is None:
            utc_time = pytz.UTC.localize(utc_time)
        argentina_tz = pytz.timezone('America/Argentina/Buenos_Aires')
        argentina_time = utc_time.astimezone(argentina_tz)
        return argentina_time.strftime('%d/%m/%Y %H:%M:%S')
    except Exception as e:
        print(f"Error al convertir timestamp: {e}")
        return timestamp_str


def safe_text(value):
    if value is None:
        return ''
    text = str(value)
    replacements = {
        '€': 'EUR',
        '£': 'GBP',
        '¥': 'JPY',
        '—': '-',
        '–': '-',
        '©': '(c)',
        '®': '(R)',
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in config.ALLOWED_EXTENSIONS