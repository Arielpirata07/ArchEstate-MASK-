import json

import pytest

from werkzeug.security import generate_password_hash


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


class TestFormOptionsPublic:
    def test_list_returns_grouped_options(self, client):
        res = client.get('/api/form-options')
        assert res.status_code == 200
        data = res.get_json()
        assert 'options' in data
        assert 'property_type' in data['options']
        assert 'currency' in data['options']

    def test_list_by_category(self, client):
        res = client.get('/api/form-options?category=currency')
        assert res.status_code == 200
        data = res.get_json()
        assert 'currency' in data['options']
        assert len(data['options']['currency']) >= 3

    def test_only_active_options_returned(self, client):
        res = client.get('/api/form-options')
        data = res.get_json()
        for cat, opts in data['options'].items():
            for opt in opts:
                assert opt['is_active'] == 1

    def test_seed_has_property_types(self, client):
        res = client.get('/api/form-options?category=property_type')
        data = res.get_json()
        values = [o['value'] for o in data['options']['property_type']]
        assert 'departamento' in values
        assert 'casa' in values
        assert 'duplex' in values
        assert 'penthouse' in values
        assert 'local_comercial' in values

    def test_seed_has_operation_types(self, client):
        res = client.get('/api/form-options?category=operation_type')
        data = res.get_json()
        values = [o['value'] for o in data['options']['operation_type']]
        assert 'Comprar Propiedad' in values
        assert 'Remodelacion Integral' in values
        assert 'Construir desde Cero' in values

    def test_seed_has_currencies(self, client):
        res = client.get('/api/form-options?category=currency')
        data = res.get_json()
        values = [o['value'] for o in data['options']['currency']]
        assert 'ARG' in values
        assert 'USD' in values
        assert 'EUR' in values


class TestFormOptionsAdmin:
    def test_list_all_requires_admin(self, client):
        res = client.get('/api/form-options/all')
        assert res.status_code in [302, 401, 403]

    def test_list_all_includes_inactive(self, admin_client):
        from models import get_db_connection
        conn = get_db_connection()
        conn.execute(
            "INSERT INTO form_options (category, value, label, icon, sort_order, is_active) VALUES (?, ?, ?, ?, ?, ?)",
            ('test_cat', 'test_val', 'Test', '', 1, 0)
        )
        conn.commit()
        conn.close()

        res = admin_client.get('/api/form-options/all')
        assert res.status_code == 200
        data = res.get_json()
        inactive = [o for o in data['options'] if o['is_active'] == 0]
        assert len(inactive) >= 1

        c = get_db_connection()
        c.execute("DELETE FROM form_options WHERE category = 'test_cat'")
        c.commit()
        c.close()

    def test_create_requires_admin(self, client):
        res = client.post('/api/form-options', json={
            'category': 'property_type', 'value': 'oficina', 'label': 'Oficina'
        })
        assert res.status_code in [302, 401, 403]

    def test_create_requires_fields(self, admin_client):
        res = admin_client.post('/api/form-options', json={})
        assert res.status_code == 400

    def test_create_invalid_category(self, admin_client):
        res = admin_client.post('/api/form-options', json={
            'category': 'invalid', 'value': 'x', 'label': 'X'
        })
        assert res.status_code == 400

    def test_create_and_delete(self, admin_client):
        res = admin_client.post('/api/form-options', json={
            'category': 'property_type', 'value': 'oficina', 'label': 'Oficina', 'icon': 'briefcase'
        })
        assert res.status_code == 200
        data = res.get_json()
        opt_id = data['id']

        res = admin_client.delete(f'/api/form-options/{opt_id}')
        assert res.status_code == 200

    def test_toggle_active(self, admin_client):
        res = admin_client.get('/api/form-options/all')
        options = res.get_json()['options']
        opt = options[0]
        new_active = 0 if opt['is_active'] else 1

        res = admin_client.put(f'/api/form-options/{opt["id"]}', json={'is_active': new_active})
        assert res.status_code == 200

        res = admin_client.put(f'/api/form-options/{opt["id"]}', json={'is_active': opt['is_active']})
        assert res.status_code == 200
