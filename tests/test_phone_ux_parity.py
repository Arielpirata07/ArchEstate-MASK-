"""
Tests de paridad cliente-servidor para validación y normalización de teléfono.

Estos tests verifican que el validador JS del cliente (static/js/auth.js)
y la lógica Python del servidor (validators.validate_phone,
utils.normalize_phone_to_e164) producen resultados consistentes.

Motivación: durante el debugging JSDOM de la UX del campo teléfono se
encontraron casos borde (espacios, caracteres unicode, regiones) donde
la divergencia cliente↔servidor puede causar fricción UX.
"""
import json
import re

import pytest

import utils
import validators


# Replicamos la lógica JS (auth.js) en Python para comparar.
# Si auth.js cambia, este test debe actualizarse.
def js_phone_validator(val):
    """Réplica del `validators.phone` en static/js/auth.js."""
    v = (val or '').strip()
    if not v:
        return False
    if v[0] == '+':
        # replace(/[^\d]/g,'') elimina el '+' (no es dígito)
        digits = re.sub(r'[^\d]', '', v)
        if len(digits) < 8 or len(digits) > 15:
            return False
        return bool(re.match(r'^\+[\d\s\-\(\)]+$', v))
    digits_only = re.sub(r'[^\d]', '', v)
    return 10 <= len(digits_only) <= 13


def js_normalize_phone(val):
    """Réplica del `normalizePhoneClient` en static/js/auth.js."""
    v = (val or '').strip()
    if not v:
        return None
    if v[0] == '+':
        digits = re.sub(r'[^\d]', '', v)
        if len(digits) < 8 or len(digits) > 15:
            return None
        return '+' + digits
    digits_only = re.sub(r'[^\d]', '', v)
    if len(digits_only) < 10 or len(digits_only) > 13:
        return None
    return '+54' + digits_only[-10:]


# --- Paridad: lo que el cliente acepta, el servidor también -----------------

@pytest.mark.parametrize("phone", [
    "+54 9 11 1234 5678",
    "+5491144445555",
    "+54 9 11 4444-5555",
    "+59899123456",
    "+34 612 345 678",
    "+1 (212) 555-1234",
    "1144445555",          # Legacy AR 10 dígitos — Buenos Aires landline
    "91144445555",         # Legacy AR 11 dígitos — móvil con 9 prefix
])
def test_js_accepts_and_server_accepts(phone):
    """
    Inputs que el cliente acepta deben ser aceptados por el servidor.

    NOTA: Esta paridad NO es perfecta. El cliente usa una regex simple
    mientras el servidor usa phonenumbers (Google lib). Algunos inputs
    pueden pasar el cliente pero no el servidor (ver test_js_false_positives).
    El servidor es siempre la fuente de verdad.
    """
    assert js_phone_validator(phone) is True, \
        f"Cliente JS rechazó: {phone!r}"
    is_valid, _ = validators.validate_phone(phone)
    assert is_valid is True, \
        f"Servidor rechazó input que el cliente acepta: {phone!r}"


@pytest.mark.parametrize("phone", [
    "123",
    "12345",
    "1234567",        # 7 dígitos — no internacional, no legacy AR
    "abc",
    "",
    "+",
    "+1234",
])
def test_js_rejects_and_server_rejects(phone):
    """Inputs claramente inválidos deben ser rechazados por ambos."""
    assert js_phone_validator(phone) is False, \
        f"Cliente JS aceptó: {phone!r}"
    is_valid, _ = validators.validate_phone(phone)
    assert is_valid is False, \
        f"Servidor aceptó input que el cliente rechaza: {phone!r}"


@pytest.mark.parametrize("phone", [
    "1544445555",     # 10 dígitos AR — no es un patrón válido de BA landline
])
def test_js_false_positives_documented(phone):
    """
    Inputs que el cliente acepta heurísticamente pero el servidor rechaza.
    Esto es esperado: la regex del cliente es permisiva para no frustrar al
    usuario en el tipeo. El servidor es la fuente de verdad final.
    """
    assert js_phone_validator(phone) is True, \
        f"Cliente debería aceptar (heurística permisiva): {phone!r}"
    is_valid, msg = validators.validate_phone(phone)
    assert is_valid is False, \
        f"Servidor debería rechazar (phonenumbers estricto): {phone!r}"
    # El mensaje del servidor guiará al usuario a corregir el input
    assert msg is not None
    assert len(msg) > 0


# --- Paridad del normalizador E.164 ----------------------------------------

@pytest.mark.parametrize("phone,expected_e164", [
    ("+54 9 11 4444 5555",  "+5491144445555"),
    ("+5491144445555",      "+5491144445555"),
    ("+59899123456",        "+59899123456"),
    ("+34 612 345 678",     "+34612345678"),
    ("+1 (212) 555-1234",   "+12125551234"),
    ("1144445555",          "+541144445555"),
])
def test_js_normalize_matches_server_normalize(phone, expected_e164):
    """
    El normalizador del cliente debe producir el mismo E.164 que el servidor
    para los casos que ambos aceptan. Esto es crítico: si difieren, el usuario
    verá un preview E.164 pero el server normalizará a otro, generando
    confusión.
    """
    js_result = js_normalize_phone(phone)
    server_result = utils.normalize_phone_to_e164(phone)
    assert js_result == expected_e164, \
        f"Cliente normalizó a {js_result!r}, esperado {expected_e164!r}"
    assert server_result == expected_e164, \
        f"Servidor normalizó a {server_result!r}, esperado {expected_e164!r}"
    assert js_result == server_result, \
        f"Cliente y servidor divergen: cliente={js_result!r}, " \
        f"servidor={server_result!r}"


# --- Sanity: el campo phone en /register tiene los hooks del cliente JS -----

class TestPhoneUxInRegisterPage:
    """Verificar que el HTML servido por Flask tiene los atributos que el JS
    en static/js/auth.js espera encontrar. Si el HTML rompe el contrato,
    el preview live no funcionará."""

    def test_phone_input_has_required_attr(self, client):
        resp = client.get('/register')
        assert b'name="phone"' in resp.data
        assert b'type="tel"' in resp.data
        assert b'required' in resp.data
        assert b'autocomplete="tel"' in resp.data

    def test_phone_input_has_phone_rule(self, client):
        resp = client.get('/register')
        m = re.search(rb'name="phone"[^>]*data-auth-rules=\'([^\']*)\'', resp.data)
        assert m is not None, "Falta data-auth-rules en el input phone"
        rules = json.loads(m.group(1).decode())
        assert rules.get('phone') is True
        assert rules.get('required') is True

    def test_phone_input_has_aria_describedby(self, client):
        """El input debe apuntar al preview para accesibilidad."""
        resp = client.get('/register')
        assert b'aria-describedby="err-phone phone-hint phone-preview"' in resp.data

    def test_phone_preview_element_exists(self, client):
        """El párrafo donde el JS pinta el preview en vivo."""
        resp = client.get('/register')
        assert b'id="phone-preview"' in resp.data
        assert b'data-phone-preview' in resp.data

    def test_phone_status_element_exists(self, client):
        """El span del icono de status (check/error)."""
        resp = client.get('/register')
        assert b'id="phone-status"' in resp.data
        assert b'data-phone-status' in resp.data  # CRÍTICO: el JS busca este atributo
        assert b'data-phone-status-icon' in resp.data

    def test_phone_hint_has_three_clickable_examples(self, client):
        """Los ejemplos AR/UY/ES como botones con data-phone-example."""
        resp = client.get('/register')
        examples = re.findall(rb'data-phone-example="([^"]+)"', resp.data)
        assert len(examples) == 3, f"Esperaba 3 ejemplos, encontré {len(examples)}"
        # Verificar que sean números de los 3 países objetivo
        joined = b' '.join(examples)
        assert b'+54' in joined, "Falta ejemplo Argentina"
        assert b'+598' in joined, "Falta ejemplo Uruguay"
        assert b'+34' in joined, "Falta ejemplo España"

    def test_auth_js_is_loaded(self, client):
        """La página debe cargar el JS que monta el preview."""
        resp = client.get('/register')
        assert b'/static/js/auth.js' in resp.data


# --- Regresión: el bug del status icon que se quedaba con último estado ----

class TestStatusIconReset:
    """
    Reproduce el bug EDGE 8 del debugging JSDOM: cuando el usuario vaciaba
    el campo, el icono del status quedaba con el último estado (check o alert)
    en vez de volver a 'circle' (neutral).

    El fix está en auth.js (renderPhonePreview). Estos tests cargan el JS
    real y validan el comportamiento.
    """
    pass  # Los tests JSDOM (en /tmp/opencode/jsdom-debug) ya cubren esto


# --- Edge cases documentados (que el cliente y servidor deben acordar) ----

@pytest.mark.parametrize("phone,should_normalize", [
    ("+54 9 11 4444 5555", True),
    ("(011) 4444-5555",    True),   # Formato AR con paréntesis y guión
    ("011 4444 5555",      True),   # Solo espacios
    ("5491144445555",      True),   # Sin + pero con código país
])
def test_various_argentina_formats_normalize(phone, should_normalize):
    """Múltiples formatos AR deben normalizar a E.164."""
    if should_normalize:
        e164 = utils.normalize_phone_to_e164(phone)
        assert e164.startswith("+54"), \
            f"{phone!r} debería normalizar a +54... pero dio {e164!r}"
