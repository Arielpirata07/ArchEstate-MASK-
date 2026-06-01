import uuid
import sqlite3
from datetime import datetime, timedelta

import pytest
from werkzeug.security import generate_password_hash


def _make_user(client, db, password='Test1234'):
    """Crea un usuario y devuelve (user_id, username, password)."""
    unique = uuid.uuid4().hex[:8]
    username = f'rm_{unique}'
    email = f'rm_{unique}@example.com'
    cursor = db.execute(
        'INSERT INTO users (username, email, hash, role, phone, phone_format_valid) '
        'VALUES (?, ?, ?, ?, ?, 1)',
        (username, email, generate_password_hash(password), 'client', '+5491112345678')
    )
    user_id = cursor.lastrowid
    db.commit()
    return user_id, username, password


def _login(client, username, password, remember=False):
    data = {'username': username, 'password': password}
    if remember:
        data['remember'] = 'on'
    return client.post('/login', data=data, follow_redirects=False)


class TestRememberMeCookie:
    def test_login_creates_remember_token(self, client, db):
        user_id, username, password = _make_user(client, db)
        resp = _login(client, username, password, remember=True)
        assert resp.status_code in (302, 301)
        cookie = next((v for k, v in resp.headers.items() if k.lower() == 'set-cookie' and 'remember_token' in v), None)
        assert cookie is not None
        assert 'HttpOnly' in cookie
        assert 'SameSite=Lax' in cookie
        assert ':' in cookie.split('=', 1)[1].split(';')[0]
        row = db.execute('SELECT user_id, selector, validator_hash, expires_at FROM remember_tokens WHERE user_id = ?', (user_id,)).fetchone()
        assert row is not None
        assert row['user_id'] == user_id
        assert len(row['selector']) >= 16
        assert len(row['validator_hash']) == 64
        expires = datetime.fromisoformat(row['expires_at'])
        delta = expires - datetime.now()
        assert 25 <= delta.days <= 31

    def test_login_without_remember_no_cookie(self, client, db):
        # Limpiar tokens existentes por si tests previos los dejaron
        db.execute('DELETE FROM remember_tokens')
        db.commit()
        _, username, password = _make_user(client, db)
        resp = _login(client, username, password, remember=False)
        assert resp.status_code in (302, 301)
        cookie = next((v for k, v in resp.headers.items() if k.lower() == 'set-cookie' and 'remember_token' in v), None)
        assert cookie is None
        n = db.execute('SELECT COUNT(*) FROM remember_tokens').fetchone()[0]
        assert n == 0

    def test_remember_token_restores_session(self, client, db):
        db.execute('DELETE FROM remember_tokens')
        db.commit()
        user_id, username, password = _make_user(client, db)
        resp = _login(client, username, password, remember=True)
        raw = next((v for k, v in resp.headers.items() if k.lower() == 'set-cookie' and 'remember_token' in v), None)
        assert raw is not None
        with client.session_transaction() as sess:
            sess.clear()
        # La cookie remember_token persiste en el cookiejar del test_client
        protected = client.get('/usuario', follow_redirects=False)
        assert protected.status_code == 200, protected.status_code
        with client.session_transaction() as sess:
            assert sess.get('user_id') == user_id

    def test_remember_token_invalid_selector_ignored(self, client, db):
        db.execute('DELETE FROM remember_tokens')
        db.commit()
        bad_cookie = 'aW52YWxpZF9zZWxlY3Rvcg:aW52YWxpZF92YWxpZGF0b3I'
        client.set_cookie('remember_token', bad_cookie)
        protected = client.get('/usuario', follow_redirects=False)
        loc = protected.headers.get('Location', '')
        assert '/login' in loc

    def test_remember_token_invalid_validator_revoked(self, client, db):
        db.execute('DELETE FROM remember_tokens')
        db.commit()
        user_id, username, password = _make_user(client, db)
        _login(client, username, password, remember=True)
        row = db.execute('SELECT selector FROM remember_tokens WHERE user_id = ?', (user_id,)).fetchone()
        assert row is not None
        bad_cookie = f"{row['selector']}:wrongvalidator123"
        with client.session_transaction() as sess:
            sess.clear()
        client.set_cookie('remember_token', bad_cookie)
        protected = client.get('/usuario', follow_redirects=False)
        loc = protected.headers.get('Location', '')
        assert '/login' in loc
        remaining = db.execute('SELECT COUNT(*) FROM remember_tokens WHERE selector = ?', (row['selector'],)).fetchone()[0]
        assert remaining == 0

    def test_remember_token_expired_revoked(self, client, db):
        db.execute('DELETE FROM remember_tokens')
        db.commit()
        user_id, username, password = _make_user(client, db)
        _login(client, username, password, remember=True)
        row = db.execute('SELECT selector, validator_hash FROM remember_tokens WHERE user_id = ?', (user_id,)).fetchone()
        assert row is not None
        db.execute(
            'UPDATE remember_tokens SET expires_at = ? WHERE selector = ?',
            ((datetime.now() - timedelta(days=1)).isoformat(), row['selector'])
        )
        db.commit()
        cookie = f"{row['selector']}:cualquiercosa"
        with client.session_transaction() as sess:
            sess.clear()
        client.set_cookie('remember_token', cookie)
        client.get('/usuario', follow_redirects=False)
        remaining = db.execute('SELECT COUNT(*) FROM remember_tokens WHERE selector = ?', (row['selector'],)).fetchone()[0]
        assert remaining == 0

    def test_logout_revokes_only_current_token(self, client, db):
        user_id, username, password = _make_user(client, db)
        # Crear dos tokens para el mismo user
        from utils import generate_remember_token, remember_expires_at
        s1, v1, h1 = generate_remember_token()
        s2, v2, h2 = generate_remember_token()
        for sel, valh in [(s1, h1), (s2, h2)]:
            db.execute(
                'INSERT INTO remember_tokens (user_id, selector, validator_hash, expires_at) VALUES (?, ?, ?, ?)',
                (user_id, sel, valh, remember_expires_at().isoformat())
            )
        db.commit()
        # Login para setear la sesión y la cookie s1
        resp = _login(client, username, password, remember=True)
        # En este punto, s1 (generado en login) es el de la cookie, los previos s1_local y s2_local son "otros dispositivos"
        # Logout con la cookie actual
        client.get('/logout', follow_redirects=False)
        # Contar: el de la cookie del login debe haberse eliminado, los 2 locales deben seguir
        remaining = db.execute('SELECT COUNT(*) FROM remember_tokens WHERE user_id = ?', (user_id,)).fetchone()[0]
        assert remaining == 2  # los 2 locales


class TestCheckUsername:
    def test_check_username_available(self, client, db):
        unique = uuid.uuid4().hex[:8]
        r = client.get(f'/api/auth/check-username?q={unique}')
        assert r.status_code == 200
        body = r.get_json()
        assert body == {'available': True, 'reason': 'ok'}

    def test_check_username_taken(self, client, db):
        user_id, username, _ = _make_user(client, db)
        r = client.get(f'/api/auth/check-username?q={username}')
        assert r.status_code == 200
        body = r.get_json()
        assert body == {'available': False, 'reason': 'taken'}

    @pytest.mark.parametrize('q,expected_reason', [
        ('ab', 'invalid'),                       # muy corto
        ('a' * 31, 'invalid'),                   # muy largo
        ('has space', 'invalid'),                # caracter inválido
        ('dash-x', 'invalid'),                   # guión no permitido
        ('café', 'invalid'),                     # caracter no-ascii
        ('', 'invalid'),                         # vacío
    ])
    def test_check_username_invalid_format(self, client, q, expected_reason):
        from urllib.parse import quote
        r = client.get(f'/api/auth/check-username?q={quote(q)}')
        assert r.status_code == 200
        body = r.get_json()
        assert body['available'] is False
        assert body['reason'] == expected_reason

    def test_check_username_rate_limited(self, client):
        # 10/min. La 11ª debe recibir 429.
        unique = uuid.uuid4().hex[:8]
        for i in range(10):
            r = client.get(f'/api/auth/check-username?q={unique}{i}')
            assert r.status_code == 200
        r11 = client.get(f'/api/auth/check-username?q={unique}x')
        assert r11.status_code == 429


class TestPurgeRememberTokens:
    def test_purge_removes_only_expired(self, app, db):
        from utils import (
            generate_remember_token, remember_expires_at, purge_expired_remember_tokens
        )
        # Un usuario y 2 tokens: uno vigente, uno expirado
        unique = uuid.uuid4().hex[:8]
        cur = db.execute(
            'INSERT INTO users (username, email, hash, role) VALUES (?, ?, ?, ?)',
            (f'purge_{unique}', f'p_{unique}@x.com', 'x', 'client')
        )
        uid = cur.lastrowid
        s_ok, _, h_ok = generate_remember_token()
        s_exp, _, h_exp = generate_remember_token()
        db.execute(
            'INSERT INTO remember_tokens (user_id, selector, validator_hash, expires_at) VALUES (?, ?, ?, ?)',
            (uid, s_ok, h_ok, remember_expires_at().isoformat())
        )
        db.execute(
            'INSERT INTO remember_tokens (user_id, selector, validator_hash, expires_at) VALUES (?, ?, ?, ?)',
            (uid, s_exp, h_exp, (datetime.now() - timedelta(days=1)).isoformat())
        )
        db.commit()

        n_deleted = purge_expired_remember_tokens()
        assert n_deleted == 1
        remaining = db.execute('SELECT COUNT(*) FROM remember_tokens WHERE user_id = ?', (uid,)).fetchone()[0]
        assert remaining == 1
