import pytest


@pytest.fixture
def admin_client(client):
    from models import get_db_connection
    conn = get_db_connection()
    conn.execute("UPDATE users SET role = 'admin', is_active = 1 WHERE username = 'admin'")
    conn.commit()
    conn.close()
    with client.session_transaction() as sess:
        sess['user_id'] = 1
        sess['username'] = 'admin'
        sess['role'] = 'admin'
    return client


class TestAdminDashboard:
    def test_admin_dashboard_renders(self, admin_client):
        res = admin_client.get('/admin')
        assert res.status_code == 200
        html = res.data.decode()
        assert 'panel-form-options' in html
        assert 'Opciones' in html

    def test_admin_requires_login(self, client):
        res = client.get('/admin')
        assert res.status_code in [302, 401, 403]

    def test_admin_requires_admin_role(self, client):
        from models import get_db_connection
        from werkzeug.security import generate_password_hash
        import uuid
        unique = uuid.uuid4().hex[:8]
        conn = get_db_connection()
        cursor = conn.execute(
            'INSERT INTO users (username, email, hash, role, phone, phone_format_valid) VALUES (?, ?, ?, ?, ?, 1)',
            (f'client_{unique}', f'{unique}@test.com', generate_password_hash('x'), 'client', '+5491112345678')
        )
        uid = cursor.lastrowid
        conn.commit()
        conn.close()
        with client.session_transaction() as sess:
            sess['user_id'] = uid
            sess['username'] = f'client_{unique}'
            sess['role'] = 'client'
        res = client.get('/admin')
        assert res.status_code in [302, 401, 403]


class TestAdminFormOptionsIntegration:
    def test_list_all_returns_all_categories(self, admin_client):
        res = admin_client.get('/api/form-options/all')
        assert res.status_code == 200
        data = res.get_json()
        categories = set(o['category'] for o in data['options'])
        assert 'property_type' in categories
        assert 'currency' in categories
        assert 'amenities' in categories

    def test_create_list_update_delete_lifecycle(self, admin_client):
        res = admin_client.post('/api/form-options', json={
            'category': 'amenities', 'value': 'lifecycle_test', 'label': 'Lifecycle', 'icon': 'star'
        })
        assert res.status_code == 200
        opt_id = res.get_json()['id']

        res = admin_client.get('/api/form-options/all')
        found = [o for o in res.get_json()['options'] if o['id'] == opt_id]
        assert len(found) == 1
        assert found[0]['label'] == 'Lifecycle'

        res = admin_client.put(f'/api/form-options/{opt_id}', json={
            'label': 'Updated Lifecycle', 'icon': 'heart'
        })
        assert res.status_code == 200

        res = admin_client.get('/api/form-options/all')
        updated = [o for o in res.get_json()['options'] if o['id'] == opt_id][0]
        assert updated['label'] == 'Updated Lifecycle'
        assert updated['icon'] == 'heart'

        res = admin_client.delete(f'/api/form-options/{opt_id}')
        assert res.status_code == 200

        res = admin_client.get('/api/form-options/all')
        remaining = [o for o in res.get_json()['options'] if o['id'] == opt_id]
        assert len(remaining) == 0

    def test_create_and_toggle_active(self, admin_client):
        res = admin_client.post('/api/form-options', json={
            'category': 'amenities', 'value': 'toggle_test', 'label': 'Toggle'
        })
        assert res.status_code == 200
        opt_id = res.get_json()['id']

        res = admin_client.put(f'/api/form-options/{opt_id}', json={'is_active': 0})
        assert res.status_code == 200

        res = admin_client.get('/api/form-options')
        all_public = [o for cat_opts in res.get_json()['options'].values() for o in cat_opts]
        assert opt_id not in [o['id'] for o in all_public]

        res = admin_client.get('/api/form-options/all')
        inactive = [o for o in res.get_json()['options'] if o['id'] == opt_id]
        assert len(inactive) == 1
        assert inactive[0]['is_active'] == 0

        admin_client.delete(f'/api/form-options/{opt_id}')

    def test_create_duplicate_returns_409(self, admin_client):
        res = admin_client.post('/api/form-options', json={
            'category': 'amenities', 'value': 'dup_test', 'label': 'Dup'
        })
        assert res.status_code == 200
        opt_id = res.get_json()['id']

        res = admin_client.post('/api/form-options', json={
            'category': 'amenities', 'value': 'dup_test', 'label': 'Dup2'
        })
        assert res.status_code == 409

        admin_client.delete(f'/api/form-options/{opt_id}')

    def test_cache_invalidation_on_create(self, admin_client):
        res = admin_client.post('/api/form-options', json={
            'category': 'amenities', 'value': 'cache_test', 'label': 'Cache', 'is_active': 0
        })
        assert res.status_code == 200
        opt_id = res.get_json()['id']

        res = admin_client.get('/api/form-options?category=amenities')
        data = res.get_json()
        values = [o['value'] for o in data['options'].get('amenities', [])]
        assert 'cache_test' not in values

        admin_client.delete(f'/api/form-options/{opt_id}')

    def test_update_nonexistent_option(self, admin_client):
        res = admin_client.put('/api/form-options/99999', json={'label': 'X'})
        assert res.status_code == 404

    def test_delete_nonexistent_option(self, admin_client):
        res = admin_client.delete('/api/form-options/99999')
        assert res.status_code == 404

    def test_create_missing_category(self, admin_client):
        res = admin_client.post('/api/form-options', json={
            'value': 'no_cat', 'label': 'No Cat'
        })
        assert res.status_code == 400

    def test_create_missing_value(self, admin_client):
        res = admin_client.post('/api/form-options', json={
            'category': 'amenities', 'label': 'No Value'
        })
        assert res.status_code == 400

    def test_create_missing_label(self, admin_client):
        res = admin_client.post('/api/form-options', json={
            'category': 'amenities', 'value': 'no_label'
        })
        assert res.status_code == 400
