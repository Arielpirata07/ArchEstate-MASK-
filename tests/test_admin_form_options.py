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


@pytest.fixture
def phone_audit_data(db):
    """Crea un profesional y eventos de phone_revealed/wa_link_generated para tests de auditoría."""
    from werkzeug.security import generate_password_hash
    import uuid

    uname = f'pro_audit_{uuid.uuid4().hex[:8]}'
    cur = db.execute(
        'INSERT INTO users (username, email, hash, role, phone, phone_e164, phone_format_valid) '
        'VALUES (?, ?, ?, ?, ?, ?, 1)',
        (uname, f'{uname}@example.com', generate_password_hash('pro123'),
         'professional', '+5491144445555', '+5491144445555')
    )
    pro_user_id = cur.lastrowid
    db.execute(
        'INSERT INTO professionals (user_id, name, license, specialty, status) VALUES (?, ?, ?, ?, ?)',
        (pro_user_id, uname, f'LIC-{uname}', 'General', 'approved')
    )
    lead_id = db.execute(
        'INSERT INTO leads (type, zone, budget, currency, phone, email, phone_format_valid) '
        'VALUES (?, ?, ?, ?, ?, ?, 1)',
        ('Comprar', 'Palermo', '500000', 'USD', '+5491144445555', f'{uname}@lead.com')
    ).lastrowid
    db.execute(
        "INSERT INTO events (user_id, lead_id, event, ts) VALUES (?, ?, 'phone_revealed', datetime('now', '-1 day'))",
        (pro_user_id, lead_id)
    )
    db.execute(
        "INSERT INTO events (user_id, lead_id, event, ts) VALUES (?, ?, 'wa_link_generated', datetime('now', '-2 hours'))",
        (pro_user_id, lead_id)
    )
    db.commit()
    return pro_user_id, uname, lead_id


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


class TestPhoneAudit:
    @pytest.fixture(autouse=True)
    def _clean_events(self, db):
        db.execute('DELETE FROM events')
        db.commit()

    def test_phone_audit_empty(self, admin_client, db):
        res = admin_client.get('/api/admin/phone-audit')
        assert res.status_code == 200
        data = res.get_json()
        assert data['success'] is True
        assert data['data'] == []
        assert data['total'] == 0

    def test_phone_audit_returns_events(self, admin_client, db, phone_audit_data):
        pro_user_id, uname, lead_id = phone_audit_data
        res = admin_client.get('/api/admin/phone-audit')
        assert res.status_code == 200
        data = res.get_json()
        assert data['success'] is True
        assert data['total'] == 2
        assert len(data['data']) == 2
        events = [e['event'] for e in data['data']]
        assert 'phone_revealed' in events
        assert 'wa_link_generated' in events
        for entry in data['data']:
            assert entry['profesional'] == uname
            assert entry['lead_id'] == lead_id

    def test_phone_audit_filter_by_profesional(self, admin_client, db, phone_audit_data):
        pro_user_id, uname, lead_id = phone_audit_data
        res = admin_client.get(f'/api/admin/phone-audit?profesional={uname}')
        assert res.status_code == 200
        data = res.get_json()
        assert data['total'] == 2

        res = admin_client.get('/api/admin/phone-audit?profesional=nonexistent')
        assert res.status_code == 200
        data = res.get_json()
        assert data['total'] == 0
        assert data['data'] == []

    def test_phone_audit_filter_by_evento(self, admin_client, db, phone_audit_data):
        pro_user_id, uname, lead_id = phone_audit_data
        res = admin_client.get('/api/admin/phone-audit?evento=phone_revealed')
        assert res.status_code == 200
        data = res.get_json()
        assert data['total'] == 1
        assert data['data'][0]['event'] == 'phone_revealed'

        res = admin_client.get('/api/admin/phone-audit?evento=wa_link_generated')
        assert res.status_code == 200
        data = res.get_json()
        assert data['total'] == 1
        assert data['data'][0]['event'] == 'wa_link_generated'

    def test_phone_audit_pagination(self, admin_client, db):
        from werkzeug.security import generate_password_hash
        import uuid

        lead_id = db.execute(
            'INSERT INTO leads (type, zone, budget, currency, phone, email, phone_format_valid) '
            'VALUES (?, ?, ?, ?, ?, ?, 1)',
            ('Comprar', 'Palermo', '500000', 'USD', '+5491144445555', 'lead@test.com')
        ).lastrowid
        pro_user_id = None
        for i in range(3):
            uname = f'pro_pag_{uuid.uuid4().hex[:8]}'
            cur = db.execute(
                'INSERT INTO users (username, email, hash, role, phone, phone_e164, phone_format_valid) '
                'VALUES (?, ?, ?, ?, ?, ?, 1)',
                (uname, f'{uname}@example.com', generate_password_hash('pro123'),
                 'professional', '+5491144445555', '+5491144445555')
            )
            uid = cur.lastrowid
            if pro_user_id is None:
                pro_user_id = uid
            db.execute(
                'INSERT INTO professionals (user_id, name, license, specialty, status) VALUES (?, ?, ?, ?, ?)',
                (uid, uname, f'LIC-{uname}', 'General', 'approved')
            )
            db.execute(
                "INSERT INTO events (user_id, lead_id, event, ts) VALUES (?, ?, 'phone_revealed', datetime('now', ?))",
                (uid, lead_id, f'-{i} hours')
            )
        db.commit()

        res = admin_client.get('/api/admin/phone-audit?per_page=2&page=1')
        assert res.status_code == 200
        data = res.get_json()
        assert data['total'] == 3
        assert len(data['data']) == 2
        assert data['page'] == 1

        res = admin_client.get('/api/admin/phone-audit?per_page=2&page=2')
        data = res.get_json()
        assert len(data['data']) == 1
        assert data['page'] == 2

    def test_phone_audit_forbidden_client(self, client, db):
        from werkzeug.security import generate_password_hash
        import uuid
        uname = f'no_admin_{uuid.uuid4().hex[:8]}'
        cur = db.execute(
            'INSERT INTO users (username, email, hash, role) VALUES (?, ?, ?, ?)',
            (uname, f'{uname}@example.com', generate_password_hash('test123'), 'client')
        )
        uid = cur.lastrowid
        db.commit()
        with client.session_transaction() as sess:
            sess['user_id'] = uid
            sess['username'] = uname
            sess['role'] = 'client'
        res = client.get('/api/admin/phone-audit')
        # admin_required redirects non-admin to public.index (302)
        assert res.status_code == 302

    def test_phone_audit_invalid_dates(self, admin_client):
        res = admin_client.get('/api/admin/phone-audit?desde=not-a-date')
        assert res.status_code == 400

        res = admin_client.get('/api/admin/phone-audit?hasta=also-invalid')
        assert res.status_code == 400

    def test_phone_audit_invalid_pagination(self, admin_client):
        res = admin_client.get('/api/admin/phone-audit?page=abc')
        assert res.status_code == 400

        res = admin_client.get('/api/admin/phone-audit?per_page=-1')
        assert res.status_code == 200  # se clamp a valor por defecto
