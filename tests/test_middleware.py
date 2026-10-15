import uuid

import pytest
from flask import g
from werkzeug.security import generate_password_hash

import models


def _make_user(db, role='client', password='Test1234'):
    unique = uuid.uuid4().hex[:8]
    username = f'mw_{unique}'
    cursor = db.execute(
        'INSERT INTO users (username, email, hash, role, phone, phone_format_valid) '
        'VALUES (?, ?, ?, ?, ?, 1)',
        (username, f'{unique}@example.com', generate_password_hash(password), role, '+5491112345678')
    )
    user_id = cursor.lastrowid
    db.commit()
    return user_id, username, password


def _login_remember(client, username, password):
    return client.post('/login', data={'username': username, 'password': password, 'remember': 'on'},
                       follow_redirects=False)


def _remember_cookie(resp):
    for k, v in resp.headers.items():
        if k.lower() == 'set-cookie' and 'remember_token' in v:
            return v.split('remember_token=')[1].split(';')[0]
    return None


class TestRememberRestore:
    def test_valid_token_restores_session(self, client, db):
        user_id, username, password = _make_user(db)
        cookie = _remember_cookie(_login_remember(client, username, password))
        assert cookie
        c2 = client.application.test_client()
        c2.set_cookie('remember_token', cookie)
        resp = c2.get('/mi-perfil')
        assert resp.status_code == 200

    def test_invalid_token_no_session(self, client, db):
        _make_user(db)
        c2 = client.application.test_client()
        c2.set_cookie('remember_token', 'bogus:also-bogus')
        resp = c2.get('/mi-perfil', follow_redirects=False)
        assert resp.status_code in (301, 302)

    def test_disabled_user_token_revoked(self, client, db):
        user_id, username, password = _make_user(db)
        cookie = _remember_cookie(_login_remember(client, username, password))
        assert cookie
        db.execute('UPDATE users SET is_active = 0 WHERE id = ?', (user_id,))
        db.commit()
        c2 = client.application.test_client()
        c2.set_cookie('remember_token', cookie)
        resp = c2.get('/mi-perfil', follow_redirects=False)
        assert resp.status_code in (301, 302)


class TestRequestScopedConnection:
    def test_same_request_reuses_connection(self, app):
        with app.test_request_context('/'):
            from models import get_db_connection
            a = get_db_connection()
            b = get_db_connection()
            assert a._real is b._real

    def test_teardown_closes_shared_connection(self, app):
        with app.test_request_context('/'):
            from models import get_db_connection
            get_db_connection()
            assert g._shared_db_conn is not None
        with app.test_request_context('/'):
            assert getattr(g, '_shared_db_conn', None) is None

    def test_explicit_close_is_noop_inside_request(self, app, db):
        with app.test_request_context('/'):
            from models import get_db_connection
            conn = get_db_connection()
            conn.close()
            row = conn.execute('SELECT 1').fetchone()
            assert row is not None


class TestLanguageInjection:
    def test_lang_in_html_tag(self, client):
        html = client.get('/').data.decode()
        assert 'lang="es"' in html

    def test_english_via_header(self, client):
        html = client.get('/', headers={'Accept-Language': 'en'}).data.decode()
        assert 'lang="en"' in html
