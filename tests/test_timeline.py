"""Tests del timeline unificado por lead (Fase 3, solo lectura)."""
import uuid

from werkzeug.security import generate_password_hash


def _make_pro(db):
    unique = uuid.uuid4().hex[:8]
    name = f'Tl Pro {unique}'
    cur = db.execute(
        'INSERT INTO users (username, email, hash, role, phone, phone_e164, is_active)'
        ' VALUES (?, ?, ?, ?, ?, ?, 1)',
        (name, f'tl_{unique}@test.com', generate_password_hash('pass'),
         'professional', '+5491198765432', '+5491198765432')
    )
    user_id = cur.lastrowid
    db.execute(
        'INSERT INTO professionals (user_id, name, license, specialty, status) VALUES (?, ?, ?, ?, ?)',
        (user_id, name, f'LIC-{unique}', 'general', 'approved')
    )
    db.commit()
    return user_id, name


def _make_lead(db):
    unique = uuid.uuid4().hex[:8]
    cur = db.execute(
        '''INSERT INTO leads (type, property_type, zone, province, budget, currency, phone, email, user_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
        ('comprar', 'departamento', 'Palermo', 'Buenos Aires', '200000', 'USD',
         '+5491112345678', f'tl_{unique}@test.com', 1)
    )
    db.commit()
    return cur.lastrowid


def _login(client, user_id, username, role):
    with client.session_transaction() as sess:
        sess['user_id'] = user_id
        sess['username'] = username
        sess['role'] = role


class TestTimelineApi:
    def test_returns_created_entry(self, client, db):
        user_id, name = _make_pro(db)
        _login(client, user_id, name, 'professional')
        lead_id = _make_lead(db)
        resp = client.get(f'/api/leads/{lead_id}/timeline')
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['success'] is True
        kinds = [e['kind'] for e in data['timeline']]
        assert 'created' in kinds

    def test_aggregates_stage_tracking_and_report(self, client, db):
        user_id, name = _make_pro(db)
        _login(client, user_id, name, 'professional')
        lead_id = _make_lead(db)
        client.post(f'/api/lead/{lead_id}/toggle-status', json={'status': 'seen'})
        client.post(f'/api/pipeline/lead/{lead_id}/move', json={'stage': 'contacted'})
        client.post(f'/api/lead/{lead_id}/report', json={'notes': 'n'})
        resp = client.get(f'/api/leads/{lead_id}/timeline')
        kinds = [e['kind'] for e in resp.get_json()['timeline']]
        for expected in ('created', 'seen', 'contacted', 'stage', 'report'):
            assert expected in kinds

    def test_missing_lead_404(self, client, db):
        user_id, name = _make_pro(db)
        _login(client, user_id, name, 'professional')
        resp = client.get('/api/leads/999999/timeline')
        assert resp.status_code == 404

    def test_client_cannot_access(self, client, db):
        unique = uuid.uuid4().hex[:8]
        username = f'tl_cli_{unique}'
        cur = db.execute(
            'INSERT INTO users (username, email, hash, role, phone, phone_e164, is_active)'
            ' VALUES (?, ?, ?, ?, ?, ?, 1)',
            (username, f'{unique}@test.com', generate_password_hash('pass'),
             'client', '+5491112345678', '+5491112345678')
        )
        db.commit()
        _login(client, cur.lastrowid, username, 'client')
        lead_id = _make_lead(db)
        resp = client.get(f'/api/leads/{lead_id}/timeline')
        assert resp.status_code in (302, 403)


class TestTimelinePage:
    def test_lead_detail_renders_timeline(self, client, db):
        user_id, name = _make_pro(db)
        _login(client, user_id, name, 'professional')
        lead_id = _make_lead(db)
        client.post(f'/api/lead/{lead_id}/toggle-status', json={'status': 'seen'})
        resp = client.get(f'/profesional/lead/{lead_id}')
        assert resp.status_code == 200
        html = resp.data.decode()
        assert 'Historial del lead' in html or 'Lead history' in html
