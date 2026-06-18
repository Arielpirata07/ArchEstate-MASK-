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

    def test_list_with_invalid_category_returns_empty(self, client):
        res = client.get('/api/form-options?category=nonexistent_cat')
        assert res.status_code == 200
        data = res.get_json()
        assert data['options'] == {}


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

    def test_update_label_and_icon(self, admin_client):
        res = admin_client.get('/api/form-options/all')
        opt = res.get_json()['options'][0]
        res = admin_client.put(f'/api/form-options/{opt["id"]}', json={
            'label': 'Updated Label', 'icon': 'new-icon', 'sort_order': 99
        })
        assert res.status_code == 200

        res = admin_client.get('/api/form-options/all')
        updated = [o for o in res.get_json()['options'] if o['id'] == opt['id']][0]
        assert updated['label'] == 'Updated Label'
        assert updated['icon'] == 'new-icon'
        assert updated['sort_order'] == 99

    def test_update_duplicate_value_returns_409(self, admin_client):
        from models import get_db_connection
        conn = get_db_connection()
        conn.execute(
            "INSERT INTO form_options (category, value, label, icon, sort_order, is_active) VALUES (?, ?, ?, ?, ?, ?)",
            ('test_dup_cat', 'val_a', 'A', '', 1, 1)
        )
        conn.execute(
            "INSERT INTO form_options (category, value, label, icon, sort_order, is_active) VALUES (?, ?, ?, ?, ?, ?)",
            ('test_dup_cat', 'val_b', 'B', '', 2, 1)
        )
        conn.commit()
        row_a = conn.execute("SELECT id FROM form_options WHERE category='test_dup_cat' AND value='val_a'").fetchone()
        conn.close()

        res = admin_client.put(f'/api/form-options/{row_a["id"]}', json={'value': 'val_b'})
        assert res.status_code == 409
        assert 'error' in res.get_json()

        conn = get_db_connection()
        conn.execute("DELETE FROM form_options WHERE category = 'test_dup_cat'")
        conn.commit()
        conn.close()

    def test_update_nonexistent_returns_404(self, admin_client):
        res = admin_client.put('/api/form-options/99999', json={'label': 'X'})
        assert res.status_code == 404


class TestFormOptionsDeleteFix:
    def test_delete_nonexistent_returns_404(self, admin_client):
        res = admin_client.delete('/api/form-options/99999')
        assert res.status_code == 404
        data = res.get_json()
        assert 'error' in data

    def test_delete_idempotent_after_double_delete(self, admin_client):
        res = admin_client.post('/api/form-options', json={
            'category': 'amenities', 'value': 'test_del', 'label': 'Test Del'
        })
        assert res.status_code == 200
        opt_id = res.get_json()['id']

        res = admin_client.delete(f'/api/form-options/{opt_id}')
        assert res.status_code == 200

        res = admin_client.delete(f'/api/form-options/{opt_id}')
        assert res.status_code == 404


class TestFormOptionsValidation:
    def test_create_rejects_long_value(self, admin_client):
        res = admin_client.post('/api/form-options', json={
            'category': 'amenities', 'value': 'x' * 101, 'label': 'Long'
        })
        assert res.status_code == 400
        assert '100 caracteres' in res.get_json()['error']

    def test_create_rejects_long_label(self, admin_client):
        res = admin_client.post('/api/form-options', json={
            'category': 'amenities', 'value': 'ok', 'label': 'L' * 201
        })
        assert res.status_code == 400
        assert '200 caracteres' in res.get_json()['error']

    def test_create_accepts_max_length_value(self, admin_client):
        res = admin_client.post('/api/form-options', json={
            'category': 'amenities', 'value': 'a' * 100, 'label': 'Max'
        })
        assert res.status_code == 200
        opt_id = res.get_json()['id']
        admin_client.delete(f'/api/form-options/{opt_id}')

    def test_create_rejects_empty_value(self, admin_client):
        res = admin_client.post('/api/form-options', json={
            'category': 'amenities', 'value': '', 'label': 'Empty'
        })
        assert res.status_code == 400

    def test_create_rejects_empty_label(self, admin_client):
        res = admin_client.post('/api/form-options', json={
            'category': 'amenities', 'value': 'valid', 'label': ''
        })
        assert res.status_code == 400

    def test_update_rejects_long_value(self, admin_client):
        res = admin_client.get('/api/form-options/all')
        opt = res.get_json()['options'][0]
        res = admin_client.put(f'/api/form-options/{opt["id"]}', json={
            'value': 'x' * 101
        })
        assert res.status_code == 400

    def test_update_rejects_long_label(self, admin_client):
        res = admin_client.get('/api/form-options/all')
        opt = res.get_json()['options'][0]
        res = admin_client.put(f'/api/form-options/{opt["id"]}', json={
            'label': 'L' * 201
        })
        assert res.status_code == 400


class TestFormOptionsSortOrder:
    def test_sort_order_shift_on_create(self, admin_client):
        from models import get_db_connection
        res = admin_client.post('/api/form-options', json={
            'category': 'amenities', 'value': 'so_test_a', 'label': 'SortA', 'sort_order': 1
        })
        assert res.status_code == 200
        id_a = res.get_json()['id']

        res = admin_client.post('/api/form-options', json={
            'category': 'amenities', 'value': 'so_test_b', 'label': 'SortB', 'sort_order': 1
        })
        assert res.status_code == 200
        id_b = res.get_json()['id']

        conn = get_db_connection()
        a = conn.execute('SELECT sort_order FROM form_options WHERE id = ?', (id_a,)).fetchone()
        b = conn.execute('SELECT sort_order FROM form_options WHERE id = ?', (id_b,)).fetchone()
        conn.close()

        assert b['sort_order'] == 1
        assert a['sort_order'] == 2

        admin_client.delete(f'/api/form-options/{id_a}')
        admin_client.delete(f'/api/form-options/{id_b}')

    def test_sort_order_decrement_on_delete(self, admin_client):
        from models import get_db_connection
        res = admin_client.post('/api/form-options', json={
            'category': 'amenities', 'value': 'so_del_a', 'label': 'DelA', 'sort_order': 50
        })
        id_a = res.get_json()['id']

        res = admin_client.post('/api/form-options', json={
            'category': 'amenities', 'value': 'so_del_b', 'label': 'DelB', 'sort_order': 51
        })
        id_b = res.get_json()['id']

        admin_client.delete(f'/api/form-options/{id_a}')

        conn = get_db_connection()
        b = conn.execute('SELECT sort_order FROM form_options WHERE id = ?', (id_b,)).fetchone()
        conn.close()
        assert b['sort_order'] == 50

        admin_client.delete(f'/api/form-options/{id_b}')

    def test_create_does_not_corrupt_sort_on_duplicate(self, admin_client):
        from models import get_db_connection
        res = admin_client.post('/api/form-options', json={
            'category': 'amenities', 'value': 'corrupt_test', 'label': 'Corrupt'
        })
        assert res.status_code == 200
        id1 = res.get_json()['id']

        original_sort = admin_client.get('/api/form-options/all')
        original_orders = {o['id']: o['sort_order'] for o in original_sort.get_json()['options']}

        res = admin_client.post('/api/form-options', json={
            'category': 'amenities', 'value': 'corrupt_test', 'label': 'Corrupt'
        })
        assert res.status_code == 409

        after_sort = admin_client.get('/api/form-options/all')
        after_orders = {o['id']: o['sort_order'] for o in after_sort.get_json()['options']}

        for oid, order in original_orders.items():
            if oid in after_orders:
                assert after_orders[oid] == order, f'Sort order corrupted for id {oid}'

        admin_client.delete(f'/api/form-options/{id1}')

    def test_update_sort_order_move_up_no_gap(self, admin_client):
        from models import get_db_connection
        ids = []
        for i in range(4):
            res = admin_client.post('/api/form-options', json={
                'category': 'amenities', 'value': f'up_gap_{i}', 'label': f'UpGap{i}', 'sort_order': 50 + i
            })
            ids.append(res.get_json()['id'])

        admin_client.put(f'/api/form-options/{ids[3]}', json={'sort_order': 50})

        conn = get_db_connection()
        orders = {}
        for oid in ids:
            row = conn.execute('SELECT sort_order FROM form_options WHERE id = ?', (oid,)).fetchone()
            orders[oid] = row['sort_order']
        conn.close()

        assert orders[ids[3]] == 50
        assert orders[ids[0]] == 51
        assert orders[ids[1]] == 52
        assert orders[ids[2]] == 53

        for oid in ids:
            admin_client.delete(f'/api/form-options/{oid}')

    def test_update_sort_order_move_down_no_gap(self, admin_client):
        from models import get_db_connection
        ids = []
        for i in range(4):
            res = admin_client.post('/api/form-options', json={
                'category': 'amenities', 'value': f'dn_gap_{i}', 'label': f'DnGap{i}', 'sort_order': 60 + i
            })
            ids.append(res.get_json()['id'])

        admin_client.put(f'/api/form-options/{ids[0]}', json={'sort_order': 63})

        conn = get_db_connection()
        orders = {}
        for oid in ids:
            row = conn.execute('SELECT sort_order FROM form_options WHERE id = ?', (oid,)).fetchone()
            orders[oid] = row['sort_order']
        conn.close()

        assert orders[ids[0]] == 63
        assert orders[ids[1]] == 60
        assert orders[ids[2]] == 61
        assert orders[ids[3]] == 62

        for oid in ids:
            admin_client.delete(f'/api/form-options/{oid}')
