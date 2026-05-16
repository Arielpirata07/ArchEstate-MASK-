import re


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
    Validación de teléfono argentino.
    Formatos aceptados: 11XXXXXXXX, +54XXXXXXXXXX, 0XXXXXXXXX, XXXXXXXXX
    Retorna (is_valid, error_message)
    """
    if not phone or not isinstance(phone, str):
        return False, "Teléfono es requerido"

    phone = phone.strip()

    phone_digits = re.sub(r'[^\d]', '', phone)

    if len(phone_digits) < 8 or len(phone_digits) > 13:
        return False, "Teléfono debe tener entre 8 y 13 dígitos"

    if len(phone_digits) == 10 and phone_digits.startswith('11'):
        return True, None

    if len(phone_digits) == 11 and phone_digits.startswith('549'):
        return True, None

    if len(phone_digits) == 9:
        return True, None

    if len(phone_digits) == 8:
        return True, None

    return False, "Formato de teléfono argentino inválido"


def validate_budget(amount):
    """
    Validación de presupuesto.
    Acepta números positivos.
    Retorna (is_valid, error_message)
    """
    if amount is None:
        return False, "Presupuesto es requerido"

    try:
        num = float(amount)
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
    Debe ser una zona válida de la lista o cadena no vacía.
    Retorna (is_valid, error_message)
    """
    if not zone or not isinstance(zone, str):
        return False, "Zona es requerida"

    zone = zone.strip().lower()

    if len(zone) < 2:
        return False, "Zona demasiado corta"

    if len(zone) > 100:
        return False, "Zona demasiado larga"

    if zone in VALID_ZONES:
        return True, None

    if re.match(r'^[a-z][a-z0-9_\s]*$', zone):
        return True, None

    return False, f"Zona '{zone}' no es válida"