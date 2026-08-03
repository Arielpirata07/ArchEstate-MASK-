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


class TestPhoneAreaCodesPublic:
    def test_list_returns_grouped_codes(self, client):
        res = client.get('/api/phone-area-codes')
        assert res.status_code == 200
        data = res.get_json()
        assert 'codes' in data
        assert '+54' in data['codes']

    def test_list_by_country_code(self, client):
        res = client.get('/api/phone-area-codes?country_code=%2B54')
        assert res.status_code == 200
        data = res.get_json()
        assert '+54' in data['codes']
        assert len(data['codes']['+54']) >= 10

    def test_only_active_codes_returned(self, client):
        res = client.get('/api/phone-area-codes')
        data = res.get_json()
        for cc, codes in data['codes'].items():
            for c in codes:
                assert c['is_active'] == 1

    def test_seed_has_argentina_codes(self, client):
        res = client.get('/api/phone-area-codes?country_code=%2B54')
        data = res.get_json()
        codes = [c['code'] for c in data['codes']['+54']]
        assert '11' in codes
        assert '341' in codes
        assert '351' in codes
        assert '3541' in codes

    def test_seed_has_international_codes(self, client):
        res = client.get('/api/phone-area-codes')
        data = res.get_json()
        assert '+598' in data['codes']
        assert '+56' in data['codes']
        assert '+55' in data['codes']
        assert '+1' in data['codes']

    def test_empty_country_code_returns_all(self, client):
        res = client.get('/api/phone-area-codes')
        data = res.get_json()
        total = sum(len(codes) for codes in data['codes'].values())
        assert total >= 100


class TestPhoneAreaCodesAdmin:
    def test_list_all_requires_admin(self, client):
        res = client.get('/api/phone-area-codes/all')
        assert res.status_code in [302, 401, 403]

    def test_list_all_includes_inactive(self, admin_client):
        from models import get_db_connection
        conn = get_db_connection()
        conn.execute(
            "INSERT INTO phone_area_codes (code, city, province, country, country_code, sort_order, is_active) VALUES (?, ?, ?, ?, ?, ?, ?)",
            ('9999', 'Test City', 'Test', 'TestCountry', '+00', 1, 0)
        )
        conn.commit()
        conn.close()

        res = admin_client.get('/api/phone-area-codes/all')
        assert res.status_code == 200
        data = res.get_json()
        inactive = [c for c in data['codes'] if c['is_active'] == 0]
        assert len(inactive) >= 1

        conn = get_db_connection()
        conn.execute("DELETE FROM phone_area_codes WHERE code = '9999' AND country_code = '+00'")
        conn.commit()
        conn.close()

    def test_create_requires_admin(self, client):
        res = client.post('/api/phone-area-codes', json={
            'code': '1234', 'city': 'Test'
        })
        assert res.status_code in [302, 401, 403]

    def test_create_requires_fields(self, admin_client):
        res = admin_client.post('/api/phone-area-codes', json={})
        assert res.status_code == 400

    def test_create_and_delete(self, admin_client):
        res = admin_client.post('/api/phone-area-codes', json={
            'code': '9999', 'city': 'Test City', 'province': 'Test', 'country': 'Argentina', 'country_code': '+54'
        })
        assert res.status_code == 200
        area_id = res.get_json()['id']

        res = admin_client.delete(f'/api/phone-area-codes/{area_id}')
        assert res.status_code == 200

    def test_update_city(self, admin_client):
        res = admin_client.post('/api/phone-area-codes', json={
            'code': '8888', 'city': 'Original', 'province': 'P', 'country': 'Argentina', 'country_code': '+54'
        })
        area_id = res.get_json()['id']

        res = admin_client.put(f'/api/phone-area-codes/{area_id}', json={'city': 'Updated'})
        assert res.status_code == 200

        res = admin_client.get('/api/phone-area-codes/all')
        updated = [c for c in res.get_json()['codes'] if c['id'] == area_id][0]
        assert updated['city'] == 'Updated'

        admin_client.delete(f'/api/phone-area-codes/{area_id}')

    def test_toggle_active(self, admin_client):
        res = admin_client.post('/api/phone-area-codes', json={
            'code': '7777', 'city': 'Toggle', 'province': 'T', 'country': 'Argentina', 'country_code': '+54'
        })
        area_id = res.get_json()['id']

        res = admin_client.put(f'/api/phone-area-codes/{area_id}', json={'is_active': 0})
        assert res.status_code == 200

        res = admin_client.put(f'/api/phone-area-codes/{area_id}', json={'is_active': 1})
        assert res.status_code == 200

        admin_client.delete(f'/api/phone-area-codes/{area_id}')

    def test_update_duplicate_code_returns_409(self, admin_client):
        from models import get_db_connection
        conn = get_db_connection()
        conn.execute(
            "INSERT INTO phone_area_codes (code, city, province, country, country_code, sort_order, is_active) VALUES (?, ?, ?, ?, ?, ?, ?)",
            ('dup_a', 'CityA', 'P', 'Argentina', '+54', 1, 1)
        )
        conn.execute(
            "INSERT INTO phone_area_codes (code, city, province, country, country_code, sort_order, is_active) VALUES (?, ?, ?, ?, ?, ?, ?)",
            ('dup_b', 'CityB', 'P', 'Argentina', '+54', 2, 1)
        )
        conn.commit()
        row_a = conn.execute("SELECT id FROM phone_area_codes WHERE code='dup_a' AND country_code='+54'").fetchone()
        conn.close()

        res = admin_client.put(f'/api/phone-area-codes/{row_a["id"]}', json={'code': 'dup_b'})
        assert res.status_code == 409
        assert 'error' in res.get_json()

        conn = get_db_connection()
        conn.execute("DELETE FROM phone_area_codes WHERE code IN ('dup_a', 'dup_b') AND country_code = '+54'")
        conn.commit()
        conn.close()

    def test_update_nonexistent_returns_404(self, admin_client):
        res = admin_client.put('/api/phone-area-codes/99999', json={'city': 'X'})
        assert res.status_code == 404

    def test_delete_nonexistent_returns_404(self, admin_client):
        res = admin_client.delete('/api/phone-area-codes/99999')
        assert res.status_code == 404
        assert 'error' in res.get_json()


class TestPhoneAreaCodesValidation:
    def test_create_rejects_long_code(self, admin_client):
        res = admin_client.post('/api/phone-area-codes', json={
            'code': 'x' * 11, 'city': 'Test'
        })
        assert res.status_code == 400

    def test_create_rejects_long_city(self, admin_client):
        res = admin_client.post('/api/phone-area-codes', json={
            'code': '123', 'city': 'C' * 201
        })
        assert res.status_code == 400

    def test_create_rejects_empty_code(self, admin_client):
        res = admin_client.post('/api/phone-area-codes', json={
            'code': '', 'city': 'Test'
        })
        assert res.status_code == 400

    def test_create_rejects_empty_city(self, admin_client):
        res = admin_client.post('/api/phone-area-codes', json={
            'code': '123', 'city': ''
        })
        assert res.status_code == 400
