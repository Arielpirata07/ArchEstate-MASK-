"""Tests de idempotencia y concurrencia (paquete crítico).

Cubre: doble submit con misma key, assign atómico, dedup de
notify_lead_created, reporte único ante carrera, pipeline no-op.
"""
import threading
import uuid

import pytest
from werkzeug.security import generate_password_hash

import models


@pytest.fixture(autouse=True)
def _no_notify_threads(monkeypatch):
    """Los POST /api/submit lanzan notify_lead_created en un hilo daemon
    con SMTP real: en tests se neutraliza para no bloquear la DB temporal
    compartida ni la red (la notificación se cubre en TestNotifyDedup)."""
    class _NoopThread:
        def __init__(self, *a, **k):
            pass

        def start(self):
            pass

    monkeypatch.setattr(threading, 'Thread', _NoopThread)


def _make_user(db, role='client', **kw):
    unique = uuid.uuid4().hex[:8]
    username = kw.pop('username', f'conc_{role}_{unique}')
    cur = db.execute(
        'INSERT INTO users (username, email, hash, role, phone, phone_e164, is_active)'
        ' VALUES (?, ?, ?, ?, ?, ?, 1)',
        (username, f'{unique}@test.com', generate_password_hash('pass'),
         role, '+5491112345678', '+5491112345678')
    )
    db.commit()
    return cur.lastrowid, username


def _make_pro(db, status='approved'):
    user_id, name = _make_user(db, 'professional')
    unique = uuid.uuid4().hex[:8]
    db.execute(
        'INSERT INTO professionals (user_id, name, license, specialty, status)'
        ' VALUES (?, ?, ?, ?, ?)',
        (user_id, name, f'LIC-{unique}', 'general', status)
    )
    db.commit()
    return user_id, name


def _login(client, user_id, username, role):
    with client.session_transaction() as sess:
        sess['user_id'] = user_id
        sess['username'] = username
        sess['role'] = role


LEAD_PAYLOAD = {
    'type': 'Comprar Propiedad',
    'property_type': 'departamento',
    'zone': 'Palermo',
    'province': 'Buenos Aires',
    'country': 'Argentina',
    'budget': '200000',
    'currency': 'USD',
    'phone': '+54 9 11 1234 5678',
}


class TestSubmitIdempotency:
    def _payload(self, key=None):
        data = dict(LEAD_PAYLOAD)
        if key:
            data['idempotency_key'] = key
        return data

    def test_same_key_twice_creates_one_lead(self, client, db):
        user_id, username = _make_user(db)
        _login(client, user_id, username, 'client')
        with client.session_transaction() as sess:
            sess['email'] = f'{username}@test.com'
        key = uuid.uuid4().hex
        r1 = client.post('/api/submit', json=self._payload(key))
        r2 = client.post('/api/submit', json=self._payload(key))
        assert r1.status_code == 200
        assert r2.status_code == 200
        assert r2.get_json().get('deduplicated') is True
        n = db.execute('SELECT COUNT(*) AS n FROM leads WHERE user_id = ?', (user_id,)).fetchone()['n']
        assert n == 1

    def test_same_key_header_twice_creates_one_lead(self, client, db):
        user_id, username = _make_user(db)
        _login(client, user_id, username, 'client')
        with client.session_transaction() as sess:
            sess['email'] = f'{username}@test.com'
        key = uuid.uuid4().hex
        r1 = client.post('/api/submit', json=self._payload(), headers={'X-Idempotency-Key': key})
        r2 = client.post('/api/submit', json=self._payload(), headers={'X-Idempotency-Key': key})
        assert r1.status_code == 200 and r2.status_code == 200
        n = db.execute('SELECT COUNT(*) AS n FROM leads WHERE user_id = ?', (user_id,)).fetchone()['n']
        assert n == 1

    def test_different_keys_create_two_leads(self, client, db):
        user_id, username = _make_user(db)
        _login(client, user_id, username, 'client')
        with client.session_transaction() as sess:
            sess['email'] = f'{username}@test.com'
        client.post('/api/submit', json=self._payload(uuid.uuid4().hex))
        client.post('/api/submit', json=self._payload(uuid.uuid4().hex))
        n = db.execute('SELECT COUNT(*) AS n FROM leads WHERE user_id = ?', (user_id,)).fetchone()['n']
        assert n == 2


class TestNotifyDedup:
    def test_notify_twice_inserts_once(self, client, db):
        _make_pro(db)
        cur = db.execute(
            '''INSERT INTO leads (type, property_type, zone, province, budget, currency, phone, email, user_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
            ('comprar', 'departamento', 'Palermo', 'Buenos Aires', '200000', 'USD',
             '+5491112345678', 'cli@test.com', 1)
        )
        db.commit()
        lead_id = cur.lastrowid
        from services.notifications import notify_lead_created
        notify_lead_created(lead_id)
        first = db.execute(
            "SELECT COUNT(*) AS n FROM notifications WHERE lead_id = ? AND type IN ('lead_new','lead_assigned')",
            (lead_id,)
        ).fetchone()['n']
        notify_lead_created(lead_id)
        second = db.execute(
            "SELECT COUNT(*) AS n FROM notifications WHERE lead_id = ? AND type IN ('lead_new','lead_assigned')",
            (lead_id,)
        ).fetchone()['n']
        assert first >= 1
        assert second == first


class TestAssignAtomic:
    def test_double_assign_same_winner(self, db):
        from services.assignment import auto_assign_lead
        _make_pro(db)
        cur = db.execute(
            '''INSERT INTO leads (type, property_type, zone, province, budget, currency, phone, email, user_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
            ('comprar', 'departamento', 'Palermo', 'Buenos Aires', '200000', 'USD',
             '+5491112345678', 'cli2@test.com', 1)
        )
        db.commit()
        lead_id = cur.lastrowid
        first = auto_assign_lead(lead_id)
        second = auto_assign_lead(lead_id)
        assert first == second


class TestReportRace:
    def test_second_report_returns_400(self, client, db):
        user_id, name = _make_pro(db)
        _login(client, user_id, name, 'professional')
        cur = db.execute(
            '''INSERT INTO leads (type, property_type, zone, province, budget, currency, phone, email, user_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
            ('comprar', 'departamento', 'Palermo', 'Buenos Aires', '200000', 'USD',
             '+5491112345678', 'cli3@test.com', 1)
        )
        db.commit()
        lead_id = cur.lastrowid
        r1 = client.post(f'/api/lead/{lead_id}/report', json={'notes': 'x'})
        r2 = client.post(f'/api/lead/{lead_id}/report', json={'notes': 'x'})
        assert r1.status_code == 200
        assert r2.status_code == 400

    def test_unique_index_blocks_direct_duplicate(self, db):
        user_id, _ = _make_pro(db)
        cur = db.execute(
            '''INSERT INTO leads (type, property_type, zone, province, budget, currency, phone, email, user_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
            ('comprar', 'departamento', 'Palermo', 'Buenos Aires', '200000', 'USD',
             '+5491112345678', 'cli4@test.com', 1)
        )
        db.commit()
        lead_id = cur.lastrowid
        db.execute(
            'INSERT INTO lead_reports (lead_id, reported_by, reason, status) VALUES (?, ?, ?, ?)',
            (lead_id, user_id, 'telefono_inexistente', 'pending')
        )
        db.commit()
        with pytest.raises(Exception):
            db.execute(
                'INSERT INTO lead_reports (lead_id, reported_by, reason, status) VALUES (?, ?, ?, ?)',
                (lead_id, user_id, 'telefono_inexistente', 'pending')
            )


class TestPipelineNoop:
    def test_same_stage_move_writes_no_history(self, client, db):
        user_id, name = _make_pro(db)
        _login(client, user_id, name, 'professional')
        cur = db.execute(
            '''INSERT INTO leads (type, property_type, zone, province, budget, currency, phone, email, user_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
            ('comprar', 'departamento', 'Palermo', 'Buenos Aires', '200000', 'USD',
             '+5491112345678', 'cli5@test.com', 1)
        )
        db.commit()
        lead_id = cur.lastrowid
        client.post(f'/api/pipeline/lead/{lead_id}/move', json={'stage': 'contacted'})
        client.post(f'/api/pipeline/lead/{lead_id}/move', json={'stage': 'contacted'})
        rows = db.execute(
            'SELECT COUNT(*) AS n FROM lead_stage_history WHERE professional_id = ? AND lead_id = ?',
            (user_id, lead_id)
        ).fetchone()['n']
        assert rows == 1


def _make_lead(db, email='cb@test.com'):
    cur = db.execute(
        '''INSERT INTO leads (type, property_type, zone, province, budget, currency, phone, email, user_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
        ('comprar', 'departamento', 'Palermo', 'Buenos Aires', '200000', 'USD',
         '+5491112345678', email, 1)
    )
    db.commit()
    return cur.lastrowid


def _make_admin(db):
    user_id, username = _make_user(db, 'admin')
    return user_id, username


class TestToggleAtomic:
    def test_double_toggle_flips_twice(self, client, db):
        user_id, name = _make_pro(db)
        _login(client, user_id, name, 'professional')
        lead_id = _make_lead(db)
        r1 = client.post(f'/api/lead/{lead_id}/toggle-status', json={'status': 'seen'})
        r2 = client.post(f'/api/lead/{lead_id}/toggle-status', json={'status': 'seen'})
        assert r1.get_json()['value'] == 1
        assert r2.get_json()['value'] == 0
        row = db.execute(
            'SELECT seen FROM lead_tracking WHERE professional_id = ? AND lead_id = ?',
            (user_id, lead_id)
        ).fetchone()
        assert row['seen'] == 0


class TestBulkMoveAtomic:
    def test_bulk_move_skips_missing_in_one_txn(self, client, db):
        user_id, name = _make_pro(db)
        _login(client, user_id, name, 'professional')
        ids = [_make_lead(db, email=f'bulk{i}@test.com') for i in range(2)]
        resp = client.post('/api/pipeline/leads/bulk-move', json={'ids': ids + [999999], 'stage': 'visit'})
        data = resp.get_json()
        assert resp.status_code == 200
        assert data['moved'] == 2
        n = db.execute(
            'SELECT COUNT(*) AS n FROM lead_stages WHERE professional_id = ? AND stage = ?',
            (user_id, 'visit')
        ).fetchone()['n']
        assert n == 2


class TestRestoreReportConflict:
    def test_restore_with_existing_pending_returns_400(self, client, db):
        pro_id, _ = _make_pro(db)
        admin_id, admin_name = _make_admin(db)
        _login(client, admin_id, admin_name, 'admin')
        lead_id = _make_lead(db)
        db.execute(
            'INSERT INTO lead_reports (lead_id, reported_by, reason, status) VALUES (?, ?, ?, ?)',
            (lead_id, pro_id, 'telefono_inexistente', 'pending')
        )
        cur = db.execute(
            'INSERT INTO lead_reports (lead_id, reported_by, reason, status) VALUES (?, ?, ?, ?)',
            (lead_id, pro_id, 'telefono_inexistente', 'dismissed')
        )
        db.commit()
        dismissed_id = cur.lastrowid
        resp = client.post(f'/api/admin/report/{dismissed_id}/restore')
        assert resp.status_code == 400


class TestIdempotencyPrune:
    def test_stale_null_placeholders_pruned_on_submit(self, client, db):
        user_id, username = _make_user(db)
        _login(client, user_id, username, 'client')
        with client.session_transaction() as sess:
            sess['email'] = f'{username}@test.com'
        db.execute(
            "INSERT INTO idempotency_keys (key, user_id, lead_id, created_at)"
            " VALUES (?, ?, NULL, datetime('now', '-2 hours'))",
            ('stale-key', user_id)
        )
        db.commit()
        payload = dict(LEAD_PAYLOAD)
        payload['idempotency_key'] = uuid.uuid4().hex
        resp = client.post('/api/submit', json=payload)
        assert resp.status_code == 200
        gone = db.execute(
            'SELECT COUNT(*) AS n FROM idempotency_keys WHERE key = ?', ('stale-key',)
        ).fetchone()['n']
        assert gone == 0
