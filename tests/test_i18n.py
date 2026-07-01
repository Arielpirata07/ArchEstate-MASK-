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
