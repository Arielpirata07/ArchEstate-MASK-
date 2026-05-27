import pytest


class TestRegister:
    def test_register_page_renders(self, client):
        resp = client.get('/register')
        assert resp.status_code == 200
        assert b'ArchEstate' in resp.data

    def test_successful_registration_with_phone(self, client, db):
        resp = client.post('/register', data={
            'username': 'newuser',
            'email': 'new@example.com',
            'phone': '+5491112345678',
            'password': 'Secure1',
            'role': 'client',
        }, follow_redirects=True)
        assert resp.status_code == 200
        assert b'Registro exitoso' in resp.data

        user = db.execute("SELECT username, phone, phone_format_valid, phone_verified FROM users WHERE username = 'newuser'").fetchone()
        assert user is not None
        assert user['phone'] == '+5491112345678'
        assert user['phone_format_valid'] == 1
        assert user['phone_verified'] == 0

    def test_registration_missing_phone(self, client):
        resp = client.post('/register', data={
            'username': 'nophone',
            'email': 'nophone@example.com',
            'phone': '',
            'password': 'Secure1',
            'role': 'client',
        }, follow_redirects=True)
        assert resp.status_code == 200
        content = resp.data.decode('utf-8')
        assert 'teléfono es requerido' in content.lower() or 'Teléfono' in content

    def test_registration_invalid_phone(self, client):
        resp = client.post('/register', data={
            'username': 'badphone',
            'email': 'badphone@example.com',
            'phone': '12',
            'password': 'Secure1',
            'role': 'client',
        }, follow_redirects=True)
        assert resp.status_code == 200
        content = resp.data.decode('utf-8')
        assert any(word in content.lower() for word in ['inválido', 'teléfono', 'número'])

    def test_registration_rejects_duplicate_username(self, client):
        resp = client.post('/register', data={
            'username': 'firstuser',
            'email': 'first@example.com',
            'phone': '+5491112345678',
            'password': 'Secure1',
            'role': 'client',
        }, follow_redirects=True)
        assert resp.status_code == 200

        resp = client.post('/register', data={
            'username': 'firstuser',
            'email': 'second@example.com',
            'phone': '+5491112345678',
            'password': 'Secure1',
            'role': 'client',
        }, follow_redirects=True)
        assert resp.status_code == 200
        content = resp.data.decode('utf-8', errors='replace')
        assert 'ya está en uso' in content or 'ya est' in content
