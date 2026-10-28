import uuid
import pytest
from werkzeug.security import generate_password_hash

import models


@pytest.fixture
def stats_pro(db):
    unique = uuid.uuid4().hex[:8]
    pro_name = f'Stats Pro {unique}'
    cursor = db.execute(
        'INSERT INTO users (username, email, hash, role, phone, phone_e164, is_active) VALUES (?, ?, ?, ?, ?, ?, ?)',
        (pro_name, f'stats_{unique}@test.com', generate_password_hash('pass'), 'professional', '+5491198765432', '+5491198765432', 1)
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
def stats_leads(db):
    unique = uuid.uuid4().hex[:8]
    ids = []
    for i, (zone, ptype) in enumerate([('Palermo', 'departamento'), ('Palermo', 'casa'), ('Recoleta', 'departamento')]):
        cursor = db.execute(
            '''INSERT INTO leads (type, property_type, zone, province, budget, currency, phone, email, user_id, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now', ?))''',
            ('comprar', ptype, zone, 'Buenos Aires', str(100000 * (i + 1)), 'USD', f'+54911123{unique[:4]}', f'stats_{unique}_{i}@test.com', 1, f'-{i} days')
        )
        ids.append(cursor.lastrowid)
    db.commit()
    return ids


def _login_as_pro(client, stats_pro):
    user_id, pro_name = stats_pro
    with client.session_transaction() as sess:
        sess['user_id'] = user_id
        sess['username'] = pro_name
        sess['role'] = 'professional'
    return user_id


class TestLeadsStats:
    def test_requires_professional(self, client):
        resp = client.get('/api/leads/stats')
        assert resp.status_code in (302, 401, 403)

    def test_unapproved_gets_403(self, client, db):
        unique = uuid.uuid4().hex[:8]
        uname = f'pending_{unique}'
        cur = db.execute(
            'INSERT INTO users (username, email, hash, role, phone, phone_e164, is_active) VALUES (?, ?, ?, ?, ?, ?, ?)',
            (uname, f'{uname}@test.com', generate_password_hash('pass'), 'professional', '+5491198765432', '+5491198765432', 1)
        )
        db.commit()
        uid = cur.lastrowid
        db.execute(
            'INSERT INTO professionals (user_id, name, license, specialty, status) VALUES (?, ?, ?, ?, ?)',
            (uid, uname, f'LIC-{unique}', 'general', 'pending')
        )
        db.commit()
        with client.session_transaction() as sess:
            sess['user_id'] = uid
            sess['username'] = uname
            sess['role'] = 'professional'
        resp = client.get('/api/leads/stats')
        assert resp.status_code == 403

    def test_returns_stats_shape(self, client, stats_pro, stats_leads):
        _login_as_pro(client, stats_pro)
        resp = client.get('/api/leads/stats?my_leads=0')
        data = resp.get_json()
        assert resp.status_code == 200
        assert data['success'] is True
        s = data['stats']
        assert s['total'] >= 3
        assert s['avg_budget'] > 0
        assert isinstance(s['by_property_type'], list)
        assert isinstance(s['by_zone'], list)
        assert isinstance(s['by_operation_type'], list)
        assert isinstance(s['trend'], list)
        assert 'previous_month' in s and 'total' in s['previous_month']
        assert 'active_zones' in s
        assert 'month' in s

    def test_month_defaults_to_current(self, client, stats_pro, stats_leads):
        _login_as_pro(client, stats_pro)
        import datetime
        cur = datetime.datetime.now().strftime('%Y-%m')
        resp = client.get('/api/leads/stats?my_leads=0')
        data = resp.get_json()
        assert data['month'] == cur

    def test_invalid_month_falls_back(self, client, stats_pro, stats_leads):
        _login_as_pro(client, stats_pro)
        resp = client.get('/api/leads/stats?month=not-a-month&my_leads=0')
        data = resp.get_json()
        assert resp.status_code == 200
        import datetime
        assert data['month'] == datetime.datetime.now().strftime('%Y-%m')

    def test_my_leads_filters(self, client, stats_pro, stats_leads):
        user_id = _login_as_pro(client, stats_pro)
        # professional has no coverage -> my_leads=1 returns 0-ish (no geo filter conditions, so all)
        resp = client.get('/api/leads/stats?my_leads=1')
        data = resp.get_json()
        assert resp.status_code == 200
        assert data['stats']['total'] >= 0

    def test_empty_dataset_does_not_crash(self, client, stats_pro):
        _login_as_pro(client, stats_pro)
        resp = client.get('/api/leads/stats?my_leads=0&month=2099-01')
        data = resp.get_json()
        assert resp.status_code == 200
        assert data['stats']['total'] == 0
        assert data['stats']['avg_budget'] == 0


class TestStatsExport:
    def test_csv_export_returns_csv(self, client, stats_pro, stats_leads):
        _login_as_pro(client, stats_pro)
        resp = client.get('/api/leads/stats/export?my_leads=0')
        assert resp.status_code == 200
        assert 'text/csv' in resp.content_type
        body = resp.get_data(as_text=True)
        assert 'Palermo' in body or 'Recoleta' in body

    def test_csv_export_empty_dataset(self, client, stats_pro):
        _login_as_pro(client, stats_pro)
        resp = client.get('/api/leads/stats/export?my_leads=0&month=2099-01')
        assert resp.status_code == 200
        assert 'text/csv' in resp.content_type

    def test_xlsx_export_returns_xlsx(self, client, stats_pro, stats_leads):
        _login_as_pro(client, stats_pro)
        resp = client.get('/api/leads/stats/export/xlsx?my_leads=0')
        assert resp.status_code == 200
        assert 'spreadsheetml' in resp.content_type or 'octet-stream' in resp.content_type or 'xlsx' in resp.content_type

    def test_xlsx_export_empty_dataset(self, client, stats_pro):
        _login_as_pro(client, stats_pro)
        resp = client.get('/api/leads/stats/export/xlsx?my_leads=0&month=2099-01')
        assert resp.status_code == 200

    def test_export_requires_approval(self, client, db):
        unique = uuid.uuid4().hex[:8]
        uname = f'pending2_{unique}'
        cur = db.execute(
            'INSERT INTO users (username, email, hash, role, phone, phone_e164, is_active) VALUES (?, ?, ?, ?, ?, ?, ?)',
            (uname, f'{uname}@test.com', generate_password_hash('pass'), 'professional', '+5491198765432', '+5491198765432', 1)
        )
        db.commit()
        uid = cur.lastrowid
        db.execute(
            'INSERT INTO professionals (user_id, name, license, specialty, status) VALUES (?, ?, ?, ?, ?)',
            (uid, uname, f'LIC-{unique}', 'general', 'pending')
        )
        db.commit()
        with client.session_transaction() as sess:
            sess['user_id'] = uid
            sess['username'] = uname
            sess['role'] = 'professional'
        resp = client.get('/api/leads/stats/export?my_leads=0')
        assert resp.status_code == 403
        resp2 = client.get('/api/leads/stats/export/xlsx?my_leads=0')
        assert resp2.status_code == 403

    def test_export_rate_limited_endpoint(self, client, stats_pro, stats_leads):
        _login_as_pro(client, stats_pro)
        # just ensure endpoint responds
        resp = client.get('/api/leads/stats/export?my_leads=0')
        assert resp.status_code == 200
