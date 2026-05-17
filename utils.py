from datetime import datetime
import pytz

import config


MIME_MAGIC_BYTES = {
    'pdf':  [b'%PDF'],
    'jpg':  [b'\xff\xd8\xff'],
    'jpeg': [b'\xff\xd8\xff'],
    'png':  [b'\x89PNG\r\n\x1a\n'],
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