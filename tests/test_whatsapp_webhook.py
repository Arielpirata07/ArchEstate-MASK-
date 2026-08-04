import uuid
from unittest.mock import patch

import pytest
from werkzeug.security import generate_password_hash


@pytest.fixture
def user_with_phone(db):
    unique = uuid.uuid4().hex[:8]
    phone = f'+54911{int(unique[:6], 16) % 1000000:06d}'
    cursor = db.execute(
        'INSERT INTO users (username, email, hash, role, phone, phone_e164, phone_verified, is_active) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
        (f'wa_{unique}', f'wa_{unique}@test.com', generate_password_hash('pass'), 'client', phone, phone, 0, 1)
    )
    db.commit()
    return cursor.lastrowid, phone


class TestWhatsAppWebhook:
    def _post(self, client, from_number, body='VERIFICAR'):
        return client.post(
            '/api/whatsapp/webhook',
            data={'From': f'whatsapp:{from_number}', 'Body': body},
            headers={'X-Twilio-Signature': 'sig'},
        )

    @patch('config.TWILIO_AUTH_TOKEN', 'test-token')
    @patch('twilio.request_validator.RequestValidator')
    def test_rejects_when_signature_invalid(self, MockValidator, client, user_with_phone):
        MockValidator.return_value.validate.return_value = False
        _, phone = user_with_phone
        resp = self._post(client, phone)
        assert resp.status_code == 403

    def test_rejects_when_token_missing(self, client, user_with_phone, monkeypatch):
        monkeypatch.setattr('config.TWILIO_AUTH_TOKEN', '')
        _, phone = user_with_phone
        resp = self._post(client, phone)
        assert resp.status_code == 403

    @patch('config.TWILIO_AUTH_TOKEN', 'test-token')
    @patch('twilio.request_validator.RequestValidator')
    def test_verifies_phone(self, MockValidator, client, db, user_with_phone):
        MockValidator.return_value.validate.return_value = True
        user_id, phone = user_with_phone
        resp = self._post(client, phone)
        assert resp.status_code == 200
        row = db.execute('SELECT phone_verified FROM users WHERE id = ?', (user_id,)).fetchone()
        assert row['phone_verified'] == 1

    @patch('config.TWILIO_AUTH_TOKEN', 'test-token')
    @patch('twilio.request_validator.RequestValidator')
    def test_ignores_non_verify_body(self, MockValidator, client, user_with_phone):
        MockValidator.return_value.validate.return_value = True
        _, phone = user_with_phone
        resp = self._post(client, phone, body='HOLA')
        assert resp.status_code == 200
        assert '<Response />' in resp.get_data(as_text=True)

    @patch('config.TWILIO_AUTH_TOKEN', 'test-token')
    @patch('twilio.request_validator.RequestValidator')
    def test_already_verified_replies_ack(self, MockValidator, client, db, user_with_phone):
        MockValidator.return_value.validate.return_value = True
        user_id, phone = user_with_phone
        db.execute('UPDATE users SET phone_verified = 1 WHERE id = ?', (user_id,))
        db.commit()
        resp = self._post(client, phone)
        assert resp.status_code == 200
        assert 'ya estaba verificado' in resp.get_data(as_text=True)

    @patch('config.TWILIO_AUTH_TOKEN', 'test-token')
    @patch('twilio.request_validator.RequestValidator')
    def test_unknown_number_replies_not_found(self, MockValidator, client):
        MockValidator.return_value.validate.return_value = True
        resp = self._post(client, '+5491000000000')
        assert resp.status_code == 200
        assert 'No se encontró' in resp.get_data(as_text=True)
