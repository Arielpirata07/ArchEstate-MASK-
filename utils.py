from datetime import datetime
import hashlib
import urllib.parse
import re

import phonenumbers
from phonenumbers import NumberParseException, PhoneNumberType
import pytz

import config


MIME_MAGIC_BYTES = {
    'pdf':  [b'%PDF'],
    'jpg':  [b'\xff\xd8\xff'],
    'jpeg': [b'\xff\xd8\xff'],
    'png':  [b'\x89PNG\r\n\x1a\n'],
    'gif':  [b'GIF87a', b'GIF89a'],
    'webp': [b'RIFF'],
}


DEFAULT_REGION = 'AR'


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


def _parse_phone(phone, region=DEFAULT_REGION):
    """
    Parsea un número con phonenumbers. Retorna el objeto PhoneNumber o None.
    region: código de país por defecto (sólo se usa si el número no incluye '+').
    """
    if not phone or not isinstance(phone, str):
        return None
    try:
        return phonenumbers.parse(phone.strip(), region)
    except NumberParseException:
        return None


def normalize_phone_to_e164(phone, region=DEFAULT_REGION):
    """
    Normaliza un teléfono a formato E.164 (con +), ej: +5491144445555.
    Retorna string vacío si no se puede parsear.
    """
    parsed = _parse_phone(phone, region)
    if parsed is None:
        return ''
    if not phonenumbers.is_possible_number(parsed):
        return ''
    try:
        return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
    except Exception:
        return ''


def is_mobile_number(phone, region=DEFAULT_REGION):
    """
    Determina si un teléfono es móvil (o posiblemente móvil) usando
    metadata de Google libphonenumber. Distingue móvil de fijo.
    """
    parsed = _parse_phone(phone, region)
    if parsed is None:
        return False
    if not phonenumbers.is_valid_number(parsed):
        return False
    t = phonenumbers.number_type(parsed)
    return t in (PhoneNumberType.MOBILE, PhoneNumberType.FIXED_LINE_OR_MOBILE)


def classify_phone_type(phone, region=DEFAULT_REGION):
    """
    Clasifica un teléfono como 'mobile' | 'fixed_or_mobile' | 'fixed' | 'other' | ''.
    Retorna string vacío si no se puede parsear.
    Usado por update_user_phone y init_db backfill para mantener coherencia.
    """
    parsed = _parse_phone(phone, region)
    if parsed is None:
        return ''
    try:
        t = phonenumbers.number_type(parsed)
    except Exception:
        return ''
    if t == PhoneNumberType.MOBILE:
        return 'mobile'
    if t == PhoneNumberType.FIXED_LINE_OR_MOBILE:
        return 'fixed_or_mobile'
    if t == PhoneNumberType.FIXED_LINE:
        return 'fixed'
    return 'other'


def is_whatsapp_capable(phone, region=DEFAULT_REGION):
    """
    Determina si un número es candidato a link wa.me.
    Reglas: (1) parseable, (2) número válido, (3) tipo móvil (o ambiguo).
    Reemplaza la heurística anterior de longitud.
    """
    return is_mobile_number(phone, region)


def normalize_phone_for_whatsapp(phone, region=DEFAULT_REGION):
    """
    Devuelve los dígitos E.164 sin el '+', listos para wa.me/{digits}.
    Retorna string vacío si no se puede parsear.
    """
    e164 = normalize_phone_to_e164(phone, region)
    if not e164:
        return ''
    return e164.lstrip('+')


def normalize_phone_for_sms(phone, region=DEFAULT_REGION):
    """
    Normaliza un teléfono para links sms: usa E.164 con '+'.
    """
    e164 = normalize_phone_to_e164(phone, region)
    if not e164:
        return ''
    if not e164.startswith('+'):
        e164 = '+' + e164
    return e164


def build_whatsapp_message(pro_name=None, operation=None, zone=None, lead_id=None):
    """
    Construye el mensaje de primer contacto para WhatsApp en español rioplatense.
    Si faltan datos relevantes, degrada a un mensaje genérico profesional.
    """
    pro = (pro_name or '').strip() or 'el equipo'
    op = (operation or '').strip()
    zn = (zone or '').strip()

    if op and zn:
        body = f"Hola, soy {pro} de ArchEstate. Te escribo por tu consulta de {op} en {zn}."
    elif op:
        body = f"Hola, soy {pro} de ArchEstate. Te escribo por tu consulta de {op}."
    elif zn:
        body = f"Hola, soy {pro} de ArchEstate. Te escribo por tu consulta en {zn}."
    else:
        body = f"Hola, soy {pro} de ArchEstate. Vi tu consulta en la plataforma y me interesa conversar."

    body += " ¿Tenés un momento para hablar?"
    return body[:500]


def build_whatsapp_url(phone, pro_name=None, operation=None, zone=None, lead_id=None, region=DEFAULT_REGION):
    """
    Construye una URL completa wa.me/{digits}?text={msg}, lista para usar en
    redirección server-side o link directo. Retorna string vacío si el
    teléfono no es WhatsApp-capable (no parseable, inválido, o no es móvil).
    """
    e164 = normalize_phone_to_e164(phone, region)
    if not e164:
        return ''
    if not is_whatsapp_capable(e164):
        return ''
    digits = e164.lstrip('+')
    msg = build_whatsapp_message(pro_name, operation, zone, lead_id)
    quoted = urllib.parse.quote_plus(msg)
    return f"https://wa.me/{digits}?text={quoted}"


def build_sms_url(phone, pro_name=None, operation=None, zone=None, region=DEFAULT_REGION):
    """
    Construye un link sms: para fallback cuando el número no es WhatsApp-capable.
    """
    e164 = normalize_phone_for_sms(phone, region)
    if not e164:
        return ''
    msg = build_whatsapp_message(pro_name, operation, zone)
    quoted = urllib.parse.quote_plus(msg[:160])
    return f"sms:{e164}?body={quoted}"


def build_tel_url(phone, region=DEFAULT_REGION):
    """
    Construye un link tel: básico (sin cuerpo).
    """
    e164 = normalize_phone_for_sms(phone, region)
    if not e164:
        return ''
    return f"tel:{e164}"


def hash_phone_digits(digits, length=16):
    """
    Hashea los dígitos de un teléfono con SHA-256 para no exponer PII en logs.
    Retorna los primeros `length` caracteres hex.
    """
    if not digits:
        return ''
    return hashlib.sha256(digits.encode('utf-8')).hexdigest()[:length]


def log_action(action, target, session=None, conn=None):
    """
    Registra una accion en la tabla de auditoria.
    Si se pasa `conn`, lo usa (recomendado para evitar 'database is locked' en SQLite
    cuando el route ya tiene una conexion abierta). Si no, abre y cierra una propia.
    Siempre hace commit() al final (es idempotente si ya estaba commiteado).
    """
    from models import get_db_connection

    own_conn = conn is None
    try:
        if own_conn:
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
        if own_conn and conn:
            conn.close()


def log_event(user_id=None, lead_id=None, event='', props=None, ip=None, conn=None):
    """
    Registra un evento en la tabla events (telemetría).
    props: dict serializable a JSON. Si no es serializable, se coerce a str.
    Si se pasa `conn`, lo usa (recomendado para SQLite). Si no, abre y cierra uno propio.
    Siempre hace commit() al final (es idempotente si ya estaba commiteado).
    """
    import json
    from models import get_db_connection

    if not event:
        return False

    own_conn = conn is None
    props_json = ''
    if props:
        try:
            props_json = json.dumps(props, ensure_ascii=False, default=str)[:2000]
        except Exception:
            props_json = json.dumps({'raw': str(props)[:500]}, ensure_ascii=False)

    try:
        if own_conn:
            conn = get_db_connection()
        conn.execute(
            'INSERT INTO events (user_id, lead_id, event, props_json, ip) VALUES (?, ?, ?, ?, ?)',
            (user_id, lead_id, event[:64], props_json, (ip or '')[:64])
        )
        conn.commit()
        return True
    except Exception as e:
        print(f"Error al registrar evento: {e}")
        return False
    finally:
        if own_conn and conn:
            conn.close()


# --- Remember-me tokens (cookie firmada) -----------------------------------

import secrets
from datetime import timedelta


def generate_remember_token():
    """
    Genera un par (selector, validator) para cookie de remember-me.
    - selector: 16 bytes url-safe (24 chars), se guarda plano en BD para lookup.
    - validator: 32 bytes url-safe (~43 chars), se hashea con sha256 y se guarda el hash.
      El validator NUNCA se persiste en claro.
    Devuelve: (selector_str, validator_str, validator_hash_hex)
    """
    selector = secrets.token_urlsafe(16)
    validator = secrets.token_urlsafe(32)
    validator_hash = hashlib.sha256(validator.encode('utf-8')).hexdigest()
    return selector, validator, validator_hash


def validate_remember_token(selector, validator):
    """
    Valida un par (selector, validator). Devuelve user_id si es válido y vigente,
    None en caso contrario. NO valida la sesión actual: esa responsabilidad es del caller.
    """
    if not selector or not validator:
        return None
    from models import get_db_connection
    conn = None
    try:
        conn = get_db_connection()
        row = conn.execute(
            'SELECT user_id, validator_hash, expires_at FROM remember_tokens WHERE selector = ?',
            (selector,)
        ).fetchone()
        if not row:
            return None
        try:
            expires_at = datetime.fromisoformat(row['expires_at'])
        except (ValueError, TypeError):
            return None
        if datetime.now() >= expires_at:
            conn.execute('DELETE FROM remember_tokens WHERE selector = ?', (selector,))
            conn.commit()
            return None
        validator_hash = hashlib.sha256(validator.encode('utf-8')).hexdigest()
        if not secrets.compare_digest(validator_hash, row['validator_hash']):
            conn.execute('DELETE FROM remember_tokens WHERE selector = ?', (selector,))
            conn.commit()
            return None
        return row['user_id']
    except Exception as e:
        print(f"Error al validar remember token: {e}")
        return None
    finally:
        if conn:
            conn.close()


def revoke_remember_token(selector):
    """Elimina un único token por selector. No falla si no existe."""
    if not selector:
        return False
    from models import get_db_connection
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.execute('DELETE FROM remember_tokens WHERE selector = ?', (selector,))
        conn.commit()
        return cursor.rowcount > 0
    except Exception as e:
        print(f"Error al revocar remember token: {e}")
        return False
    finally:
        if conn:
            conn.close()


def purge_expired_remember_tokens():
    """Elimina todos los tokens expirados. Idempotente, llamar en before_request."""
    from models import get_db_connection
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.execute(
            'DELETE FROM remember_tokens WHERE expires_at < ?',
            (datetime.now().isoformat(),)
        )
        conn.commit()
        return cursor.rowcount
    except Exception as e:
        print(f"Error al purgar remember tokens: {e}")
        return 0
    finally:
        if conn:
            conn.close()


def remember_cookie_max_age():
    """Devuelve el max_age en segundos para la cookie remember_token."""
    return config.REMEMBER_TOKEN_DAYS * 24 * 3600


def remember_expires_at():
    """Devuelve el datetime de expiración para guardar en BD."""
    return datetime.now() + timedelta(days=config.REMEMBER_TOKEN_DAYS)
