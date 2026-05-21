from datetime import datetime
import pytz
import re

import config


MIME_MAGIC_BYTES = {
    'pdf':  [b'%PDF'],
    'jpg':  [b'\xff\xd8\xff'],
    'jpeg': [b'\xff\xd8\xff'],
    'png':  [b'\x89PNG\r\n\x1a\n'],
    'gif':  [b'GIF87a', b'GIF89a'],
    'webp': [b'RIFF'],  # se valida RIFF + WEBP en validate_mime_type
}


def validate_mime_type(file_stream, filename):
    """
    Valida el tipo MIME real leyendo los magic bytes del archivo.
    Retorna (is_valid, detected_ext, error_message).
    """
    if not filename or '.' not in filename:
        return False, None, "Nombre de archivo inválido"

    ext = filename.rsplit('.', 1)[1].lower()

    if ext not in MIME_MAGIC_BYTES:
        return False, None, f"Extensión .{ext} no permitida"

    file_stream.seek(0)
    header = file_stream.read(16)
    file_stream.seek(0)

    for magic in MIME_MAGIC_BYTES[ext]:
        if header.startswith(magic):
            if ext == 'webp' and (header[0:4] != b'RIFF' or header[8:12] != b'WEBP'):
                continue
            return True, ext, None

    return False, None, f"El contenido del archivo no corresponde a un {ext.upper()}"


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


import re


def normalize_phone_for_whatsapp(phone):
    """
    Normaliza un numero de telefono para usar en links de WhatsApp (wa.me).
    WhatsApp requiere solo digitos, sin el '+' inicial.
    """
    if not phone:
        return ''
    digits = re.sub(r'\D', '', phone)
    return digits


def is_whatsapp_capable(phone):
    """
    Determina si un numero de telefono es valido para WhatsApp.
    """
    if not phone:
        return False
    digits = re.sub(r'\D', '', phone)
    return 10 <= len(digits) <= 15 and not digits.startswith('0')


def normalize_phone_for_sms(phone):
    """
    Normaliza un numero de telefono para usar en links de SMS.
    """
    if not phone:
        return ''
    digits = re.sub(r'[^\d+]', '', phone)
    if not digits.startswith('+'):
        digits = '+' + digits
    return digits


def log_action(action, target, session=None):
    """Registra una accion en la tabla de auditoria de la base de datos."""
    from models import get_db_connection

    conn = None
    try:
        conn = get_db_connection()
        safe_action = safe_text(action)[:100]
        safe_target = safe_text(target)[:200]
        safe_username = safe_text(session.get('username', 'sistema') if session else 'sistema')[:50]
        user_id = session.get('user_id') if session else None
        conn.execute(
            'INSERT INTO audit_log (action, target, admin, user_id) VALUES (?, ?, ?, ?)',
            (safe_action, safe_target, safe_username, user_id)
        )
        conn.commit()
    except Exception as e:
        print(f"Error al registrar auditoria: {e}")
    finally:
        if conn:
            conn.close()