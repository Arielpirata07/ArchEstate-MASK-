import uuid
import pytest
from werkzeug.security import generate_password_hash

import models


@pytest.fixture
def pipeline_pro(db):
    unique = uuid.uuid4().hex[:8]
    pro_name = f'Pipe Pro {unique}'
    cursor = db.execute(
        'INSERT INTO users (username, email, hash, role, phone, phone_e164, is_active) VALUES (?, ?, ?, ?, ?, ?, ?)',
        (pro_name, f'pipe_{unique}@test.com', generate_password_hash('pass'), 'professional', '+5491198765432', '+5491198765432', 1)
    )
    db.commit()
    user_id = cursor.lastrowid
    db.execute(
        'INSERT INTO professionals (user_id, name, license, specialty, status) VALUES (?, ?, ?, ?, ?)',
        (user_id, pro_name, f'LIC-{unique}', 'general', 'approved')
    )
    db.commit()
    return user_id, pro_name


@pytest.fixture
def pipeline_lead(db):
    unique = uuid.uuid4().hex[:8]
    cursor = db.execute(
        '''INSERT INTO leads (type, property_type, zone, province, budget, currency, phone, email, user_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
        ('comprar', 'departamento', 'Palermo', 'Buenos Aires', '200000', 'USD', f'+54911123{unique[:4]}', f'pipe_{unique}@test.com', 1)
    )
    db.commit()
    return cursor.lastrowid


def _login_as_pro(client, pipeline_pro):
    user_id, pro_name = pipeline_pro
    with client.session_transaction() as sess:
        sess['user_id'] = user_id
        sess['username'] = pro_name
        sess['role'] = 'professional'
    return user_id


class TestPipelineMove:
    def test_move_creates_stage_row(self, client, db, pipeline_pro, pipeline_lead):
        user_id = _login_as_pro(client, pipeline_pro)
        resp = client.post(f'/api/pipeline/lead/{pipeline_lead}/move', json={'stage': 'contacted'})
        data = resp.get_json()
        assert resp.status_code == 200
        assert data['success'] is True
        assert data['from_stage'] == 'new'
        assert data['to_stage'] == 'contacted'
        row = db.execute(
            'SELECT stage FROM lead_stages WHERE professional_id = ? AND lead_id = ?',
            (user_id, pipeline_lead)
        ).fetchone()
        assert row['stage'] == 'contacted'

    def test_move_records_history(self, client, db, pipeline_pro, pipeline_lead):
        user_id = _login_as_pro(client, pipeline_pro)
        client.post(f'/api/pipeline/lead/{pipeline_lead}/move', json={'stage': 'contacted'})
        client.post(f'/api/pipeline/lead/{pipeline_lead}/move', json={'stage': 'visit'})
        rows = db.execute(
            'SELECT from_stage, to_stage FROM lead_stage_history WHERE professional_id = ? AND lead_id = ? ORDER BY id',
            (user_id, pipeline_lead)
        ).fetchall()
        assert [(r['from_stage'], r['to_stage']) for r in rows] == [('new', 'contacted'), ('contacted', 'visit')]

    def test_move_invalid_stage_400(self, client, pipeline_pro, pipeline_lead):
        _login_as_pro(client, pipeline_pro)
        resp = client.post(f'/api/pipeline/lead/{pipeline_lead}/move', json={'stage': 'nope'})
        assert resp.status_code == 400
        assert resp.get_json()['success'] is False

    def test_move_missing_lead_404(self, client, pipeline_pro):
        _login_as_pro(client, pipeline_pro)
        resp = client.post('/api/pipeline/lead/999999/move', json={'stage': 'contacted'})
        assert resp.status_code == 404

    def test_move_updates_tracking_contacted(self, client, db, pipeline_pro, pipeline_lead):
        user_id = _login_as_pro(client, pipeline_pro)
        client.post(f'/api/pipeline/lead/{pipeline_lead}/move', json={'stage': 'negotiation'})
        row = db.execute(
            'SELECT contacted FROM lead_tracking WHERE professional_id = ? AND lead_id = ?',
            (user_id, pipeline_lead)
        ).fetchone()
        assert row is not None and row['contacted'] == 1

    def test_move_to_new_does_not_force_contacted(self, client, db, pipeline_pro, pipeline_lead):
        user_id = _login_as_pro(client, pipeline_pro)
        client.post(f'/api/pipeline/lead/{pipeline_lead}/move', json={'stage': 'new'})
        row = db.execute(
            'SELECT contacted FROM lead_tracking WHERE professional_id = ? AND lead_id = ?',
            (user_id, pipeline_lead)
        ).fetchone()
        assert row is None or row['contacted'] == 0

    def test_same_stage_move_is_upsert(self, client, db, pipeline_pro, pipeline_lead):
        user_id = _login_as_pro(client, pipeline_pro)
        client.post(f'/api/pipeline/lead/{pipeline_lead}/move', json={'stage': 'contacted'})
        client.post(f'/api/pipeline/lead/{pipeline_lead}/move', json={'stage': 'contacted'})
        rows = db.execute(
            'SELECT id FROM lead_stages WHERE professional_id = ? AND lead_id = ?',
            (user_id, pipeline_lead)
        ).fetchall()
        assert len(rows) == 1


class TestPipelineRead:
    def test_stages_returns_counts(self, client, db, pipeline_pro, pipeline_lead):
        _login_as_pro(client, pipeline_pro)
        client.post(f'/api/pipeline/lead/{pipeline_lead}/move', json={'stage': 'visit'})
        before = {s['stage']: s['count'] for s in client.get('/api/pipeline/stages?my_leads=0').get_json()['stages']}
        cursor = db.execute(
            '''INSERT INTO leads (type, property_type, zone, province, budget, currency, phone, email, user_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
            ('comprar', 'casa', 'ZonaX', 'CABA', '100000', 'USD', '+549110000000', 'new_stage@test.com', 1)
        )
        db.commit()
        assert cursor.lastrowid
        resp = client.get('/api/pipeline/stages?my_leads=0')
        data = resp.get_json()
        assert data['success'] is True
        counts = {s['stage']: s['count'] for s in data['stages']}
        assert counts['visit'] == before['visit']
        assert counts['new'] == before['new'] + 1
        assert set(counts) == set(models.PIPELINE_STAGES)

    def test_leads_by_stage(self, client, pipeline_pro, pipeline_lead):
        _login_as_pro(client, pipeline_pro)
        client.post(f'/api/pipeline/lead/{pipeline_lead}/move', json={'stage': 'proposal'})
        resp = client.get('/api/pipeline/leads?stage=proposal&my_leads=0')
        data = resp.get_json()
        assert data['success'] is True
        assert [l['id'] for l in data['leads']] == [pipeline_lead]
        assert data['leads'][0]['pipeline_stage'] == 'proposal'
        resp = client.get('/api/pipeline/leads?stage=new&my_leads=0')
        assert pipeline_lead not in [l['id'] for l in resp.get_json()['leads']]

    def test_leads_invalid_stage_400(self, client, pipeline_pro):
        _login_as_pro(client, pipeline_pro)
        resp = client.get('/api/pipeline/leads?stage=nope')
        assert resp.status_code == 400

    def test_stats_returns_metrics(self, client, pipeline_pro, pipeline_lead):
        _login_as_pro(client, pipeline_pro)
        client.post(f'/api/pipeline/lead/{pipeline_lead}/move', json={'stage': 'contacted'})
        resp = client.get('/api/pipeline/stats')
        data = resp.get_json()
        assert data['success'] is True
        assert data['stats']['counts']['contacted'] == 1
        assert data['stats']['total_moves'] == 1
        assert 'avg_days_in_stage' in data['stats']

    def test_bulk_move(self, client, db, pipeline_pro, pipeline_lead):
        user_id = _login_as_pro(client, pipeline_pro)
        resp = client.post('/api/pipeline/leads/bulk-move', json={'ids': [pipeline_lead], 'stage': 'closed_won'})
        data = resp.get_json()
        assert data['success'] is True
        assert data['moved'] == 1
        assert models.get_lead_stage(user_id, pipeline_lead) == 'closed_won'

    def test_non_professional_cannot_move(self, client, auth_client, pipeline_lead):
        resp = client.post(f'/api/pipeline/lead/{pipeline_lead}/move', json={'stage': 'contacted'})
        assert resp.status_code in (302, 403)
