"""
Tests para los endpoints /api/phone/send-code y /api/phone/verify.
Refactorizado en Fase C para usar VerifierRouter. Se mantiene compatibilidad
con el contrato externo (status, error, formato de respuesta).
"""

import json
from datetime import datetime, timedelta

import pytest
from freezegun import freeze_time

from services.verifier import reset_default_router


def _user_id(auth_client, db):
    with auth_client.session_transaction() as sess:
        username = sess.get('username')
    user = db.execute('SELECT id FROM users WHERE username = ?', (username,)).fetchone()
    return user['id'] if user else None


@pytest.fixture(autouse=True)
def _reset_router_singleton():
    reset_default_router()
    yield
    reset_default_router()


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
        assert 'channel' in data

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

    def test_code_never_equals_zero_string(self, auth_client, db):
        """Fase 3.1: el código OTP nunca debe ser '000000' (colisión con 'no hay código')."""
        uid = _user_id(auth_client, db)
        for _ in range(20):
            auth_client.post('/api/phone/send-code', content_type='application/json')
            user = db.execute('SELECT verification_code FROM users WHERE id = ?', (uid,)).fetchone()
            assert user['verification_code'] != '000000'

    def test_code_is_in_range_1_to_999999(self, auth_client, db):
        """Fase 3.1: el código debe estar en el rango 1..999999."""
        uid = _user_id(auth_client, db)
        for _ in range(20):
            auth_client.post('/api/phone/send-code', content_type='application/json')
            user = db.execute('SELECT verification_code FROM users WHERE id = ?', (uid,)).fetchone()
            value = int(user['verification_code'])
            assert 1 <= value <= 999999

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

    def test_logs_consent(self, auth_client, db):
        resp = auth_client.post('/api/phone/send-code', content_type='application/json')
        assert resp.status_code == 200
        row = db.execute('SELECT * FROM consent_log ORDER BY id DESC LIMIT 1').fetchone()
        assert row is not None
        assert row['channel'] in ('sms', 'whatsapp')
        assert row['user_id'] is not None

    def test_logs_event(self, auth_client, db):
        resp = auth_client.post('/api/phone/send-code', content_type='application/json')
        assert resp.status_code == 200
        row = db.execute("SELECT * FROM events WHERE event = 'otp_sent' ORDER BY id DESC LIMIT 1").fetchone()
        assert row is not None

    def test_graceful_degradation_when_prefs_fail(self, auth_client, db, monkeypatch):
        """Fase 3.2: si get_user_preferences falla, el endpoint debe
        degradar a 'auto' en vez de 500."""
        import models

        def boom(_uid):
            raise RuntimeError("DB corrupted")

        monkeypatch.setattr(models, 'get_user_preferences', boom)
        resp = auth_client.post('/api/phone/send-code', content_type='application/json')
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['status'] == 'success'
        # No debe haber crasheado; el canal debe caer al default (sms o whatsapp)
        assert data['channel'] in ('sms', 'whatsapp')


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


class TestUpdatePhone:
    def test_requires_authentication(self, client):
        resp = client.post('/api/user/update-phone',
                           data=json.dumps({'phone': '+5491144445555'}),
                           content_type='application/json')
        assert resp.status_code == 401

    def test_updates_phone_with_e164(self, auth_client, db):
        uid = _user_id(auth_client, db)
        resp = auth_client.post('/api/user/update-phone',
                                data=json.dumps({'phone': '+5491144449999'}),
                                content_type='application/json')
        assert resp.status_code == 200
        user = db.execute('SELECT phone, phone_e164, phone_number_type FROM users WHERE id = ?', (uid,)).fetchone()
        assert user['phone'] == '+5491144449999'
        assert user['phone_e164'] == '+5491144449999'
        assert user['phone_number_type'] in ('mobile', 'fixed_or_mobile')

    def test_invalidates_otp_when_phone_changes(self, auth_client, db):
        uid = _user_id(auth_client, db)
        auth_client.post('/api/phone/send-code', content_type='application/json')

        resp = auth_client.post('/api/user/update-phone',
                                data=json.dumps({'phone': '+5491144440000'}),
                                content_type='application/json')
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['phone_verified'] == 0
        user = db.execute('SELECT verification_code, phone_verified FROM users WHERE id = ?', (uid,)).fetchone()
        assert user['verification_code'] == ''
        assert user['phone_verified'] == 0

    def test_keeps_verification_when_phone_unchanged(self, auth_client, db):
        uid = _user_id(auth_client, db)
        db.execute('UPDATE users SET phone_verified = 1, phone = ? WHERE id = ?',
                   ('+5491144445555', uid))
        db.commit()

        resp = auth_client.post('/api/user/update-phone',
                                data=json.dumps({'phone': '+5491144445555'}),
                                content_type='application/json')
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['phone_verified'] == 1

    def test_rejects_empty(self, auth_client):
        resp = auth_client.post('/api/user/update-phone',
                                data=json.dumps({'phone': ''}),
                                content_type='application/json')
        assert resp.status_code == 400

    def test_rejects_invalid_format(self, auth_client):
        resp = auth_client.post('/api/user/update-phone',
                                data=json.dumps({'phone': 'abc'}),
                                content_type='application/json')
        assert resp.status_code == 400

    def test_does_not_invalidate_otp_for_format_only_change(self, auth_client, db):
        """Fase 2.3: si el E.164 no cambia (cambia solo formato/whitespace), no invalidar OTP."""
        uid = _user_id(auth_client, db)
        # Estado inicial: phone = +5491144445555, verified = 1
        db.execute('UPDATE users SET phone = ?, phone_e164 = ?, phone_verified = 1, '
                   'verification_code = ?, verification_expires = ? WHERE id = ?',
                   ('+5491144445555', '+5491144445555', '123456',
                    (datetime.now() + timedelta(minutes=10)).isoformat(), uid))
        db.commit()

        # Mismo número, distinto formato (con espacios)
        resp = auth_client.post('/api/user/update-phone',
                                data=json.dumps({'phone': '+54 9 11 4444 5555'}),
                                content_type='application/json')
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['phone_verified'] == 1, "OTP no debe invalidarse si E.164 no cambia"


class TestVerifyRejectsInvalidFormat:
    """Fase 2.5: verify_phone_code debe exigir phone_format_valid=1."""

    def test_rejects_when_phone_format_invalid(self, auth_client, db):
        uid = _user_id(auth_client, db)
        # Forzar formato inválido y código pendiente
        db.execute('UPDATE users SET phone_format_valid = 0, phone_e164 = \'\', '
                   'verification_code = ?, verification_expires = ? WHERE id = ?',
                   ('123456', (datetime.now() + timedelta(minutes=10)).isoformat(), uid))
        db.commit()

        resp = auth_client.post('/api/phone/verify',
                                data=json.dumps({'code': '123456'}),
                                content_type='application/json')
        assert resp.status_code == 400
        assert 'formato' in resp.get_json()['error'].lower()

    def test_sets_phone_format_valid_on_success(self, auth_client, db):
        uid = _user_id(auth_client, db)
        # Pre-condición: el usuario tiene un código válido y formato válido
        resp = auth_client.post('/api/phone/send-code', content_type='application/json')
        assert resp.status_code == 200
        # Forzar formato inválido después de generar el código (simula estado inconsistente)
        db.execute('UPDATE users SET phone_format_valid = 0 WHERE id = ?', (uid,))
        db.commit()

        # El verify debe rechazar antes de comparar el código
        resp = auth_client.post('/api/phone/verify',
                                data=json.dumps({'code': '000000'}),
                                content_type='application/json')
        assert resp.status_code == 400
        # No debe haber marcado phone_verified
        user = db.execute('SELECT phone_verified, phone_format_valid FROM users WHERE id = ?', (uid,)).fetchone()
        assert user['phone_verified'] == 0


class TestVerifyKeepsFormatValid:
    """Fase 2.5: la verificación exitosa debe preservar phone_format_valid=1."""

    def test_format_valid_remains_one_after_success(self, auth_client, db):
        uid = _user_id(auth_client, db)
        auth_client.post('/api/phone/send-code', content_type='application/json')
        user = db.execute('SELECT verification_code FROM users WHERE id = ?', (uid,)).fetchone()
        code = user['verification_code']

        resp = auth_client.post('/api/phone/verify',
                                data=json.dumps({'code': code}),
                                content_type='application/json')
        assert resp.status_code == 200
        user = db.execute('SELECT phone_format_valid FROM users WHERE id = ?', (uid,)).fetchone()
        assert user['phone_format_valid'] == 1


class TestBruteForceProtection:
    """Tests para la protección contra fuerza bruta en verificación OTP."""

    def test_increments_failed_attempts_on_wrong_code(self, auth_client, db):
        uid = _user_id(auth_client, db)
        auth_client.post('/api/phone/send-code', content_type='application/json')

        auth_client.post('/api/phone/verify',
                         data=json.dumps({'code': '000001'}),
                         content_type='application/json')
        user = db.execute('SELECT failed_attempts FROM users WHERE id = ?', (uid,)).fetchone()
        assert user['failed_attempts'] == 1

    def test_increments_on_each_wrong_attempt(self, auth_client, db):
        uid = _user_id(auth_client, db)
        auth_client.post('/api/phone/send-code', content_type='application/json')

        for i in range(1, 4):
            auth_client.post('/api/phone/verify',
                             data=json.dumps({'code': f'{i:06d}'}),
                             content_type='application/json')
        user = db.execute('SELECT failed_attempts FROM users WHERE id = ?', (uid,)).fetchone()
        assert user['failed_attempts'] == 3

    def test_locks_out_after_max_attempts(self, auth_client, db):
        uid = _user_id(auth_client, db)
        auth_client.post('/api/phone/send-code', content_type='application/json')

        for i in range(1, 6):
            resp = auth_client.post('/api/phone/verify',
                                    data=json.dumps({'code': f'{i:06d}'}),
                                    content_type='application/json')
        assert resp.status_code == 429
        assert 'bloqueado' in resp.get_json()['error'].lower()

    def test_invalidates_otp_on_lockout(self, auth_client, db):
        uid = _user_id(auth_client, db)
        auth_client.post('/api/phone/send-code', content_type='application/json')

        for i in range(1, 6):
            auth_client.post('/api/phone/verify',
                             data=json.dumps({'code': f'{i:06d}'}),
                             content_type='application/json')

        user = db.execute(
            'SELECT verification_code, verification_expires, failed_attempts FROM users WHERE id = ?',
            (uid,)).fetchone()
        assert user['verification_code'] == ''
        assert user['verification_expires'] is None
        assert user['failed_attempts'] == 5

    def test_rejects_after_lockout_even_with_correct_code(self, auth_client, db):
        uid = _user_id(auth_client, db)
        auth_client.post('/api/phone/send-code', content_type='application/json')
        user = db.execute('SELECT verification_code FROM users WHERE id = ?', (uid,)).fetchone()
        real_code = user['verification_code']

        for i in range(1, 6):
            auth_client.post('/api/phone/verify',
                             data=json.dumps({'code': f'{i:06d}'}),
                             content_type='application/json')

        resp = auth_client.post('/api/phone/verify',
                                data=json.dumps({'code': real_code}),
                                content_type='application/json')
        assert resp.status_code == 429

    def test_resets_failed_attempts_on_new_code(self, auth_client, db):
        import rate_limit
        uid = _user_id(auth_client, db)
        auth_client.post('/api/phone/send-code', content_type='application/json')

        for i in range(1, 4):
            auth_client.post('/api/phone/verify',
                             data=json.dumps({'code': f'{i:06d}'}),
                             content_type='application/json')
        user = db.execute('SELECT failed_attempts FROM users WHERE id = ?', (uid,)).fetchone()
        assert user['failed_attempts'] == 3

        with rate_limit._rate_lock:
            rate_limit._save_store({})
        auth_client.post('/api/phone/send-code', content_type='application/json')
        user = db.execute('SELECT failed_attempts FROM users WHERE id = ?', (uid,)).fetchone()
        assert user['failed_attempts'] == 0

    def test_resets_failed_attempts_on_success(self, auth_client, db):
        uid = _user_id(auth_client, db)
        auth_client.post('/api/phone/send-code', content_type='application/json')

        auth_client.post('/api/phone/verify',
                         data=json.dumps({'code': '000001'}),
                         content_type='application/json')
        user = db.execute('SELECT failed_attempts FROM users WHERE id = ?', (uid,)).fetchone()
        assert user['failed_attempts'] == 1

        auth_client.post('/api/phone/send-code', content_type='application/json')
        user = db.execute('SELECT verification_code FROM users WHERE id = ?', (uid,)).fetchone()
        real_code = user['verification_code']

        resp = auth_client.post('/api/phone/verify',
                                data=json.dumps({'code': real_code}),
                                content_type='application/json')
        assert resp.status_code == 200
        user = db.execute('SELECT failed_attempts FROM users WHERE id = ?', (uid,)).fetchone()
        assert user['failed_attempts'] == 0

    def test_logs_lockout_event(self, auth_client, db):
        uid = _user_id(auth_client, db)
        auth_client.post('/api/phone/send-code', content_type='application/json')

        for i in range(1, 6):
            auth_client.post('/api/phone/verify',
                             data=json.dumps({'code': f'{i:06d}'}),
                             content_type='application/json')

        row = db.execute("SELECT * FROM events WHERE event = 'otp_locked_out' ORDER BY id DESC LIMIT 1").fetchone()
        assert row is not None


class TestSendCodeFormatValid:
    """Tests para la validación de phone_format_valid en send-code."""

    def test_rejects_when_phone_format_invalid(self, auth_client, db):
        uid = _user_id(auth_client, db)
        db.execute('UPDATE users SET phone_format_valid = 0, phone = ? WHERE id = ?', ('123', uid))
        db.commit()

        resp = auth_client.post('/api/phone/send-code', content_type='application/json')
        assert resp.status_code == 400

    def test_allows_send_when_format_valid(self, auth_client, db):
        uid = _user_id(auth_client, db)
        db.execute('UPDATE users SET phone_format_valid = 1 WHERE id = ?', (uid,))
        db.commit()

        resp = auth_client.post('/api/phone/send-code', content_type='application/json')
        assert resp.status_code == 200


class TestProfilePhoneUpdate:
    """Tests para el fix de doble ruta: update_user_credentials con cambio de teléfono."""

    def test_resets_verification_when_phone_changes_via_profile(self, auth_client, db):
        uid = _user_id(auth_client, db)
        db.execute(
            'UPDATE users SET phone = ?, phone_e164 = ?, phone_verified = 1, '
            'verification_code = ?, verification_expires = ? WHERE id = ?',
            ('+5491144445555', '+5491144445555', '123456',
             (datetime.now() + timedelta(minutes=10)).isoformat(), uid)
        )
        db.commit()

        resp = auth_client.put('/api/profile/user',
                               data=json.dumps({
                                   'email': 'test@example.com',
                                   'phone': '+5491144440000',
                                   'first_name': '', 'last_name': '', 'bio': '',
                               }),
                               content_type='application/json')
        assert resp.status_code == 200

        user = db.execute(
            'SELECT phone, phone_e164, phone_verified, verification_code, phone_number_type '
            'FROM users WHERE id = ?', (uid,)).fetchone()
        assert user['phone'] == '+5491144440000'
        assert user['phone_e164'] == '+5491144440000'
        assert user['phone_verified'] == 0
        assert user['verification_code'] == ''
        assert user['phone_number_type'] in ('mobile', 'fixed_or_mobile')

    def test_preserves_verification_when_phone_unchanged_via_profile(self, auth_client, db):
        uid = _user_id(auth_client, db)
        db.execute(
            'UPDATE users SET phone = ?, phone_e164 = ?, phone_verified = 1 WHERE id = ?',
            ('+5491144445555', '+5491144445555', uid)
        )
        db.commit()

        resp = auth_client.put('/api/profile/user',
                               data=json.dumps({
                                   'email': 'test@example.com',
                                   'phone': '+5491144445555',
                                   'first_name': '', 'last_name': '', 'bio': '',
                               }),
                               content_type='application/json')
        assert resp.status_code == 200

        user = db.execute('SELECT phone_verified FROM users WHERE id = ?', (uid,)).fetchone()
        assert user['phone_verified'] == 1

    def test_updates_phone_e164_even_when_unchanged(self, auth_client, db):
        uid = _user_id(auth_client, db)
        db.execute("UPDATE users SET phone_e164 = '' WHERE id = ?", (uid,))
        db.commit()

        resp = auth_client.put('/api/profile/user',
                               data=json.dumps({
                                   'email': 'test@example.com',
                                   'phone': '+5491144445555',
                                   'first_name': '', 'last_name': '', 'bio': '',
                               }),
                               content_type='application/json')
        assert resp.status_code == 200

        user = db.execute('SELECT phone_e164, phone_number_type FROM users WHERE id = ?', (uid,)).fetchone()
        assert user['phone_e164'] == '+5491144445555'
        assert user['phone_number_type'] in ('mobile', 'fixed_or_mobile')
