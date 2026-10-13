import uuid
import pytest
from werkzeug.security import generate_password_hash

import models


@pytest.fixture
def dash_pro(db):
    unique = uuid.uuid4().hex[:8]
    pro_name = f'Dash Pro {unique}'
    cursor = db.execute(
        'INSERT INTO users (username, email, hash, role, phone, phone_e164, is_active) VALUES (?, ?, ?, ?, ?, ?, ?)',
        (pro_name, f'dash_{unique}@test.com', generate_password_hash('pass'), 'professional', '+5491198765432', '+5491198765432', 1)
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
def dash_leads(db):
    unique = uuid.uuid4().hex[:8]
    ids = []
    for i, (zone, ptype) in enumerate([('Palermo', 'departamento'), ('Palermo', 'casa'), ('Recoleta', 'departamento')]):
        cursor = db.execute(
            '''INSERT INTO leads (type, property_type, zone, province, budget, currency, phone, email, user_id, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now', ?))''',
            ('comprar', ptype, zone, 'Buenos Aires', str(100000 * (i + 1)), 'USD', f'+54911123{unique[:4]}', f'dash_{unique}_{i}@test.com', 1, f'-{i} days')
        )
        ids.append(cursor.lastrowid)
    db.commit()
    return ids


def _login_as_pro(client, dash_pro):
    user_id, pro_name = dash_pro
    with client.session_transaction() as sess:
        sess['user_id'] = user_id
        sess['username'] = pro_name
        sess['role'] = 'professional'
    return user_id


class TestDashboard:
    def test_summary_returns_kpis(self, client, dash_pro, dash_leads):
        _login_as_pro(client, dash_pro)
        resp = client.get('/api/dashboard/summary?my_leads=0')
        data = resp.get_json()
        assert resp.status_code == 200
        assert data['success'] is True
        s = data['summary']
        assert s['total_leads'] >= 3
        assert s['new_this_week'] >= 3
        assert 'contact_rate' in s and 'avg_budget' in s
        assert s['avg_budget'] > 0
        assert 'vs_last_week' in s and 'leads' in s['vs_last_week']
        assert s['top_zone'] == 'Palermo'
        assert s['top_property_type'] == 'departamento'

    def test_trends_returns_days(self, client, dash_pro, dash_leads):
        _login_as_pro(client, dash_pro)
        resp = client.get('/api/dashboard/trends?days=7&my_leads=0')
        data = resp.get_json()
        assert data['success'] is True
        assert data['days'] == 7
        assert len(data['trends']) == 7
        assert sum(p['count'] for p in data['trends']) >= 3

    def test_pipeline_returns_funnel(self, client, dash_pro, dash_leads):
        user_id = _login_as_pro(client, dash_pro)
        models.move_lead_stage(user_id, dash_leads[0], 'contacted')
        resp = client.get('/api/dashboard/pipeline')
        data = resp.get_json()
        assert data['success'] is True
        funnel = {f['stage']: f['count'] for f in data['funnel']}
        assert funnel['contacted'] == 1
        assert len(funnel) == len(models.PIPELINE_STAGES)

    def test_activity_with_limit(self, client, dash_pro, dash_leads):
        user_id = _login_as_pro(client, dash_pro)
        models.move_lead_stage(user_id, dash_leads[0], 'contacted')
        resp = client.get('/api/dashboard/activity?limit=5')
        data = resp.get_json()
        assert data['success'] is True
        assert len(data['activity']) <= 5
        kinds = {e['kind'] for e in data['activity']}
        assert 'stage_move' in kinds or 'contacted' in kinds

    def test_empty_dashboard_returns_zeros(self, client, db):
        unique = uuid.uuid4().hex[:8]
        pro_name = f'Empty {unique}'
        cursor = db.execute(
            'INSERT INTO users (username, email, hash, role, phone, phone_e164, is_active) VALUES (?, ?, ?, ?, ?, ?, ?)',
            (pro_name, f'empty_{unique}@test.com', generate_password_hash('pass'), 'professional', '+5491198765432', '+5491198765432', 1)
        )
        db.commit()
        user_id = cursor.lastrowid
        db.execute(
            'INSERT INTO professionals (user_id, name, license, specialty, status, province, zone) VALUES (?, ?, ?, ?, ?, ?, ?)',
            (user_id, pro_name, f'LIC-{unique}', 'general', 'approved', 'Tierra del Fuego', f'ZonaVacia{unique}')
        )
        db.commit()
        with client.session_transaction() as sess:
            sess['user_id'] = user_id
            sess['username'] = pro_name
            sess['role'] = 'professional'
        data = client.get('/api/dashboard/summary').get_json()
        assert data['success'] is True
        assert data['summary']['total_leads'] == 0
        assert data['summary']['contact_rate'] == 0.0
        trends = client.get('/api/dashboard/trends?days=7').get_json()
        assert sum(p['count'] for p in trends['trends']) == 0

    def test_top_metrics(self, client, dash_pro, dash_leads):
        _login_as_pro(client, dash_pro)
        resp = client.get('/api/dashboard/top-metrics?my_leads=0')
        data = resp.get_json()
        assert data['success'] is True
        assert data['top_zones'][0]['label'] == 'Palermo'
        assert data['top_zones'][0]['value'] >= 2
        assert any(p['label'] == 'departamento' for p in data['top_property_types'])

    def test_funnel_respects_my_leads(self, client, db, dash_pro, dash_leads):
        user_id = _login_as_pro(client, dash_pro)
        models.move_lead_stage(user_id, dash_leads[0], 'contacted')
        resp_all = client.get('/api/dashboard/pipeline?my_leads=0')
        assert resp_all.get_json()['success'] is True
        funnel_all = {f['stage']: f['count'] for f in resp_all.get_json()['funnel']}
        assert funnel_all['contacted'] >= 1
        resp = client.get('/api/dashboard/pipeline?my_leads=1')
        assert resp.get_json()['success'] is True

    def test_non_professional_blocked(self, client, auth_client):
        resp = client.get('/api/dashboard/summary')
        assert resp.status_code in (302, 403)
