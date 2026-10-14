import uuid
import pytest
from werkzeug.security import generate_password_hash

import models


@pytest.fixture
def cal_pro(db):
    unique = uuid.uuid4().hex[:8]
    pro_name = f'Cal Pro {unique}'
    cursor = db.execute(
        'INSERT INTO users (username, email, hash, role, phone, phone_e164, is_active) VALUES (?, ?, ?, ?, ?, ?, ?)',
        (pro_name, f'cal_{unique}@test.com', generate_password_hash('pass'), 'professional', '+5491198765432', '+5491198765432', 1)
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
def cal_lead(db):
    unique = uuid.uuid4().hex[:8]
    cursor = db.execute(
        '''INSERT INTO leads (type, property_type, zone, province, budget, currency, phone, email, user_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
        ('comprar', 'casa', 'Palermo', 'Buenos Aires', '300000', 'USD', f'+54911223{unique[:4]}', f'cal_{unique}@test.com', 1)
    )
    db.commit()
    return cursor.lastrowid


def _login_as_pro(client, cal_pro):
    user_id, pro_name = cal_pro
    with client.session_transaction() as sess:
        sess['user_id'] = user_id
        sess['username'] = pro_name
        sess['role'] = 'professional'
    return user_id


VALID_EVENT = {'title': 'Visita depto', 'date': '2026-11-15', 'start_time': '10:00', 'end_time': '11:00', 'type': 'visit'}


class TestCalendar:
    def test_create_event(self, client, cal_pro):
        _login_as_pro(client, cal_pro)
        resp = client.post('/api/calendar/events', json=dict(VALID_EVENT))
        data = resp.get_json()
        assert resp.status_code == 200
        assert data['success'] is True
        assert data['id']

    def test_create_without_title_400(self, client, cal_pro):
        _login_as_pro(client, cal_pro)
        payload = dict(VALID_EVENT)
        payload.pop('title')
        resp = client.post('/api/calendar/events', json=payload)
        assert resp.status_code == 400
        assert resp.get_json()['success'] is False

    def test_list_by_month(self, client, cal_pro):
        _login_as_pro(client, cal_pro)
        client.post('/api/calendar/events', json=dict(VALID_EVENT))
        client.post('/api/calendar/events', json={'title': 'Otro', 'date': '2026-12-01', 'type': 'call'})
        resp = client.get('/api/calendar/events?month=2026-11')
        data = resp.get_json()
        assert data['success'] is True
        assert len(data['events']) == 1
        assert data['events'][0]['title'] == 'Visita depto'

    def test_update_event(self, client, cal_pro):
        _login_as_pro(client, cal_pro)
        eid = client.post('/api/calendar/events', json=dict(VALID_EVENT)).get_json()['id']
        resp = client.put(f'/api/calendar/events/{eid}', json={'title': 'Visita actualizada'})
        assert resp.get_json()['success'] is True
        resp = client.get('/api/calendar/events?month=2026-11')
        assert resp.get_json()['events'][0]['title'] == 'Visita actualizada'

    def test_delete_event(self, client, db, cal_pro):
        user_id = _login_as_pro(client, cal_pro)
        eid = client.post('/api/calendar/events', json=dict(VALID_EVENT)).get_json()['id']
        resp = client.delete(f'/api/calendar/events/{eid}')
        assert resp.get_json()['success'] is True
        assert models.get_calendar_event(user_id, eid) is None

    def test_move_event(self, client, cal_pro):
        _login_as_pro(client, cal_pro)
        eid = client.post('/api/calendar/events', json=dict(VALID_EVENT)).get_json()['id']
        resp = client.post(f'/api/calendar/events/{eid}/move', json={'date': '2026-11-20'})
        assert resp.get_json()['success'] is True
        resp = client.get('/api/calendar/events?month=2026-11')
        assert resp.get_json()['events'][0]['event_date'] == '2026-11-20'

    def test_event_with_lead_link(self, client, cal_pro, cal_lead):
        _login_as_pro(client, cal_pro)
        payload = dict(VALID_EVENT)
        payload['lead_id'] = cal_lead
        resp = client.post('/api/calendar/events', json=payload)
        assert resp.get_json()['success'] is True
        payload['lead_id'] = 999999
        resp = client.post('/api/calendar/events', json=payload)
        assert resp.status_code == 400

    def test_upcoming(self, client, cal_pro):
        from datetime import date, timedelta
        _login_as_pro(client, cal_pro)
        soon = (date.today() + timedelta(days=2)).isoformat()
        client.post('/api/calendar/events', json={'title': 'Pronto', 'date': soon, 'type': 'call'})
        resp = client.get('/api/calendar/events/upcoming?days=7')
        data = resp.get_json()
        assert data['success'] is True
        assert any(e['title'] == 'Pronto' for e in data['events'])

    def test_non_professional_blocked(self, client, auth_client):
        resp = client.get('/api/calendar/events')
        assert resp.status_code in (302, 403)

    def test_end_before_start_rejected(self, client, cal_pro):
        _login_as_pro(client, cal_pro)
        payload = dict(VALID_EVENT)
        payload['start_time'] = '13:50'
        payload['end_time'] = '13:40'
        resp = client.post('/api/calendar/events', json=payload)
        assert resp.status_code == 400
        assert resp.get_json()['success'] is False
