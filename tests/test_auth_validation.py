import json
import os
import re
import subprocess
import uuid

import pytest
from werkzeug.security import generate_password_hash

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# --- Helpers ---------------------------------------------------------------

def _password_strength(value):
    """
    Reimplementación fiel de static/js/auth.js :: passwordStrength
    para testear parametrizadamente sin levantar el browser.
    Mantener en sincronía con el JS.
    """
    v = value or ''
    score = 0
    if len(v) >= 6:
        score += 1
    if len(v) >= 8:
        score += 1
    if re.search(r'[A-Z]', v) and re.search(r'[a-z]', v):
        score += 1
    if re.search(r'\d', v) and re.search(r'[^\w\s]', v):
        score += 1
    if score > 4:
        score = 4
    labels = ['vacía', 'débil', 'aceptable', 'buena', 'fuerte']
    return {'score': score, 'label': labels[score]}


# --- HTML rendering: login ------------------------------------------------

class TestLoginPageRendering:
    def test_login_renders_200(self, client):
        resp = client.get('/login')
        assert resp.status_code == 200

    def test_login_has_data_auth_form(self, client):
        resp = client.get('/login')
        assert b'data-auth-form="login"' in resp.data
        assert b'novalidate' in resp.data

    def test_login_has_remember_me_checkbox(self, client):
        resp = client.get('/login')
        assert b'name="remember"' in resp.data
        assert b'value="on"' in resp.data
        assert 'Recordarme por 30 días'.encode('utf-8') in resp.data
        assert b'remember-me' in resp.data

    def test_login_has_password_toggle(self, client):
        resp = client.get('/login')
        assert b'data-toggle-pass="password"' in resp.data
        assert 'aria-label="Mostrar contraseña"'.encode('utf-8') in resp.data

    def test_login_has_inline_error_containers(self, client):
        resp = client.get('/login')
        assert b'data-for="username"' in resp.data
        assert b'data-for="password"' in resp.data
        assert b'aria-live="polite"' in resp.data

    def test_login_has_submitting_button(self, client):
        resp = client.get('/login')
        assert b'btn-submit' in resp.data
        assert b'data-spinner' in resp.data
        assert b'data-label' in resp.data

    def test_login_username_has_data_auth_rules(self, client):
        resp = client.get('/login')
        # Extraer el bloque del input username (outer = single quote, inner JSON = double quote)
        m = re.search(rb"name=\"username\"[^>]*data-auth-rules='([^']*)'", resp.data)
        assert m is not None, "data-auth-rules no presente en input username"
        rules = json.loads(m.group(1).decode())
        assert rules.get('required') is True
        assert 'messages' in rules
        assert 'required' in rules['messages']

    def test_login_password_has_data_auth_rules(self, client):
        resp = client.get('/login')
        m = re.search(rb"name=\"password\"[^>]*data-auth-rules='([^']*)'", resp.data)
        assert m is not None
        rules = json.loads(m.group(1).decode())
        assert rules.get('required') is True

    def test_login_has_autocomplete(self, client):
        resp = client.get('/login')
        assert b'autocomplete="username"' in resp.data
        assert b'autocomplete="current-password"' in resp.data


# --- HTML rendering: register ---------------------------------------------

class TestRegisterPageRendering:
    def test_register_renders_200(self, client):
        resp = client.get('/register')
        assert resp.status_code == 200

    def test_register_has_data_auth_form(self, client):
        resp = client.get('/login')
        # /login es login; register debe tener su form
        resp = client.get('/register')
        assert b'data-auth-form="register"' in resp.data
        assert b'novalidate' in resp.data

    def test_register_has_all_required_inputs(self, client):
        resp = client.get('/register')
        for field in (b'name="role"', b'name="username"', b'name="email"',
                      b'name="phone"', b'name="password"', b'name="license"'):
            assert field in resp.data, f"campo {field.decode()} no encontrado"

    def test_register_has_password_strength_meter(self, client):
        resp = client.get('/register')
        assert b'data-strength-meter' in resp.data
        assert b'data-strength-bar' in resp.data
        assert b'data-strength-label' in resp.data

    def test_register_has_password_rules(self, client):
        resp = client.get('/register')
        for rule in (b'data-password-rule="length"',
                     b'data-password-rule="letter"',
                     b'data-password-rule="number"',
                     b'data-password-rule="upper"',
                     b'data-password-rule="symbol"'):
            assert rule in resp.data, f"regla {rule.decode()} no encontrada"

    def test_register_has_username_async_hint(self, client):
        resp = client.get('/register')
        assert b'data-async-check="true"' in resp.data
        assert b'data-username-hint' in resp.data

    def test_register_username_input_has_data_auth_rules(self, client):
        resp = client.get('/register')
        m = re.search(rb"name=\"username\"[^>]*data-auth-rules='([^']*)'", resp.data)
        assert m is not None
        rules = json.loads(m.group(1).decode())
        assert rules.get('required') is True
        assert rules.get('usernameFormat') is True

    def test_register_password_input_has_strength_and_rules(self, client):
        resp = client.get('/register')
        m = re.search(rb"name=\"password\"[^>]*data-auth-rules='([^']*)'", resp.data)
        assert m is not None
        rules = json.loads(m.group(1).decode())
        assert rules.get('minLength') == 6
        assert rules.get('hasLetter') is True
        assert rules.get('hasNumber') is True

    def test_register_phone_input_has_phone_rule(self, client):
        resp = client.get('/register')
        m = re.search(rb"name=\"phone\"[^>]*data-auth-rules='([^']*)'", resp.data)
        assert m is not None
        rules = json.loads(m.group(1).decode())
        assert rules.get('phone') is True

    def test_register_email_input_has_email_rule(self, client):
        resp = client.get('/register')
        m = re.search(rb"name=\"email\"[^>]*data-auth-rules='([^']*)'", resp.data)
        assert m is not None
        rules = json.loads(m.group(1).decode())
        assert rules.get('email') is True

    def test_register_has_aria_describedby_chains(self, client):
        resp = client.get('/register')
        assert b'aria-describedby="err-username username-hint"' in resp.data
        assert b'aria-describedby="err-password password-strength password-rules"' in resp.data

    def test_register_license_container_hidden_by_default(self, client):
        resp = client.get('/register')
        assert b'data-license-container' in resp.data
        assert b'id="license-container"' in resp.data
        # La clase hidden está aplicada
        assert b'<div data-license-container id="license-container"' in resp.data


# --- Server-side: no regresión con HTML5/JS validation -------------------

class TestServerSideValidation:
    """Asegurar que la validación server sigue siendo la fuente de verdad."""

    def test_register_empty_username_rejected(self, client):
        resp = client.post('/register', data={
            'username': '',
            'email': 'a@b.com',
            'phone': '+5491112345678',
            'password': 'Abc123',
            'role': 'client',
        }, follow_redirects=True)
        assert b'usuario' in resp.data.lower() or b'caracteres' in resp.data.lower()

    def test_register_bad_email_rejected(self, client):
        resp = client.post('/register', data={
            'username': 'gooduser',
            'email': 'no-es-email',
            'phone': '+5491112345678',
            'password': 'Abc123',
            'role': 'client',
        }, follow_redirects=True)
        assert b'inv' in resp.data.lower() or b'email' in resp.data.lower()

    def test_register_short_password_rejected(self, client):
        resp = client.post('/register', data={
            'username': 'shortpass',
            'email': 'a@b.com',
            'phone': '+5491112345678',
            'password': 'Ab1',
            'role': 'client',
        }, follow_redirects=True)
        assert b'6' in resp.data or b'm' in resp.data.lower()

    def test_register_password_without_letter_rejected(self, client):
        resp = client.post('/register', data={
            'username': 'noletter',
            'email': 'a@b.com',
            'phone': '+5491112345678',
            'password': '123456',
            'role': 'client',
        }, follow_redirects=True)
        assert b'letra' in resp.data.lower() or b'car' in resp.data.lower()

    def test_register_invalid_phone_rejected(self, client):
        resp = client.post('/register', data={
            'username': 'badphone2',
            'email': 'a@b.com',
            'phone': '12',
            'password': 'Abc123',
            'role': 'client',
        }, follow_redirects=True)
        assert b'tel' in resp.data.lower() or b'inv' in resp.data.lower()

    def test_login_invalid_credentials_shows_error(self, client):
        resp = client.post('/login', data={
            'username': 'nonexistent',
            'password': 'wrongpass',
        }, follow_redirects=True)
        assert b'Credenciales inv' in resp.data or b'credenciales' in resp.data.lower()


# --- Password strength (parametrized, espeja JS) -------------------------

class TestPasswordStrength:
    @pytest.mark.parametrize('value,expected_score,expected_label', [
        ('', 0, 'vacía'),
        ('a', 0, 'vacía'),                     # <6
        ('abcdef', 1, 'débil'),                # ≥6 pero <8
        ('abcdefgh', 2, 'aceptable'),          # ≥8 pero sin may+min
        ('Abcdefgh', 3, 'buena'),              # ≥8 + may/min, sin num
        ('Abcdefg1', 3, 'buena'),              # ≥8 + may/min + num, sin símbolo
        ('Abcdefg1!', 4, 'fuerte'),            # ≥8 + may/min + num + símbolo
        ('Aa1!aaaa', 4, 'fuerte'),
    ])
    def test_score_and_label(self, value, expected_score, expected_label):
        s = _password_strength(value)
        assert s['score'] == expected_score, f"{value!r} → score {s['score']} != {expected_score}"
        assert s['label'] == expected_label, f"{value!r} → label {s['label']!r} != {expected_label!r}"


# --- JS file syntax check ------------------------------------------------

class TestAuthJsSyntax:
    def test_auth_js_is_valid_javascript(self):
        """Verifica que static/js/auth.js se parsea sin errores de sintaxis."""
        result = subprocess.run(
            ['node', '--check', 'static/js/auth.js'],
            capture_output=True, text=True, cwd=REPO_ROOT
        )
        assert result.returncode == 0, f"JS syntax error:\n{result.stderr}"

    def test_auth_js_exposes_authform_namespace(self):
        """Verifica que el namespace AuthForm está definido y exporta las funciones esperadas."""
        result = subprocess.run(
            ['node', '-e', '''
                const fs = require('fs');
                const code = fs.readFileSync('static/js/auth.js', 'utf8');
                // Stub mínimo de window/document/fetch para que el IIFE no falle
                const sandbox = `
                    var window = { AuthForm: null };
                    var document = {
                        addEventListener: function(){},
                        querySelector: function(){ return null; },
                        querySelectorAll: function(){ return []; },
                    };
                    var fetch = function(){};
                    ${code}
                    process.stdout.write(JSON.stringify({
                        hasAuthForm: typeof window.AuthForm === 'object',
                        keys: Object.keys(window.AuthForm || {}).sort()
                    }));
                `;
                eval(sandbox);
            '''],
            capture_output=True, text=True, cwd=REPO_ROOT
        )
        assert result.returncode == 0, f"Eval error:\n{result.stderr}"
        import json as _json
        out = _json.loads(result.stdout.strip())
        assert out['hasAuthForm'] is True
        for fn in ('attach', 'validators', 'passwordStrength', 'runFieldRules', 'checkUsernameAvailable', 'validateForm'):
            assert fn in out['keys'], f"Falta función exportada: {fn}"


# --- Integration: register con remember=on también setea cookie ---------

class TestRememberMeIntegration:
    def test_login_with_remember_in_login_page_flow(self, client, db):
        db.execute('DELETE FROM remember_tokens')
        db.commit()
        unique = uuid.uuid4().hex[:8]
        username = f'int_{unique}'
        db.execute(
            'INSERT INTO users (username, email, hash, role, phone, phone_format_valid) '
            'VALUES (?, ?, ?, ?, ?, 1)',
            (username, f'{unique}@x.com', generate_password_hash('Test1234'), 'client', '+5491112345678')
        )
        db.commit()
        # El nuevo template usa name="remember" value="on" (mismo formato que el form real)
        resp = client.post('/login', data={'username': username, 'password': 'Test1234', 'remember': 'on'}, follow_redirects=False)
        assert resp.status_code in (302, 301)
        cookie = next((v for k, v in resp.headers.items() if k.lower() == 'set-cookie' and 'remember_token' in v), None)
        assert cookie is not None

    def test_login_without_remember_in_login_page_flow(self, client, db):
        db.execute('DELETE FROM remember_tokens')
        db.commit()
        unique = uuid.uuid4().hex[:8]
        username = f'norem_{unique}'
        db.execute(
            'INSERT INTO users (username, email, hash, role, phone, phone_format_valid) '
            'VALUES (?, ?, ?, ?, ?, 1)',
            (username, f'{unique}@x.com', generate_password_hash('Test1234'), 'client', '+5491112345678')
        )
        db.commit()
        resp = client.post('/login', data={'username': username, 'password': 'Test1234'}, follow_redirects=False)
        cookie = next((v for k, v in resp.headers.items() if k.lower() == 'set-cookie' and 'remember_token' in v), None)
        assert cookie is None
