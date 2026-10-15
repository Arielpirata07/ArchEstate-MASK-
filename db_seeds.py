import logging
import os
import secrets

from werkzeug.security import generate_password_hash

import utils

logger = logging.getLogger(__name__)


def _is_prod():
    """True when running outside dev and tests (production-like)."""
    return os.environ.get('FLASK_DEBUG', '0').lower() not in ('1', 'true') and not os.environ.get('PYTEST_CURRENT_TEST')


def _clean_lead_test_data(cursor):
    """Limpia datos de prueba sin sentido en la tabla leads. Solo entornos dev/test."""
    import utils

    fixes = [
        (1, '150000 - 400000', 'USD', ''),
        (2, '200000 - 500000', 'USD', ''),
        (3, '100000 - 350000', 'USD', 'Córdoba'),
        (9, '100000 - 400000', 'USD', ''),
    ]
    for lid, budget, currency, zone in fixes:
        parts = []
        params = []
        if budget:
            parts.append('budget = ?')
            params.append(budget)
        if currency:
            parts.append('currency = ?')
            params.append(currency)
        if zone:
            parts.append('zone = ?')
            params.append(zone)
        if parts:
            params.append(lid)
            cursor.execute(f'UPDATE leads SET {", ".join(parts)} WHERE id = ?', params)

    # Clean up random test text
    cursor.execute("UPDATE leads SET additional_features = '' WHERE additional_features = 'fafa'")

    # Recalcular phone_format_valid para leads con teléfono
    pending = cursor.execute(
        'SELECT id, phone FROM leads WHERE phone IS NOT NULL AND phone != "" AND phone_format_valid = 0'
    ).fetchall()
    for row in pending:
        e164 = utils.normalize_phone_to_e164(row['phone'])
        if e164:
            cursor.execute('UPDATE leads SET phone_format_valid = 1 WHERE id = ?', (row['id'],))

    if fixes or pending:
        logger.info('[init_db] Cleaned test data: %d leads budget/zone, %d phone_format_valid', len(fixes), len(pending))



def seed_all(cursor):
    """Seeds + fixups + admin inicial (idempotentes)."""
    FORM_OPTIONS_SEED = [
        ('property_type', 'departamento', 'Departamento', 'building', 1),
        ('property_type', 'casa', 'Casa', 'home', 2),
        ('property_type', 'duplex', 'Duplex', 'layers', 3),
        ('property_type', 'penthouse', 'Penthouse', 'crown', 4),
        ('property_type', 'local_comercial', 'Local Comercial', 'store', 5),
        ('operation_type', 'Comprar Propiedad', 'Comprar Propiedad', 'shopping-cart', 1),
        ('operation_type', 'Remodelación Integral', 'Remodelación Integral', 'wrench', 2),
        ('operation_type', 'Construir desde Cero', 'Construir desde Cero', 'hammer', 3),
        ('currency', 'ARG', 'Pesos Argentinos', 'dollar-sign', 1),
        ('currency', 'USD', 'Dolares', 'dollar-sign', 2),
        ('currency', 'EUR', 'Euros', 'euro', 3),
        ('parking', '', 'Sin preferencia', '', 1),
        ('parking', 'sin_cochera', 'Sin cochera', 'x-circle', 2),
        ('parking', 'simple_cubierta', 'Cochera simple cubierta', 'car', 3),
        ('parking', 'doble_cubierta', 'Cochera doble cubierta', 'car', 4),
        ('parking', 'descubierta', 'Descubierta', 'car', 5),
        ('parking', 'garage', 'Garage cerrado', 'lock', 6),
        ('orientation', '', 'Indiferente', '', 1),
        ('orientation', 'Norte', 'Norte', 'arrow-up', 2),
        ('orientation', 'Sur', 'Sur', 'arrow-down', 3),
        ('orientation', 'Este', 'Este', 'arrow-right', 4),
        ('orientation', 'Oeste', 'Oeste', 'arrow-left', 5),
        ('orientation', 'Noreste', 'Noreste', 'arrow-up-right', 6),
        ('orientation', 'Noroeste', 'Noroeste', 'arrow-up-left', 7),
        ('orientation', 'Sureste', 'Sureste', 'arrow-down-right', 8),
        ('orientation', 'Suroeste', 'Suroeste', 'arrow-down-left', 9),
        ('condition', '', 'Sin preferencia', '', 1),
        ('condition', 'A estrenar', 'A estrenar', 'sparkles', 2),
        ('condition', 'Usado', 'Usado', 'home', 3),
        ('condition', 'A reciclar', 'A reciclar', 'wrench', 4),
        ('condition', 'En construcción', 'En construcción', 'hard-hat', 5),
        ('age', '', 'Indiferente', '', 1),
        ('age', 'Hasta 5 años', 'Hasta 5 años', 'clock', 2),
        ('age', '5 a 15 años', '5 a 15 años', 'clock', 3),
        ('age', '15 a 30 años', '15 a 30 años', 'clock', 4),
        ('age', 'Más de 30 años', 'Más de 30 años', 'clock', 5),
        ('budget_range', 'hasta_200k', 'Hasta $200k', 'dollar-sign', 1),
        ('budget_range', '200k_500k', '$200k - $500k', 'dollar-sign', 2),
        ('budget_range', '500k_1m', '$500k - $1M', 'dollar-sign', 3),
        ('budget_range', '1m_2m', '$1M - $2M', 'dollar-sign', 4),
        ('budget_range', 'mas_2m', 'Mas de $2M', 'dollar-sign', 5),
        ('province', 'Buenos Aires', 'Buenos Aires', '', 1),
        ('province', 'CABA', 'CABA', '', 2),
        ('province', 'Catamarca', 'Catamarca', '', 3),
        ('province', 'Chaco', 'Chaco', '', 4),
        ('province', 'Chubut', 'Chubut', '', 5),
        ('province', 'Cordoba', 'Cordoba', '', 6),
        ('province', 'Corrientes', 'Corrientes', '', 7),
        ('province', 'Entre Rios', 'Entre Rios', '', 8),
        ('province', 'Formosa', 'Formosa', '', 9),
        ('province', 'Jujuy', 'Jujuy', '', 10),
        ('province', 'La Pampa', 'La Pampa', '', 11),
        ('province', 'La Rioja', 'La Rioja', '', 12),
        ('province', 'Mendoza', 'Mendoza', '', 13),
        ('province', 'Misiones', 'Misiones', '', 14),
        ('province', 'Neuquen', 'Neuquen', '', 15),
        ('province', 'Rio Negro', 'Rio Negro', '', 16),
        ('province', 'Salta', 'Salta', '', 17),
        ('province', 'San Juan', 'San Juan', '', 18),
        ('province', 'San Luis', 'San Luis', '', 19),
        ('province', 'Santa Cruz', 'Santa Cruz', '', 20),
        ('province', 'Santa Fe', 'Santa Fe', '', 21),
        ('province', 'Santiago del Estero', 'Santiago del Estero', '', 22),
        ('province', 'Tierra del Fuego', 'Tierra del Fuego', '', 23),
        ('province', 'Tucuman', 'Tucuman', '', 24),
        ('country', 'Argentina', 'Argentina', 'globe', 1),
        ('country', 'Uruguay', 'Uruguay', 'globe', 2),
        ('country', 'Chile', 'Chile', 'globe', 3),
        ('country', 'Brasil', 'Brasil', 'globe', 4),
        ('country', 'Paraguay', 'Paraguay', 'globe', 5),
        ('country', 'Bolivia', 'Bolivia', 'globe', 6),
        ('country', 'Colombia', 'Colombia', 'globe', 7),
        ('country', 'Mexico', 'Mexico', 'globe', 8),
        ('country', 'España', 'España', 'globe', 9),
        ('country', 'Estados Unidos', 'Estados Unidos', 'globe', 10),
        ('country', 'Portugal', 'Portugal', 'globe', 11),
        ('architectural_style', 'Moderno', 'Moderno', '', 1),
        ('architectural_style', 'Classico', 'Classico', '', 2),
        ('architectural_style', 'Minimalista', 'Minimalista', '', 3),
        ('architectural_style', 'Industrial', 'Industrial', '', 4),
        ('architectural_style', 'Rustico', 'Rustico', '', 5),
        ('architectural_style', 'Contemporaneo', 'Contemporaneo', '', 6),
        ('architectural_style', 'Vanguardista', 'Vanguardista', '', 7),
        ('architectural_style', 'Tradicional', 'Tradicional', '', 8),
        ('architectural_style', 'Mediterraneo', 'Mediterraneo', '', 9),
        ('architectural_style', 'Nordico', 'Nordico', '', 10),
        ('architectural_style', 'Colonial', 'Colonial', '', 11),
        ('architectural_style', 'Art Deco', 'Art Deco', '', 12),
        ('architectural_style', 'Bauhaus', 'Bauhaus', '', 13),
        ('architectural_style', 'Organico', 'Organico', '', 14),
        ('architectural_style', 'High-Tech', 'High-Tech', '', 15),
        ('architectural_style', 'Neoclasic', 'Neoclasic', '', 16),
        ('architectural_style', 'Gotico', 'Gotico', '', 17),
        ('architectural_style', 'Barroco', 'Barroco', '', 18),
        ('architectural_style', 'Renacentista', 'Renacentista', '', 19),
        ('architectural_style', 'Otro', 'Otro', '', 20),
        ('amenities', 'SUM', 'SUM', '', 1),
        ('amenities', 'Terraza', 'Terraza', '', 2),
        ('amenities', 'Quincho', 'Quincho', '', 3),
        ('amenities', 'Jardin', 'Jardin', '', 4),
        ('amenities', 'Pileta cubierta', 'Pileta cubierta', '', 5),
        ('amenities', 'Barrio privado', 'Barrio privado', '', 6),
        ('amenities', 'Seguridad 24h', 'Seguridad 24h', '', 7),
        ('amenities', 'Club house', 'Club house', '', 8),
        ('amenities', 'Canchas deportivas', 'Canchas deportivas', '', 9),
        ('amenities', 'Lagunas artificiales', 'Lagunas artificiales', '', 10),
        ('amenities', 'Terraza panoramica', 'Terraza panoramica', '', 11),
        ('amenities', 'Jacuzzi', 'Jacuzzi', '', 12),
        ('amenities', 'Vista 360', 'Vista 360', '', 13),
        ('amenities', 'Vitrina', 'Vitrina', '', 14),
        ('amenities', 'Deposito', 'Deposito', '', 15),
        ('amenities', 'Bano comercial', 'Bano comercial', '', 16),
        ('amenities', 'Aire acondicionado', 'Aire acondicionado', '', 17),
        ('amenities', 'Piscina Infinity', 'Piscina Infinity', '', 18),
        ('amenities', 'Bodega', 'Bodega', '', 19),
        ('amenities', 'Gimnasio Privado', 'Gimnasio Privado', '', 20),
        ('amenities', 'Domotica Avanzada', 'Domotica Avanzada', '', 21),
        ('amenities', 'Helipad', 'Helipad', '', 22),

    ]


    for cat, val, lbl, icon, order in FORM_OPTIONS_SEED:
        cursor.execute(
            'INSERT OR IGNORE INTO form_options (category, value, label, icon, sort_order) VALUES (?, ?, ?, ?, ?)',
            (cat, val, lbl, icon, order)
        )


    cursor.execute('''
        CREATE TABLE IF NOT EXISTS phone_area_codes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT NOT NULL,
            city TEXT NOT NULL,
            province TEXT NOT NULL DEFAULT '',
            country TEXT NOT NULL DEFAULT 'Argentina',
            country_code TEXT NOT NULL DEFAULT '+54',
            sort_order INTEGER DEFAULT 0,
            is_active INTEGER NOT NULL DEFAULT 1,
            UNIQUE(code, country_code)
        )
    ''')

    cursor.execute('CREATE INDEX IF NOT EXISTS idx_phone_area_country ON phone_area_codes(country_code)')

    cursor.execute('CREATE INDEX IF NOT EXISTS idx_phone_area_code ON phone_area_codes(code)')


    PHONE_AREA_CODES_SEED = [
        ('11', 'Buenos Aires / CABA', 'CABA', 'Argentina', '+54', 1),
        ('220', 'San Nicolás', 'Buenos Aires', 'Argentina', '+54', 2),
        ('221', 'La Plata', 'Buenos Aires', 'Argentina', '+54', 3),
        ('223', 'Mar del Plata', 'Buenos Aires', 'Argentina', '+54', 4),
        ('236', 'Junín', 'Buenos Aires', 'Argentina', '+54', 5),
        ('237', 'Olavarría', 'Buenos Aires', 'Argentina', '+54', 6),
        ('249', 'Tandil', 'Buenos Aires', 'Argentina', '+54', 7),
        ('2262', 'Necochea', 'Buenos Aires', 'Argentina', '+54', 8),
        ('261', 'Mendoza', 'Mendoza', 'Argentina', '+54', 9),
        ('260', 'San Rafael', 'Mendoza', 'Argentina', '+54', 10),
        ('264', 'San Juan', 'San Juan', 'Argentina', '+54', 11),
        ('2622', 'Tupungato', 'Mendoza', 'Argentina', '+54', 12),
        ('2655', 'Malargüe', 'Mendoza', 'Argentina', '+54', 14),
        ('2656', 'La Paz', 'Mendoza', 'Argentina', '+54', 15),
        ('266', 'San Luis', 'San Luis', 'Argentina', '+54', 16),
        ('280', 'San Miguel de Tucumán', 'Tucumán', 'Argentina', '+54', 17),
        ('3865', 'Concepción', 'Tucumán', 'Argentina', '+54', 18),
        ('3863', 'Monteros', 'Tucumán', 'Argentina', '+54', 19),
        ('291', 'Bahía Blanca', 'Buenos Aires', 'Argentina', '+54', 20),
        ('294', 'Santiago del Estero', 'Santiago del Estero', 'Argentina', '+54', 21),
        ('298', 'San Carlos de Bariloche', 'Río Negro', 'Argentina', '+54', 22),
        ('299', 'Neuquén', 'Neuquén', 'Argentina', '+54', 23),
        ('341', 'Rosario', 'Santa Fe', 'Argentina', '+54', 24),
        ('342', 'Santa Fe', 'Santa Fe', 'Argentina', '+54', 25),
        ('343', 'Paraná', 'Entre Ríos', 'Argentina', '+54', 26),
        ('345', 'Concepción del Uruguay', 'Entre Ríos', 'Argentina', '+54', 27),
        ('346', 'Alisos', 'Tucumán', 'Argentina', '+54', 28),
        ('348', 'Venado Tuerto', 'Santa Fe', 'Argentina', '+54', 29),
        ('351', 'Córdoba', 'Córdoba', 'Argentina', '+54', 30),
        ('353', 'Villa María', 'Córdoba', 'Argentina', '+54', 31),
        ('358', 'Río Cuarto', 'Córdoba', 'Argentina', '+54', 32),
        ('362', 'Resistencia', 'Chaco', 'Argentina', '+54', 33),
        ('364', 'Formosa', 'Formosa', 'Argentina', '+54', 34),
        ('370', 'Posadas', 'Misiones', 'Argentina', '+54', 35),
        ('3777', 'Goya', 'Corrientes', 'Argentina', '+54', 36),
        ('376', 'Eldorado', 'Misiones', 'Argentina', '+54', 37),
        ('3757', 'Puerto Iguazú', 'Misiones', 'Argentina', '+54', 38),
        ('3755', 'Oberá', 'Misiones', 'Argentina', '+54', 39),
        ('379', 'Corrientes', 'Corrientes', 'Argentina', '+54', 40),
        ('381', 'Tucumán', 'Tucumán', 'Argentina', '+54', 41),
        ('383', 'San Fernando del Valle de Catamarca', 'Catamarca', 'Argentina', '+54', 42),
        ('385', 'La Rioja', 'La Rioja', 'Argentina', '+54', 43),
        ('387', 'San Salvador de Jujuy', 'Jujuy', 'Argentina', '+54', 44),
        ('388', 'Salta', 'Salta', 'Argentina', '+54', 45),
        ('3541', 'Villa Carlos Paz', 'Córdoba', 'Argentina', '+54', 46),
        ('3543', 'Cosquín', 'Córdoba', 'Argentina', '+54', 47),
        ('3544', 'Alta Gracia', 'Córdoba', 'Argentina', '+54', 48),
        ('3546', 'Mina Clavero', 'Córdoba', 'Argentina', '+54', 49),
        ('3547', 'Cruz del Eje', 'Córdoba', 'Argentina', '+54', 50),
        ('3563', 'Rafaela', 'Santa Fe', 'Argentina', '+54', 51),
        ('3564', 'Reconquista', 'Santa Fe', 'Argentina', '+54', 52),
        ('3571', 'Casilda', 'Santa Fe', 'Argentina', '+54', 53),
        ('3825', 'Añatuya', 'Santiago del Estero', 'Argentina', '+54', 54),
        ('3832', 'Fiambalá', 'Catamarca', 'Argentina', '+54', 55),
        ('3835', 'Andalgalá', 'Catamarca', 'Argentina', '+54', 56),
        ('3844', 'Chilecito', 'La Rioja', 'Argentina', '+54', 57),
        ('3855', 'Chacabuco', 'Buenos Aires', 'Argentina', '+54', 58),
        ('3861', 'Orán', 'Salta', 'Argentina', '+54', 59),
        ('3862', 'Tartagal', 'Salta', 'Argentina', '+54', 60),
        ('3865', 'Cafayate', 'Salta', 'Argentina', '+54', 61),
        ('3873', 'Humahuaca', 'Jujuy', 'Argentina', '+54', 62),
        ('3876', 'Tilcara', 'Jujuy', 'Argentina', '+54', 63),
        ('2901', 'Viedma', 'Río Negro', 'Argentina', '+54', 64),
        ('2920', 'Choele Choel', 'Río Negro', 'Argentina', '+54', 65),
        ('2925', 'Cipolletti', 'Río Negro', 'Argentina', '+54', 66),
        ('2926', 'General Roca', 'Río Negro', 'Argentina', '+54', 67),
        ('3751', 'Curuzú Cuatiá', 'Corrientes', 'Argentina', '+54', 68),
        ('3772', 'Paso de los Libres', 'Corrientes', 'Argentina', '+54', 69),
        ('3775', 'Monte Caseros', 'Corrientes', 'Argentina', '+54', 70),
        ('2', 'Montevideo', 'Montevideo', 'Uruguay', '+598', 1),
        ('42', 'Punta del Este', 'Maldonado', 'Uruguay', '+598', 2),
        ('44', 'Colonia del Sacramento', 'Colonia', 'Uruguay', '+598', 3),
        ('55', 'Salto', 'Salto', 'Uruguay', '+598', 4),
        ('473', 'Rivera', 'Rivera', 'Uruguay', '+598', 5),
        ('2', 'Santiago', 'Metropolitana de Santiago', 'Chile', '+56', 1),
        ('32', 'Valparaíso', 'Valparaíso', 'Chile', '+56', 2),
        ('33', 'Viña del Mar', 'Valparaíso', 'Chile', '+56', 3),
        ('41', 'Concepción', 'Biobío', 'Chile', '+56', 4),
        ('45', 'Antofagasta', 'Antofagasta', 'Chile', '+56', 5),
        ('51', 'La Serena', 'Coquimbo', 'Chile', '+56', 6),
        ('61', 'Temuco', 'Araucanía', 'Chile', '+56', 7),
        ('63', 'Osorno', 'Los Lagos', 'Chile', '+56', 8),
        ('65', 'Puerto Montt', 'Los Lagos', 'Chile', '+56', 9),
        ('67', 'Punta Arenas', 'Magallanes', 'Chile', '+56', 10),
        ('11', 'São Paulo', 'São Paulo', 'Brasil', '+55', 1),
        ('21', 'Rio de Janeiro', 'Rio de Janeiro', 'Brasil', '+55', 2),
        ('31', 'Belo Horizonte', 'Minas Gerais', 'Brasil', '+55', 3),
        ('41', 'Curitiba', 'Paraná', 'Brasil', '+55', 4),
        ('51', 'Porto Alegre', 'Rio Grande do Sul', 'Brasil', '+55', 5),
        ('61', 'Brasília', 'Distrito Federal', 'Brasil', '+55', 6),
        ('71', 'Salvador', 'Bahía', 'Brasil', '+55', 7),
        ('81', 'Recife', 'Pernambuco', 'Brasil', '+55', 8),
        ('85', 'Fortaleza', 'Ceará', 'Brasil', '+55', 9),
        ('21', 'Asunción', 'Central', 'Paraguay', '+595', 1),
        ('61', 'Ciudad del Este', 'Alto Paraná', 'Paraguay', '+595', 2),
        ('71', 'Encarnación', 'Itapúa', 'Paraguay', '+595', 3),
        ('2', 'La Paz', 'La Paz', 'Bolivia', '+591', 1),
        ('3', 'Santa Cruz', 'Santa Cruz', 'Bolivia', '+591', 2),
        ('4', 'Cochabamba', 'Cochabamba', 'Bolivia', '+591', 3),
        ('1', 'Bogotá', 'Cundinamarca', 'Colombia', '+57', 1),
        ('2', 'Cali', 'Valle del Cauca', 'Colombia', '+57', 2),
        ('4', 'Medellín', 'Antioquia', 'Colombia', '+57', 3),
        ('5', 'Barranquilla', 'Atlántico', 'Colombia', '+57', 4),
        ('55', 'Ciudad de México', 'CDMX', 'México', '+52', 1),
        ('33', 'Guadalajara', 'Jalisco', 'México', '+52', 2),
        ('81', 'Monterrey', 'Nuevo León', 'México', '+52', 3),
        ('646', 'Tijuana', 'Baja California', 'México', '+52', 4),
        ('91', 'Madrid', 'Madrid', 'España', '+34', 1),
        ('93', 'Barcelona', 'Cataluña', 'España', '+34', 2),
        ('95', 'Sevilla', 'Andalucía', 'España', '+34', 3),
        ('96', 'Valencia', 'Valencia', 'España', '+34', 4),
        ('94', 'Bilbao', 'País Vasco', 'España', '+34', 5),
        ('201', 'New Jersey', 'NJ', 'Estados Unidos', '+1', 1),
        ('212', 'New York', 'NY', 'Estados Unidos', '+1', 2),
        ('310', 'Los Angeles', 'CA', 'Estados Unidos', '+1', 3),
        ('305', 'Miami', 'FL', 'Estados Unidos', '+1', 4),
        ('415', 'San Francisco', 'CA', 'Estados Unidos', '+1', 5),
        ('713', 'Houston', 'TX', 'Estados Unidos', '+1', 6),

    ]


    for code, city, province, country, cc, order in PHONE_AREA_CODES_SEED:
        cursor.execute(
            'INSERT OR IGNORE INTO phone_area_codes (code, city, province, country, country_code, sort_order) VALUES (?, ?, ?, ?, ?, ?)',
            (code, city, province, country, cc, order)
        )


    # Backfill/migration: remove rows seeded by mistake (mobile prefixes that

    # collide with mobile detection) and fix mislabeled Colombia areas, but only

    # when they still hold the original seed values (never clobber admin edits).

    cursor.execute(
        "DELETE FROM phone_area_codes WHERE (country_code = '+56' AND code = '9') "
        "OR (country_code = '+598' AND code = '99') OR (country_code = '+57' AND code = '3')"

    )

    cursor.execute(
        "UPDATE phone_area_codes SET city = 'Cali', province = 'Valle del Cauca' "
        "WHERE country_code = '+57' AND code = '2' AND city = 'Medellín'"

    )

    cursor.execute(
        "UPDATE phone_area_codes SET city = 'Medellín', province = 'Antioquia' "
        "WHERE country_code = '+57' AND code = '4' AND city = 'Barranquilla'"

    )


    if not _is_prod():
        _clean_lead_test_data(cursor)


    cursor.execute('SELECT COUNT(*) FROM users')

    if cursor.fetchone()[0] == 0:
        if _is_prod():
            admin_password = os.environ.get('ADMIN_INITIAL_PASSWORD')
            if not admin_password:
                import secrets
                admin_password = secrets.token_urlsafe(12)
                pw_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.admin_initial_password')
                try:
                    with open(pw_file, 'w') as f:
                        f.write(admin_password + '\n')
                    os.chmod(pw_file, 0o600)
                    logger.info('Admin user created. Initial password saved to .admin_initial_password')
                except OSError as e:
                    logger.warning('Could not write .admin_initial_password: %s', e)
                    logger.info('Admin password (copy it NOW): %s', admin_password)
            else:
                logger.info('Admin user created with password from ADMIN_INITIAL_PASSWORD env')
        else:
            admin_password = 'admin123'
        cursor.execute('INSERT INTO users (username, email, hash, role) VALUES (?, ?, ?, ?)',
                      ('admin', 'admin@archestate.local', generate_password_hash(admin_password), 'admin'))

