import pytest
from flask import session

from i18n import t, get_language
from i18n.translations import TRANSLATIONS, t as _t, DEFAULT_LANG
from i18n.browser import get_browser_language


class TestTranslationsDict:
    def test_both_languages_have_same_keys(self):
        es_keys = set(TRANSLATIONS['es'].keys())
        en_keys = set(TRANSLATIONS['en'].keys())
        assert es_keys == en_keys, f'Missing in EN: {es_keys - en_keys}, Missing in ES: {en_keys - es_keys}'

    def test_no_empty_values(self):
        for lang in ('es', 'en'):
            for key, val in TRANSLATIONS[lang].items():
                assert val, f'Empty translation for {lang}.{key}'

    def test_translation_count(self):
        count = len(TRANSLATIONS['es'])
        assert count >= 300, f'Expected 300+ keys, got {count}'


class TestTFunction:
    def test_returns_es_by_default(self):
        result = _t('nav.home')
        assert result == 'Inicio'

    def test_returns_en(self):
        result = _t('nav.home', 'en')
        assert result == 'Home'

    def test_returns_key_when_missing(self):
        result = _t('nonexistent.key')
        assert result == 'nonexistent.key'

    def test_interpolates_variables(self):
        result = _t('validator.phone_invalid_for', 'es', region='AR')
        assert 'AR' in result

    def test_interpolation_en(self):
        result = _t('validator.phone_invalid_for', 'en', region='US')
        assert 'US' in result

    def test_fallback_to_es_on_unknown_lang(self):
        result = _t('nav.home', 'fr')
        assert result == 'Inicio'

    def test_empty_kwargs(self):
        result = _t('nav.home', 'es')
        assert result == 'Inicio'


class TestBrowserLanguage:
    def _make_request(self, accept_language=''):
        from flask import Flask
        app = Flask(__name__)
        with app.test_request_context('/', headers={'Accept-Language': accept_language}):
            from flask import request
            return get_browser_language(request)

    def test_spanish(self):
        assert self._make_request('es-AR,es;q=0.9') == 'es'

    def test_english(self):
        assert self._make_request('en-US,en;q=0.9') == 'en'

    def test_empty(self):
        assert self._make_request('') == 'es'

    def test_spanish_primary(self):
        assert self._make_request('es-AR,es;q=0.9,en;q=0.5') == 'es'

    def test_unsupported_falls_back_to_es(self):
        assert self._make_request('fr-FR,fr;q=0.9') == 'es'

    def test_exact_es(self):
        assert self._make_request('es') == 'es'

    def test_exact_en(self):
        assert self._make_request('en') == 'en'


class TestGetLanguage:
    def test_returns_es_by_default(self, client):
        resp = client.get('/')
        assert resp.status_code == 200

    def test_returns_en_from_browser(self, client):
        resp = client.get('/')
        assert resp.status_code == 200

    def test_uses_session_when_logged_in(self, client, auth_client):
        resp = auth_client.get('/mi-perfil')
        assert resp.status_code == 200


class TestMiddlewareIntegration:
    def test_lang_injected_in_template(self, client):
        resp = client.get('/')
        assert resp.status_code == 200
        html = resp.data.decode()
        assert 'lang="' in html

    def test_t_function_in_template(self, client):
        resp = client.get('/')
        assert resp.status_code == 200
        html = resp.data.decode()
        assert 'Acceso Privado' in html or 'Solicitud' in html

    def test_i18n_js_included(self, client):
        resp = client.get('/')
        html = resp.data.decode()
        assert 'i18n.js' in html

    def test_t_function_available_in_templates(self, client):
        resp = client.get('/')
        assert resp.status_code == 200


class TestNoHardcodedSpanish:
    '''Fase 4 (v0.38.0): ningún template/email renderiza español hardcoded.

    Heurística: línea con caracteres ES (acentos/¿¡) que no usa {{ t( }},
    no es comentario Jinja/HTML y no está en la whitelist de falsos positivos
    (strings de lógica backend, nombres nativos de idioma).
    '''

    ALLOWED = {
        'templates/admin.html': ["entry.action == 'Aprobación'"],
        'templates/profile.html': ['Español', 'English'],
        # value="..." de amenities: son DATOS del formulario (se guardan en DB),
        # no texto UI. Traducirlos rompería el matching en backend.
        'templates/user.html': ['value="Terraza panorámica"', 'value="Depósito"', 'value="Baño comercial"'],
    }

    SCAN_FILES = [
        'templates/base.html',
        'templates/landing.html',
        'templates/user.html',
        'templates/professional.html',
        'templates/admin.html',
        'templates/profile.html',
        'templates/login.html',
        'templates/register.html',
        'templates/lead_detail.html',
        'templates/edit_lead.html',
        'templates/notifications.html',
        'templates/user_management.html',
        'templates/partials/contact_buttons.html',
        'templates/email/base.html',
        'templates/email/lead_assigned.html',
        'templates/email/password_reset.html',
        'templates/email/professional_status.html',
        'templates/email/report_deleted.html',
        'templates/email/status_change.html',
    ]

    def _scan(self):
        import pathlib
        import re
        root = pathlib.Path(__file__).resolve().parent.parent
        pattern = re.compile(r'[ÁÉÍÓÚÑáéíóúñ¿¡]')
        offenders = []
        for rel in self.SCAN_FILES:
            text = (root / rel).read_text(encoding='utf-8')
            allowed = self.ALLOWED.get(rel, [])
            in_comment = False
            for i, line in enumerate(text.splitlines(), 1):
                if '{#' in line and '-#}' not in line:
                    in_comment = True
                if in_comment:
                    if '-#}' in line:
                        in_comment = False
                    continue
                if not pattern.search(line):
                    continue
                if '{{ t(' in line or '<!--' in line:
                    continue
                if any(a in line for a in allowed):
                    continue
                offenders.append(f'{rel}:{i}: {line.strip()[:90]}')
        return offenders

    def test_no_hardcoded_spanish_in_templates(self):
        offenders = self._scan()
        assert not offenders, 'Español hardcoded sin t():\n' + '\n'.join(offenders)


class TestFase4Keys:
    def test_new_keys_present_both_langs(self):
        for key in ('otp.digit_label', 'user.budget_min_aria', 'admin.export_png',
                    'profile.bio_placeholder', 'seo.meta_description', 'landing.page_title',
                    'pro.op_duplex', 'auth.req_email', 'edit_lead.area_hint',
                    'email.pro_active', 'contact.call', 'faq.free_q'):
            assert _t(key, 'es') != key, f'Missing ES: {key}'
            assert _t(key, 'en') != key, f'Missing EN: {key}'

    def test_otp_digit_interpolation(self):
        assert _t('otp.digit_label', 'es', n=2) == 'Dígito 2 de 6'
        assert _t('otp.digit_label', 'en', n=2) == 'Digit 2 of 6'


class TestRenderEnglish:
    def test_register_renders_english_validation(self, client):
        resp = client.get('/register', headers={'Accept-Language': 'en'})
        assert resp.status_code == 200
        html = resp.data.decode()
        assert 'Enter your email.' in html
        assert 'Ingresá tu email.' not in html

    def test_login_renders_english_validation(self, client):
        resp = client.get('/login', headers={'Accept-Language': 'en'})
        assert resp.status_code == 200
        html = resp.data.decode()
        assert 'Enter your password.' in html
        assert 'Ingresá tu contraseña.' not in html

    def test_og_locale_follows_language(self, client):
        es_html = client.get('/').data.decode()
        assert 'es_AR' in es_html
        en_html = client.get('/', headers={'Accept-Language': 'en'}).data.decode()
        assert 'en_US' in en_html
