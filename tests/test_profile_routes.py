class TestProfileUpdate:
    def test_update_user_info(self, auth_client, db):
        resp = auth_client.put('/api/profile/user', json={
            'first_name': 'Ana',
            'last_name': 'García',
            'email': 'nuevo@test.com',
            'phone': '+5491123456789',
        })
        assert resp.status_code == 200
        assert resp.get_json()['success'] is True

        user_id = None
        with auth_client.session_transaction() as sess:
            user_id = sess['user_id']
        row = db.execute('SELECT email, phone FROM users WHERE id = ?', (user_id,)).fetchone()
        assert row['email'] == 'nuevo@test.com'
        assert row['phone'] == '+5491123456789'
        profile = db.execute('SELECT first_name, last_name FROM user_profiles WHERE user_id = ?', (user_id,)).fetchone()
        assert profile['first_name'] == 'Ana'
        assert profile['last_name'] == 'García'

    def test_update_user_rejects_invalid_email(self, auth_client):
        resp = auth_client.put('/api/profile/user', json={'email': 'not-an-email'})
        assert resp.status_code == 400

    def test_update_user_requires_login(self, client):
        resp = client.put('/api/profile/user', json={'first_name': 'X'})
        assert resp.status_code in (401, 301, 302)


class TestPasswordChange:
    def test_changes_password(self, auth_client, db):
        user_id = None
        with auth_client.session_transaction() as sess:
            user_id = sess['user_id']
        resp = auth_client.put('/api/profile/user/password', json={
            'current_password': 'abc123',
            'new_password': 'newpass123',
        })
        assert resp.status_code == 200
        assert resp.get_json()['success'] is True

        row = db.execute('SELECT hash FROM users WHERE id = ?', (user_id,)).fetchone()
        from werkzeug.security import check_password_hash
        assert check_password_hash(row['hash'], 'newpass123')

    def test_wrong_current_password(self, auth_client):
        resp = auth_client.put('/api/profile/user/password', json={
            'current_password': 'wrongpass',
            'new_password': 'newpass123',
        })
        assert resp.status_code == 400

    def test_weak_new_password_rejected(self, auth_client):
        resp = auth_client.put('/api/profile/user/password', json={
            'current_password': 'abc123',
            'new_password': 'short',
        })
        assert resp.status_code == 400

    def test_missing_fields_rejected(self, auth_client):
        resp = auth_client.put('/api/profile/user/password', json={})
        assert resp.status_code == 400


class TestSettings:
    def test_get_settings(self, auth_client):
        resp = auth_client.get('/api/profile/settings')
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['success'] is True
        assert isinstance(data['preferences'], dict)

    def test_update_settings(self, auth_client, db):
        user_id = None
        with auth_client.session_transaction() as sess:
            user_id = sess['user_id']
        resp = auth_client.put('/api/profile/settings', json={
            'theme': 'dark',
            'language': 'en',
            'lead_alerts': 1,
        })
        assert resp.status_code == 200

        prefs = db.execute('SELECT * FROM user_preferences WHERE user_id = ?', (user_id,)).fetchone()
        assert prefs is not None

    def test_update_settings_invalid_theme(self, auth_client):
        resp = auth_client.put('/api/profile/settings', json={'theme': 'neon'})
        assert resp.status_code == 400

    def test_update_settings_invalid_language(self, auth_client):
        resp = auth_client.put('/api/profile/settings', json={'language': 'fr'})
        assert resp.status_code == 400

    def test_update_settings_empty_rejected(self, auth_client):
        resp = auth_client.put('/api/profile/settings', json={})
        assert resp.status_code == 400


class TestSessions:
    def test_get_sessions(self, auth_client):
        resp = auth_client.get('/api/profile/sessions')
        assert resp.status_code == 200
        assert resp.get_json()['success'] is True

    def test_delete_own_session(self, auth_client, db):
        user_id = None
        with auth_client.session_transaction() as sess:
            user_id = sess['user_id']
        cursor = db.execute(
            'INSERT INTO user_login_history (user_id, ip_address, user_agent) VALUES (?, ?, ?)',
            (user_id, '127.0.0.1', 'test-agent')
        )
        db.commit()
        entry_id = cursor.lastrowid

        resp = auth_client.delete(f'/api/profile/sessions/{entry_id}')
        assert resp.status_code == 200

        row = db.execute('SELECT * FROM user_login_history WHERE id = ?', (entry_id,)).fetchone()
        assert row is None

    def test_delete_others_session_rejected(self, auth_client, db):
        import uuid
        from werkzeug.security import generate_password_hash
        unique = uuid.uuid4().hex[:8]
        cursor = db.execute(
            'INSERT INTO users (username, email, hash, role, phone, is_active) VALUES (?, ?, ?, ?, ?, ?)',
            (f'other_{unique}', f'other_{unique}@test.com', generate_password_hash('x'), 'client', '+5491999999999', 1)
        )
        db.commit()
        other_id = cursor.lastrowid
        cur = db.execute(
            'INSERT INTO user_login_history (user_id, ip_address, user_agent) VALUES (?, ?, ?)',
            (other_id, '127.0.0.1', 'other-agent')
        )
        db.commit()

        resp = auth_client.delete(f'/api/profile/sessions/{cur.lastrowid}')
        assert resp.status_code == 404
