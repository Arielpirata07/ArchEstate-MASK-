from unittest.mock import patch

import models


VALID_LEAD = {
    'type': 'Comprar Propiedad',
    'property_type': 'departamento',
    'zone': 'Palermo',
    'budget': '200000',
    'currency': 'USD',
    'phone': '+5491123456789',
    'email': 'client@test.com',
}


class TestUserView:
    def test_renders_for_client(self, auth_client):
        resp = auth_client.get('/usuario')
        assert resp.status_code == 200

    def test_redirects_professional(self, client, db):
        import uuid
        from werkzeug.security import generate_password_hash
        unique = uuid.uuid4().hex[:8]
        cursor = db.execute(
            'INSERT INTO users (username, email, hash, role, phone, is_active) VALUES (?, ?, ?, ?, ?, ?)',
            (f'pro_{unique}', f'pro_{unique}@test.com', generate_password_hash('x'), 'professional', '+5491111111111', 1)
        )
        db.commit()
        user_id = cursor.lastrowid
        db.execute(
            'INSERT INTO professionals (user_id, name, license, specialty, status) VALUES (?, ?, ?, ?, ?)',
            (user_id, 'Pro', 'LIC', 'departamento', 'approved')
        )
        db.commit()
        with client.session_transaction() as sess:
            sess['user_id'] = user_id
            sess['username'] = f'pro_{unique}'
            sess['role'] = 'professional'

        resp = client.get('/usuario', follow_redirects=False)
        assert resp.status_code == 302
        assert '/login' not in resp.headers.get('Location', '')

    def test_requires_login(self, client):
        resp = client.get('/usuario', follow_redirects=False)
        assert resp.status_code in (301, 302)


class TestSubmitLead:
    def test_requires_login(self, client):
        resp = client.post('/api/submit', json=VALID_LEAD)
        assert resp.status_code in (401, 301, 302)

    @patch('services.notifications.notify_lead_created')
    def test_submits_lead(self, mock_notify, auth_client, db):
        resp = auth_client.post('/api/submit', json=VALID_LEAD)
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['status'] == 'success'

        row = db.execute('SELECT * FROM leads ORDER BY id DESC LIMIT 1').fetchone()
        assert row['phone'] == '+5491123456789'
        assert row['zone'] == 'Palermo'
        assert row['phone_format_valid'] == 1

    @patch('services.notifications.notify_lead_created')
    def test_missing_phone_rejected(self, mock_notify, auth_client):
        payload = dict(VALID_LEAD)
        payload.pop('phone')
        resp = auth_client.post('/api/submit', json=payload)
        assert resp.status_code == 400
        assert resp.get_json()['status'] == 'error'

    @patch('services.notifications.notify_lead_created')
    def test_invalid_operation_type_rejected(self, mock_notify, auth_client):
        payload = dict(VALID_LEAD)
        payload['type'] = 'no_existe'
        resp = auth_client.post('/api/submit', json=payload)
        assert resp.status_code == 400
        assert resp.get_json()['status'] == 'error'

    @patch('services.notifications.notify_lead_created')
    def test_missing_email_rejected(self, mock_notify, auth_client):
        payload = dict(VALID_LEAD)
        payload.pop('email')
        resp = auth_client.post('/api/submit', json=payload)
        assert resp.status_code == 400

    @patch('services.notifications.notify_lead_created')
    def test_session_email_takes_precedence(self, mock_notify, auth_client, db):
        with auth_client.session_transaction() as sess:
            sess['email'] = 'session@test.com'

        payload = dict(VALID_LEAD)
        payload['email'] = 'data@test.com'
        resp = auth_client.post('/api/submit', json=payload)
        assert resp.status_code == 200

        row = db.execute('SELECT email FROM leads ORDER BY id DESC LIMIT 1').fetchone()
        assert row['email'] == 'session@test.com'
