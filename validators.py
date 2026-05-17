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
    Validación de teléfono con código de país.
    Formatos aceptados: +54 9 11 XXXX XXXX, +598 XX XXXX XXXX, 11XXXXXXXX, etc.
    Retorna (is_valid, error_message)
    """
    if not phone or not isinstance(phone, str):
        return False, "Teléfono es requerido"

    phone = phone.strip()

    phone_digits = re.sub(r'[^\d]', '', phone)

    if len(phone_digits) < 8 or len(phone_digits) > 15:
        return False, "Teléfono debe tener entre 8 y 15 dígitos"

    return True, None


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