import pytest
import json
from unittest.mock import patch
from datetime import datetime, timedelta


def _user_id(auth_client, db):
    with auth_client.session_transaction() as sess:
        username = sess.get('username')
    user = db.execute('SELECT id FROM users WHERE username = ?', (username,)).fetchone()
    return user['id'] if user else None


class TestSendCode:
    def test_requires_authentication(self, client):
        resp = client.post('/api/phone/send-code', content_type='application/json')
        assert resp.status_code == 401
        data = resp.get_json()
        assert data['error'] == 'No autorizado'

    def test_returns_success_for_authenticated_user(self, auth_client):
        resp = auth_client.post('/api/phone/send-code', content_type='application/json')
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['status'] == 'success'

    def test_stores_code_in_database(self, auth_client, db):
        uid = _user_id(auth_client, db)
        resp = auth_client.post('/api/phone/send-code', content_type='application/json')
        assert resp.status_code == 200

        user = db.execute('SELECT verification_code, verification_expires FROM users WHERE id = ?', (uid,)).fetchone()
        assert user is not None
        assert len(user['verification_code']) == 6
        assert user['verification_code'].isdigit()
        assert user['verification_expires'] is not None

    def test_code_is_6_digits(self, auth_client, db):
        uid = _user_id(auth_client, db)
        resp = auth_client.post('/api/phone/send-code', content_type='application/json')
        assert resp.status_code == 200

        user = db.execute('SELECT verification_code FROM users WHERE id = ?', (uid,)).fetchone()
        code = user['verification_code']
        assert len(code) == 6
        assert code.isdigit()

    def test_rejects_when_already_verified(self, auth_client, db):
        uid = _user_id(auth_client, db)
        db.execute('UPDATE users SET phone_verified = 1 WHERE id = ?', (uid,))
        db.commit()

        resp = auth_client.post('/api/phone/send-code', content_type='application/json')
        assert resp.status_code == 400
        data = resp.get_json()
        assert 'ya está verificado' in data['error']

    def test_rejects_missing_phone(self, auth_client, db):
        uid = _user_id(auth_client, db)
        db.execute('UPDATE users SET phone = ? WHERE id = ?', ('', uid))
        db.commit()

        resp = auth_client.post('/api/phone/send-code', content_type='application/json')
        assert resp.status_code == 400
        data = resp.get_json()
        assert 'teléfono registrado' in data['error']

    def test_generates_new_code_each_time(self, auth_client, db):
        uid = _user_id(auth_client, db)
        resp1 = auth_client.post('/api/phone/send-code', content_type='application/json')
        assert resp1.status_code == 200

        user1 = db.execute('SELECT verification_code FROM users WHERE id = ?', (uid,)).fetchone()
        code1 = user1['verification_code']

        resp2 = auth_client.post('/api/phone/send-code', content_type='application/json')
        assert resp2.status_code == 200

        user2 = db.execute('SELECT verification_code FROM users WHERE id = ?', (uid,)).fetchone()
        code2 = user2['verification_code']

        assert code1 != code2


class TestVerifyCode:
    def test_requires_authentication(self, client):
        resp = client.post('/api/phone/verify',
                           data=json.dumps({'code': '123456'}),
                           content_type='application/json')
        assert resp.status_code == 401

    def test_rejects_invalid_format(self, auth_client):
        resp = auth_client.post('/api/phone/verify',
                                data=json.dumps({'code': 'abc'}),
                                content_type='application/json')
        assert resp.status_code == 400

    def test_rejects_empty_code(self, auth_client):
        resp = auth_client.post('/api/phone/verify',
                                data=json.dumps({'code': ''}),
                                content_type='application/json')
        assert resp.status_code == 400

    def test_rejects_short_code(self, auth_client):
        resp = auth_client.post('/api/phone/verify',
                                data=json.dumps({'code': '12345'}),
                                content_type='application/json')
        assert resp.status_code == 400

    def test_rejects_no_pending_code(self, auth_client):
        resp = auth_client.post('/api/phone/verify',
                                data=json.dumps({'code': '123456'}),
                                content_type='application/json')
        assert resp.status_code == 400
        data = resp.get_json()
        assert 'No hay código pendiente' in data['error']

    def test_successful_verification(self, auth_client, db):
        uid = _user_id(auth_client, db)
        auth_client.post('/api/phone/send-code', content_type='application/json')
        user = db.execute('SELECT verification_code FROM users WHERE id = ?', (uid,)).fetchone()
        code = user['verification_code']

        resp = auth_client.post('/api/phone/verify',
                                data=json.dumps({'code': code}),
                                content_type='application/json')
        assert resp.status_code == 200

        verified = db.execute('SELECT phone_verified FROM users WHERE id = ?', (uid,)).fetchone()
        assert verified['phone_verified'] == 1

    def test_rejects_wrong_code(self, auth_client, db):
        uid = _user_id(auth_client, db)
        auth_client.post('/api/phone/send-code', content_type='application/json')

        resp = auth_client.post('/api/phone/verify',
                                data=json.dumps({'code': '000000'}),
                                content_type='application/json')
        assert resp.status_code == 400
        data = resp.get_json()
        assert 'incorrecto' in data['error']

    def test_rejects_expired_code(self, auth_client, db):
        uid = _user_id(auth_client, db)
        auth_client.post('/api/phone/send-code', content_type='application/json')
        user = db.execute('SELECT verification_code FROM users WHERE id = ?', (uid,)).fetchone()
        code = user['verification_code']

        expired_time = (datetime.now() - timedelta(minutes=15)).isoformat()
        db.execute('UPDATE users SET verification_expires = ? WHERE id = ?', (expired_time, uid))
        db.commit()

        resp = auth_client.post('/api/phone/verify',
                                data=json.dumps({'code': code}),
                                content_type='application/json')
        assert resp.status_code == 410
        data = resp.get_json()
        assert 'expirado' in data['error']

    def test_rejects_after_already_verified(self, auth_client, db):
        uid = _user_id(auth_client, db)
        auth_client.post('/api/phone/send-code', content_type='application/json')
        user = db.execute('SELECT verification_code FROM users WHERE id = ?', (uid,)).fetchone()
        code = user['verification_code']

        auth_client.post('/api/phone/verify',
                         data=json.dumps({'code': code}),
                         content_type='application/json')

        resp = auth_client.post('/api/phone/verify',
                                data=json.dumps({'code': code}),
                                content_type='application/json')
        assert resp.status_code == 400
        data = resp.get_json()
        assert 'ya está verificado' in data['error']

    def test_clears_code_after_verification(self, auth_client, db):
        uid = _user_id(auth_client, db)
        auth_client.post('/api/phone/send-code', content_type='application/json')
        user = db.execute('SELECT verification_code FROM users WHERE id = ?', (uid,)).fetchone()
        code = user['verification_code']

        auth_client.post('/api/phone/verify',
                         data=json.dumps({'code': code}),
                         content_type='application/json')

        user = db.execute('SELECT verification_code, verification_expires FROM users WHERE id = ?', (uid,)).fetchone()
        assert user['verification_code'] == ''
        assert user['verification_expires'] is None
