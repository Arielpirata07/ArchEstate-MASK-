import re

import phonenumbers
from phonenumbers import NumberParseException
from i18n import t, get_language


VALID_ZONES = [
    'centro', 'norte', 'sur', 'este', 'oeste',
    'palermo', 'belgrano', 'recoleta', 'caballito', 'flores',
    'villa_crespo', 'almagro', 'boedo', 'chacarita', 'colegiales',
    'constitucion', 'liniers', 'mataderos', 'monte_castro', 'parque_avellaneda',
    'paternal', 'san_cristobal', 'san_nicolas', 'velez_sarsfield', 'versailles',
    'villa_lugano', 'villa_urquiza', 'villa_general_mitre', 'villa_del_parque',
    'villa_santa_rita', 'congreso', 'saavedra', 'coghlan', 'santo_domingo',
    'villanueva', 'nuñez', 'urquiza', 'martinez', 'olivos',
    'vicente_lopez', 'san_isidro', 'beccar', 'tigre', 'san_fernando',
    'acassuso', 'carril', 'boulogne', 'martindale', 'villa_adelina',
    'san_andres', 'temperley', 'lanus', 'avellaneda', 'quilmes',
    'berazategui', 'ezeiza', 'esteban_echeverria', 'loreto', 'la_matanza',
    'tres_de_febrero', 'moron', 'hurlingham', 'ituzaingo', 'merlo',
    'general_rodriguez', 'marcos_paz', 'navegacion', 'san_miguel', 'jose_c_paz',
    'malvinas_argentinas', 'pilar', 'del_viso', 'polvorines', '_MANZANA_'
]


def get_valid_property_types():
    from models import get_form_options_by_category
    return get_form_options_by_category('property_type')


def get_valid_operation_types():
    from models import get_form_options_by_category
    return get_form_options_by_category('operation_type')


def get_valid_currencies():
    from models import get_form_options_by_category
    return get_form_options_by_category('currency')


def validate_email(email):
    """
    Validación completa de email.
    Retorna (is_valid, error_message)
    """
    lang = get_language()

    if not email or not isinstance(email, str):
        return False, t('val.email_required', lang)

    email = email.strip()

    if len(email) > 254:
        return False, t('val.email_too_long', lang)

    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(pattern, email):
        return False, t('val.email_invalid_format', lang)

    local, domain = email.rsplit('@', 1)
    if len(local) > 64:
        return False, t('val.email_local_too_long', lang)

    if '..' in email:
        return False, t('val.email_double_dot', lang)

    if domain.startswith('.') or domain.endswith('.'):
        return False, t('val.email_invalid_domain', lang)

    return True, None


def validate_phone(phone):
    """
    Validación de teléfono con código de país.
    Usa phonenumbers (Google libphonenumber) para validación por país.
    Formatos aceptados: +54 9 11 XXXX XXXX, +598 XX XXXX XXXX, etc.
    Retorna (is_valid, error_message).

    Si el parse con región None falla (sin '+'), intenta como número argentino
    (region='AR') para preservar compatibilidad con usuarios legacy.
    """
    lang = get_language()

    if not phone or not isinstance(phone, str):
        return False, t('val.phone_required', lang)

    phone = phone.strip()

    parsed = None
    try:
        parsed = phonenumbers.parse(phone, None)
    except NumberParseException:
        try:
            parsed = phonenumbers.parse(phone, "AR")
        except NumberParseException:
            return False, t('val.phone_invalid_format', lang)

    if parsed is None:
        return False, t('val.phone_invalid_format', lang)

    if not phonenumbers.is_possible_number(parsed):
        return False, t('val.phone_impossible', lang)

    if not phonenumbers.is_valid_number(parsed):
        region = phonenumbers.region_code_for_number(parsed)
        if region:
            return False, t('val.phone_invalid_for_region', lang, region=region)
        return False, t('val.phone_invalid_check_code', lang)

    return True, None


def validate_budget(amount):
    """
    Validación de presupuesto.
    Acepta números positivos o range strings "min - max".
    Retorna (is_valid, error_message)
    """
    lang = get_language()

    if amount is None:
        return False, t('val.budget_required', lang)

    try:
        parts = str(amount).split(' - ')
        for part in parts:
            num = float(part.strip())
            if num <= 0:
                return False, t('val.budget_positive', lang)
            if num > 1000000000000:
                return False, t('val.budget_too_large', lang)
        return True, None
    except (ValueError, TypeError):
        return False, t('val.budget_invalid', lang)


def validate_zone(zone):
    """
    Validación de zona.
    Acepta cualquier texto no vacío entre 2 y 100 caracteres.
    Retorna (is_valid, error_message)
    """
    lang = get_language()

    if not zone or not isinstance(zone, str):
        return False, t('val.zone_required', lang)

    zone = zone.strip()

    if len(zone) < 2:
        return False, t('val.zone_too_short', lang)

    if len(zone) > 100:
        return False, t('val.zone_too_long', lang)

    return True, None


def validate_username(username):
    lang = get_language()
    if not username or len(username) < 3 or len(username) > 30:
        return False, t('val.username_length', lang)
    if not re.match(r'^[a-zA-Z0-9_]+$', username):
        return False, t('val.username_format', lang)
    return True, None


def validate_password(password):
    lang = get_language()
    if not password or len(password) < 6:
        return False, t('val.password_min_length', lang)
    if not re.search(r'[A-Za-z]', password) or not re.search(r'[0-9]', password):
        return False, t('val.password_format', lang)
    return True, None


def validate_property_type(ptype):
    lang = get_language()
    valid = get_valid_property_types()
    if not ptype or ptype not in valid:
        return False, t('val.invalid_property_type', lang)
    return True, None


def validate_operation_type(otype):
    lang = get_language()
    valid = get_valid_operation_types()
    if not otype or otype not in valid:
        return False, t('val.invalid_operation_type', lang)
    return True, None