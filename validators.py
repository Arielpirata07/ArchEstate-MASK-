import re

import phonenumbers
from phonenumbers import NumberParseException


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

VALID_PROPERTY_TYPES = ['departamento', 'casa', 'duplex', 'penthouse', 'local_comercial']
VALID_OPERATION_TYPES = ['Comprar Propiedad', 'Remodelación Integral', 'Construir desde Cero']


def validate_email(email):
    """
    Validación completa de email.
    Retorna (is_valid, error_message)
    """
    if not email or not isinstance(email, str):
        return False, "Email es requerido"

    email = email.strip()

    if len(email) > 254:
        return False, "Email demasiado largo"

    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(pattern, email):
        return False, "Formato de email inválido"

    local, domain = email.rsplit('@', 1)
    if len(local) > 64:
        return False, "Parte local del email demasiado larga"

    if '..' in email:
        return False, "Email inválido: punto doble"

    if domain.startswith('.') or domain.endswith('.'):
        return False, "Dominio inválido"

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
    if not phone or not isinstance(phone, str):
        return False, "Teléfono es requerido"

    phone = phone.strip()

    parsed = None
    try:
        parsed = phonenumbers.parse(phone, None)
    except NumberParseException:
        try:
            parsed = phonenumbers.parse(phone, "AR")
        except NumberParseException:
            return False, "Número inválido. Incluí el código de país (ej: +54 9 11 1234 5678)"

    if parsed is None:
        return False, "Número inválido. Incluí el código de país (ej: +54 9 11 1234 5678)"

    if not phonenumbers.is_possible_number(parsed):
        return False, "Número imposible (cantidad de dígitos inválida)"

    if not phonenumbers.is_valid_number(parsed):
        region = phonenumbers.region_code_for_number(parsed)
        if region:
            return False, f"Número inválido para {region}"
        return False, "Número inválido (verificá el código de país)"

    return True, None


def validate_budget(amount):
    """
    Validación de presupuesto.
    Acepta números positivos o range strings "min - max".
    Retorna (is_valid, error_message)
    """
    if amount is None:
        return False, "Presupuesto es requerido"

    try:
        parts = str(amount).split(' - ')
        for part in parts:
            num = float(part.strip())
            if num <= 0:
                return False, "El presupuesto debe ser positivo"
            if num > 1000000000000:
                return False, "Presupuesto demasiado grande"
        return True, None
    except (ValueError, TypeError):
        return False, "Presupuesto debe ser un número válido"


def validate_zone(zone):
    """
    Validación de zona.
    Acepta cualquier texto no vacío entre 2 y 100 caracteres.
    Retorna (is_valid, error_message)
    """
    if not zone or not isinstance(zone, str):
        return False, "Zona es requerida"

    zone = zone.strip()

    if len(zone) < 2:
        return False, "Zona demasiado corta"

    if len(zone) > 100:
        return False, "Zona demasiado larga"

    return True, None


def validate_username(username):
    if not username or len(username) < 3 or len(username) > 30:
        return False, 'El nombre de usuario debe tener entre 3 y 30 caracteres.'
    if not re.match(r'^[a-zA-Z0-9_]+$', username):
        return False, 'El usuario solo puede contener letras, numeros y guion bajo.'
    return True, None


def validate_password(password):
    if not password or len(password) < 6:
        return False, 'La contrasena debe tener al menos 6 caracteres.'
    if not re.search(r'[A-Za-z]', password) or not re.search(r'[0-9]', password):
        return False, 'La contrasena debe contener al menos una letra y un numero.'
    return True, None


def validate_property_type(ptype):
    if not ptype or ptype not in VALID_PROPERTY_TYPES:
        return False, 'Tipo de propiedad no valido.'
    return True, None


def validate_operation_type(otype):
    if not otype or otype not in VALID_OPERATION_TYPES:
        return False, 'Tipo de operacion no valido.'
    return True, None