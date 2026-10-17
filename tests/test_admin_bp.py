import uuid

import pytest
from werkzeug.security import generate_password_hash

import models


@pytest.fixture
def admin_client(client):
    conn = models.get_db_connection()
    conn.execute("UPDATE users SET role = 'admin', is_active = 1 WHERE username = 'admin'")
    conn.commit()
    conn.close()
    with client.session_transaction() as sess:
        sess['user_id'] = 1
        sess['username'] = 'admin'
        sess['role'] = 'admin'
    return client


@pytest.fixture
def sample_professional(db):
    unique = uuid.uuid4().hex[:8]
    pro_name = f'Abp {unique}'
    cursor = db.execute(
        'INSERT INTO users (username, email, hash, role, phone, phone_e164, is_active) VALUES (?, ?, ?, ?, ?, ?, ?)',
        (pro_name, f'abp_{unique}@test.com', generate_password_hash('pass'), 'professional', '+5491198765432', '+5491198765432', 1)
    )
    user_id = cursor.lastrowid
    pro_id = db.execute(
        'INSERT INTO professionals (user_id, name, license, specialty, status) VALUES (?, ?, ?, ?, ?)',
        (user_id, pro_name, f'LIC-{unique}', 'arquitectura', 'pending')
    ).lastrowid
    db.commit()
    return user_id, pro_id


@pytest.fixture
def sample_lead(db):
    unique = uuid.uuid4().hex[:8]
    cursor = db.execute(
        '''INSERT INTO leads (type, property_type, zone, province, budget, currency, phone, email, user_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
        ('comprar', 'departamento', 'Palermo', 'Buenos Aires', '200000', 'USD', f'+54911123{unique[:4]}', f'abp_{unique}@test.com', 1)
    )
    db.commit()
    return cursor.lastrowid


@pytest.fixture
def sample_report(db, sample_lead, sample_professional):
    user_id, _ = sample_professional
    cursor = db.execute(
        'INSERT INTO lead_reports (lead_id, reported_by, reason, status) VALUES (?, ?, ?, ?)',
        (sample_lead, user_id, 'telefono_inexistente', 'pending')
    )
    db.commit()
    return cursor.lastrowid


class TestProfessionalApproval:
    def test_list_professionals(self, admin_client):
        resp = admin_client.get('/api/professionals')
        assert resp.status_code == 200
        assert resp.get_json()['success'] is True
    def test_approve_professional(self, admin_client, sample_professional):
        _, pro_id = sample_professional
        resp = admin_client.post(f'/api/admin/professional/{pro_id}/status', json={'status': 'approved'})
        assert resp.get_json()['success'] is True
        pro = models.get_professional_by_user_id(sample_professional[0])
        assert pro['status'] == 'approved'

    def test_reject_professional(self, admin_client, sample_professional):
        _, pro_id = sample_professional
        resp = admin_client.post(f'/api/admin/professional/{pro_id}/status', json={'status': 'rejected'})
        assert resp.get_json()['success'] is True

    def test_invalid_status_400(self, admin_client, sample_professional):
        _, pro_id = sample_professional
        resp = admin_client.post(f'/api/admin/professional/{pro_id}/status', json={'status': 'maybe'})
        assert resp.status_code == 400

    def test_missing_professional_404(self, admin_client):
        resp = admin_client.post('/api/admin/professional/999999/status', json={'status': 'approved'})
        assert resp.status_code == 404

    def test_non_admin_forbidden(self, client, sample_professional):
        user_id, pro_name = sample_professional
        with client.session_transaction() as sess:
            sess['user_id'] = user_id
            sess['username'] = pro_name
            sess['role'] = 'professional'
        _, pro_id = sample_professional
        resp = client.post(f'/api/admin/professional/{pro_id}/status', json={'status': 'approved'})
        assert resp.status_code in (302, 401, 403)


class TestLeadManagement:
    def test_get_lead_detail(self, admin_client, sample_lead):
        resp = admin_client.get(f'/api/admin/lead/{sample_lead}')
        assert resp.status_code == 200

    def test_get_missing_lead_404(self, admin_client):
        resp = admin_client.get('/api/admin/lead/999999')
        assert resp.status_code == 404

    def test_admin_stats(self, admin_client):
        resp = admin_client.get('/api/admin/stats')
        assert resp.status_code == 200


class TestReports:
    def test_list_reports(self, admin_client, sample_report):
        resp = admin_client.get('/api/admin/reports')
        assert resp.status_code == 200
        assert resp.get_json()['success'] is True

    def test_dismiss_restore_cycle(self, admin_client, sample_report):
        assert admin_client.post(f'/api/admin/report/{sample_report}/dismiss').get_json()['success'] is True
        assert admin_client.post(f'/api/admin/report/{sample_report}/restore').get_json()['success'] is True

    def test_delete_report(self, admin_client, sample_report):
        resp = admin_client.post(f'/api/admin/report/{sample_report}/delete')
        assert resp.get_json()['success'] is True

    def test_missing_report_404(self, admin_client):
        assert admin_client.post('/api/admin/report/999999/dismiss').status_code == 404


class TestUserManagement:
    def test_set_active_false_true(self, admin_client, sample_professional):
        user_id, _ = sample_professional
        assert admin_client.post(f'/api/admin/user/{user_id}/set-active', json={'is_active': False}).get_json()['success'] is True
        assert admin_client.post(f'/api/admin/user/{user_id}/set-active', json={'is_active': True}).get_json()['success'] is True

    def test_cannot_deactivate_self(self, admin_client):
        resp = admin_client.post('/api/admin/user/1/set-active', json={'is_active': False})
        assert resp.status_code == 403

    def test_invalid_state_400(self, admin_client, sample_professional):
        user_id, _ = sample_professional
        resp = admin_client.post(f'/api/admin/user/{user_id}/set-active', json={'is_active': 'x'})
        assert resp.status_code == 400

    def test_reset_password(self, admin_client, sample_professional):
        user_id, _ = sample_professional
        resp = admin_client.post(f'/api/admin/user/{user_id}/reset-password', json={'password': 'NewPass123'})
        assert resp.get_json()['success'] is True

    def test_reset_password_weak_400(self, admin_client, sample_professional):
        user_id, _ = sample_professional
        resp = admin_client.post(f'/api/admin/user/{user_id}/reset-password', json={'password': 'x'})
        assert resp.status_code == 400


class TestAdminNotifications:
    def test_send_requires_title(self, admin_client):
        resp = admin_client.post('/api/admin/send-notification', json={'title': '', 'body': 'hola', 'broadcast': True})
        assert resp.status_code == 400

    def test_send_broadcast(self, admin_client):
        resp = admin_client.post('/api/admin/send-notification', json={'title': 'Aviso', 'body': 'hola', 'broadcast': True})
        assert resp.get_json()['success'] is True

    def test_notification_log(self, admin_client):
        resp = admin_client.get('/api/admin/notification-log')
        assert resp.status_code == 200


class TestAdminSla:
    def _mk(self, db, elapsed, zone='Palermo', pro_id=1):
        import uuid as _u
        unique = _u.uuid4().hex[:8]
        from datetime import datetime, timedelta
        created = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d %H:%M:%S')
        cur = db.execute(
            '''INSERT INTO leads (type, property_type, zone, province, budget, currency, phone, email, user_id, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
            ('comprar', 'departamento', zone, 'Buenos Aires', '100000', 'USD',
             f'+5491112{unique[:5]}', f'sla_{unique}@test.com', 1, created)
        )
        lead_id = cur.lastrowid
        db.execute(
            'INSERT INTO lead_first_contact (lead_id, professional_id, contact_at, source, business_hours_elapsed) '
            "VALUES (?, ?, datetime('now'), 'stage', ?)",
            (lead_id, pro_id, elapsed)
        )
        db.commit()
        return lead_id

    def test_requires_admin(self, client):
        resp = client.get('/api/admin/sla')
        assert resp.status_code in (302, 401, 403)

    def test_returns_kpis(self, admin_client, db):
        self._mk(db, elapsed=3.0)    # met
        self._mk(db, elapsed=30.0)   # breached
        resp = admin_client.get('/api/admin/sla?days=30')
        data = resp.get_json()
        assert resp.status_code == 200
        assert data['success'] is True
        sla = data['sla']
        assert sla['days'] == 30
        assert sla['threshold_hours'] == 24.0
        assert sla['contacted'] >= 2
        assert sla['met'] >= 1
        assert sla['breached'] >= 1
        assert sla['compliance_pct'] >= 0.0
        assert 'median_hours' in sla and 'p90_hours' in sla
        assert isinstance(sla['by_professional'], list)
        assert isinstance(sla['by_zone'], list)

    def test_invalid_days_falls_back(self, admin_client):
        resp = admin_client.get('/api/admin/sla?days=999')
        assert resp.get_json()['sla']['days'] == 30

    def test_panel_renders_in_admin_view(self, admin_client):
        resp = admin_client.get('/admin')
        assert resp.status_code == 200
        html = resp.data.decode()
        assert 'panel-sla' in html
        assert 'sla-cards' in html
        assert 'adm-sla-period' in html
