import uuid

from datetime import datetime, timedelta, timezone

import pytest

import models


class RecordingSender:
    def __init__(self):
        self.sent = []

    def send(self, to, subject, html_body, text_body=None):
        self.sent.append({'to': to, 'subject': subject, 'html_body': html_body})
        return True


@pytest.fixture
def sender(monkeypatch):
    import services.email

    recorder = RecordingSender()
    monkeypatch.setattr(services.email, 'get_email_sender', lambda: recorder)
    return recorder


def _make_user(db, email_verified=0):
    unique = uuid.uuid4().hex[:8]
    cursor = db.execute(
        'INSERT INTO users (username, email, hash, role, phone, phone_format_valid, email_verified) '
        "VALUES (?, ?, 'x', 'client', '+5491112345678', 1, ?)",
        (f'emv_{unique}', f'emv_{unique}@test.com', email_verified)
    )
    db.commit()
    return cursor.lastrowid, f'emv_{unique}@test.com'


def _future(hours=24):
    return (datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(hours=hours)).isoformat()


class TestEmailVerificationLink:
    def test_valid_token_verifies_user(self, client, db):
        user_id, email = _make_user(db)
        token = 'tok-' + uuid.uuid4().hex
        assert models.create_email_verification_token(user_id, token, email, _future())

        resp = client.get(f'/verify-email/{token}')
        assert resp.status_code == 302

        row = db.execute('SELECT email_verified FROM users WHERE id = ?', (user_id,)).fetchone()
        assert row['email_verified'] == 1
        tok = db.execute('SELECT used FROM email_verification_tokens WHERE token = ?', (token,)).fetchone()
        assert tok['used'] == 1

    def test_token_single_use(self, client, db):
        user_id, email = _make_user(db)
        token = 'tok-' + uuid.uuid4().hex
        models.create_email_verification_token(user_id, token, email, _future())

        assert client.get(f'/verify-email/{token}').status_code == 302
        assert models.validate_email_verification_token(token) is None

    def test_expired_token_rejected(self, client, db):
        user_id, email = _make_user(db)
        token = 'tok-' + uuid.uuid4().hex
        models.create_email_verification_token(user_id, token, email, _future(-1))

        assert models.validate_email_verification_token(token) is None
        resp = client.get(f'/verify-email/{token}')
        assert resp.status_code == 302
        row = db.execute('SELECT email_verified FROM users WHERE id = ?', (user_id,)).fetchone()
        assert row['email_verified'] == 0

    def test_unknown_token_rejected(self, client):
        resp = client.get('/verify-email/does-not-exist')
        assert resp.status_code == 302

    def test_new_token_invalidates_previous(self, db):
        user_id, email = _make_user(db)
        first = 'tok-' + uuid.uuid4().hex
        second = 'tok-' + uuid.uuid4().hex
        models.create_email_verification_token(user_id, first, email, _future())
        models.create_email_verification_token(user_id, second, email, _future())

        assert models.validate_email_verification_token(first) is None
        assert models.validate_email_verification_token(second) == user_id


class TestSendEmailVerification:
    def test_requires_login(self, client):
        resp = client.post('/api/email/send-verification')
        assert resp.status_code in (302, 401, 403)

    def test_sends_email_and_creates_token(self, auth_client, db, sender):
        resp = auth_client.post('/api/email/send-verification')
        data = resp.get_json()
        assert resp.status_code == 200
        assert data['success'] is True
        assert len(sender.sent) == 1

        with auth_client.session_transaction() as sess:
            user_id = sess['user_id']
        count = db.execute(
            'SELECT COUNT(*) AS c FROM email_verification_tokens WHERE user_id = ? AND used = 0',
            (user_id,)
        ).fetchone()['c']
        assert count == 1

    def test_already_verified_is_noop(self, client, db, sender):
        user_id, email = _make_user(db, email_verified=1)
        db.execute('UPDATE users SET email = ? WHERE id = ?', (email, user_id))
        db.commit()

        with client.session_transaction() as sess:
            sess['user_id'] = user_id
            sess['username'] = f'emv_{user_id}'
            sess['role'] = 'client'

        resp = client.post('/api/email/send-verification')
        data = resp.get_json()
        assert resp.status_code == 200
        assert data['already_verified'] is True
        assert sender.sent == []


class TestRegistrationEmailVerification:
    def test_register_sends_verification_email(self, client, db, sender):
        unique = uuid.uuid4().hex[:8]
        username = f'newreg_{unique}'
        resp = client.post('/register', data={
            'username': username,
            'email': f'{unique}@example.com',
            'phone': '+5491112345678',
            'password': 'abc123',
            'role': 'client',
        })
        assert resp.status_code == 302
        assert len(sender.sent) == 1
        assert sender.sent[0]['to'] == f'{unique}@example.com'

        row = db.execute('SELECT id, email_verified FROM users WHERE username = ?', (username,)).fetchone()
        assert row is not None
        assert row['email_verified'] == 0
        token_row = db.execute(
            'SELECT COUNT(*) AS c FROM email_verification_tokens WHERE user_id = ?',
            (row['id'],)
        ).fetchone()
        assert token_row['c'] == 1


class TestEmailChangeResetsVerification:
    def test_update_user_account_resets_when_email_changes(self, db):
        user_id, _ = _make_user(db, email_verified=1)
        assert models.update_user_account(user_id, 'changed@test.com', '', {})
        row = db.execute('SELECT email_verified FROM users WHERE id = ?', (user_id,)).fetchone()
        assert row['email_verified'] == 0

    def test_update_user_account_keeps_when_email_same(self, db):
        user_id, email = _make_user(db, email_verified=1)
        assert models.update_user_account(user_id, email, '', {})
        row = db.execute('SELECT email_verified FROM users WHERE id = ?', (user_id,)).fetchone()
        assert row['email_verified'] == 1


class TestEmailTokenBinding:
    def test_token_invalid_after_email_change(self, client, db):
        user_id, email = _make_user(db)
        token = 'tok-' + uuid.uuid4().hex
        models.create_email_verification_token(user_id, token, email, _future())

        new_email = f'reset_{uuid.uuid4().hex[:8]}@test.com'
        assert models.update_user_account(user_id, new_email, '', {}) is True
        assert models.validate_email_verification_token(token) is None

    def test_token_not_valid_for_different_email(self, db):
        user_id, _ = _make_user(db)
        token = 'tok-' + uuid.uuid4().hex
        models.create_email_verification_token(user_id, token, 'otra@test.com', _future())
        assert models.validate_email_verification_token(token) is None
