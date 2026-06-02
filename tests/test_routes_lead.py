"""
Tests para el blueprint lead_bp:
  - /api/lead/<id>/r/whatsapp  (server-side 302 con UTM)
  - /api/lead/<id>/phone        (reveal con hash en audit)
  - /api/lead/<id>/whatsapp-event (telemetría)
"""

import json
import os
import pytest


def _create_professional_and_lead(db, professional_user, lead_phone='+5491144445555'):
    """Helper: crea un profesional aprobado y un lead con un teléfono dado."""
    import uuid
    from werkzeug.security import generate_password_hash

    uname = f'pro_{uuid.uuid4().hex[:8]}'
    cur = db.execute(
        'INSERT INTO users (username, email, hash, role, phone, phone_e164, phone_format_valid) '
        'VALUES (?, ?, ?, ?, ?, ?, 1)',
        (uname, f'{uname}@example.com', generate_password_hash('pro123'),
         'professional', lead_phone, lead_phone)
    )
    user_id = cur.lastrowid

    db.execute(
        'INSERT INTO professionals (user_id, name, license, specialty, status) VALUES (?, ?, ?, ?, ?)',
        (user_id, uname, f'LIC-{uname}', 'General', 'approved')
    )
    lead_id = db.execute(
        'INSERT INTO leads (type, zone, budget, currency, phone, email, phone_format_valid) '
        'VALUES (?, ?, ?, ?, ?, ?, 1)',
        ('Comprar Propiedad', 'Palermo', '500000', 'USD', lead_phone, f'{uname}@lead.com')
    ).lastrowid
    db.commit()
    return user_id, uname, lead_id


@pytest.fixture
def auth_professional(db, client):
    """Crea un profesional aprobado, lo loguea y devuelve (client, user_id, lead_id)."""
    user_id, username, lead_id = _create_professional_and_lead(db, None)
    with client.session_transaction() as sess:
        sess['user_id'] = user_id
        sess['username'] = username
        sess['role'] = 'professional'
    return client, user_id, lead_id


class TestRedirectWhatsapp:
    def test_redirects_to_wa_me_for_mobile(self, auth_professional):
        client, _, lead_id = auth_professional
        resp = client.get(f'/api/lead/{lead_id}/r/whatsapp', follow_redirects=False)
        assert resp.status_code == 302
        assert resp.headers['Location'].startswith('https://wa.me/5491144445555?text=')
        assert 'utm_source=archestate' in resp.headers['Location']
        assert 'utm_medium=lead' in resp.headers['Location']
        assert f'utm_campaign=lead_{lead_id}' in resp.headers['Location']

    def test_message_contains_operation_and_zone(self, auth_professional):
        client, _, lead_id = auth_professional
        resp = client.get(f'/api/lead/{lead_id}/r/whatsapp', follow_redirects=False)
        from urllib.parse import urlparse, parse_qs
        parsed = urlparse(resp.headers['Location'])
        qs = parse_qs(parsed.query)
        text = qs.get('text', [''])[0]
        assert 'Comprar Propiedad' in text or 'comprar' in text.lower()
        assert 'Palermo' in text
        assert 'ArchEstate' in text

    def test_returns_422_for_landline(self, auth_professional, db):
        client, user_id, _ = auth_professional
        uname = db.execute('SELECT username FROM users WHERE id = ?', (user_id,)).fetchone()['username']
        lead_id = db.execute(
            'INSERT INTO leads (type, zone, budget, currency, phone, email, phone_format_valid) '
            'VALUES (?, ?, ?, ?, ?, ?, 1)',
            ('Comprar Propiedad', 'Palermo', '500000', 'USD',
             '+541144444555',  # fijo AR
             f'{uname}2@lead.com')
        ).lastrowid
        db.commit()

        resp = client.get(f'/api/lead/{lead_id}/r/whatsapp', follow_redirects=False)
        assert resp.status_code == 422
        data = resp.get_json()
        assert 'celular' in data['error'].lower() or 'whatsapp' in data['error'].lower()

    def test_returns_404_for_missing_lead(self, auth_professional):
        client, _, _ = auth_professional
        resp = client.get('/api/lead/99999/r/whatsapp', follow_redirects=False)
        assert resp.status_code == 404

    def test_requires_professional_role(self, auth_client, db):
        # auth_client es client, no professional
        resp = auth_client.get('/api/lead/1/r/whatsapp', follow_redirects=False)
        assert resp.status_code in (302, 403)

    def test_logs_audit_with_hash(self, auth_professional, db):
        client, _, lead_id = auth_professional
        client.get(f'/api/lead/{lead_id}/r/whatsapp', follow_redirects=False)
        row = db.execute("SELECT * FROM audit_log WHERE action = 'WhatsApp link generated' ORDER BY id DESC LIMIT 1").fetchone()
        assert row is not None
        assert 'phone_hash=' in row['target']
        assert '54911' not in row['target']  # NO debe aparecer el número completo

    def test_logs_event(self, auth_professional, db):
        client, _, lead_id = auth_professional
        client.get(f'/api/lead/{lead_id}/r/whatsapp', follow_redirects=False)
        row = db.execute("SELECT * FROM events WHERE event = 'wa_link_generated' ORDER BY id DESC LIMIT 1").fetchone()
        assert row is not None
        assert row['lead_id'] == lead_id


class TestRevealPhone:
    def test_returns_phone(self, auth_professional):
        client, _, lead_id = auth_professional
        resp = client.get(f'/api/lead/{lead_id}/phone')
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['status'] == 'success'
        assert data['phone'] == '+5491144445555'

    def test_audit_log_uses_hash(self, auth_professional, db):
        client, _, lead_id = auth_professional
        client.get(f'/api/lead/{lead_id}/phone')
        row = db.execute("SELECT * FROM audit_log WHERE action = 'Consulta Telefono' ORDER BY id DESC LIMIT 1").fetchone()
        assert row is not None
        assert 'phone_hash=' in row['target']

    def test_emits_event(self, auth_professional, db):
        client, _, lead_id = auth_professional
        client.get(f'/api/lead/{lead_id}/phone')
        row = db.execute("SELECT * FROM events WHERE event = 'phone_revealed' ORDER BY id DESC LIMIT 1").fetchone()
        assert row is not None

    def test_returns_404_for_missing_lead(self, auth_professional):
        client, _, _ = auth_professional
        resp = client.get('/api/lead/99999/phone')
        assert resp.status_code == 404


class TestWhatsappEvent:
    def test_records_click(self, auth_professional, db):
        client, _, lead_id = auth_professional
        resp = client.post(f'/api/lead/{lead_id}/whatsapp-event',
                           data=json.dumps({'event': 'wa_button_clicked', 'props': {'source': 'table'}}),
                           content_type='application/json')
        assert resp.status_code == 200
        row = db.execute("SELECT * FROM events WHERE event = 'wa_button_clicked' ORDER BY id DESC LIMIT 1").fetchone()
        assert row is not None
        assert row['lead_id'] == lead_id

    def test_records_popup_blocked(self, auth_professional, db):
        client, _, lead_id = auth_professional
        resp = client.post(f'/api/lead/{lead_id}/whatsapp-event',
                           data=json.dumps({'event': 'wa_popup_blocked', 'props': {}}),
                           content_type='application/json')
        assert resp.status_code == 200
        row = db.execute("SELECT * FROM events WHERE event = 'wa_popup_blocked' ORDER BY id DESC LIMIT 1").fetchone()
        assert row is not None

    def test_records_sms_fallback(self, auth_professional, db):
        client, _, lead_id = auth_professional
        resp = client.post(f'/api/lead/{lead_id}/whatsapp-event',
                           data=json.dumps({'event': 'sms_fallback_used', 'props': {}}),
                           content_type='application/json')
        assert resp.status_code == 200

    def test_rejects_unknown_event(self, auth_professional):
        client, _, lead_id = auth_professional
        resp = client.post(f'/api/lead/{lead_id}/whatsapp-event',
                           data=json.dumps({'event': 'malicious_event', 'props': {}}),
                           content_type='application/json')
        assert resp.status_code == 400

    def test_requires_auth(self, client):
        resp = client.post('/api/lead/1/whatsapp-event',
                           data=json.dumps({'event': 'wa_button_clicked', 'props': {}}),
                           content_type='application/json')
        assert resp.status_code in (302, 403)


class TestReportLead:
    def test_report_lead_does_not_log_full_phone(self, auth_professional, db):
        """Fase 1: el audit_log NO debe contener el teléfono completo, sólo el hash."""
        from utils import hash_phone_digits
        client, _, lead_id = auth_professional
        resp = client.post(f'/api/lead/{lead_id}/report',
                           data=json.dumps({'notes': 'no contesta'}),
                           content_type='application/json')
        assert resp.status_code == 200
        row = db.execute(
            "SELECT * FROM audit_log WHERE action = 'Reporte de Lead' ORDER BY id DESC LIMIT 1"
        ).fetchone()
        assert row is not None
        target = row['target']
        assert '+5491144445555' not in target, f"El audit log filtró el teléfono: {target}"
        assert '445555' not in target, f"El audit log filtró los últimos 6 dígitos: {target}"
        expected_hash = hash_phone_digits('+5491144445555')
        assert f'phone_hash={expected_hash}' in target

    def test_report_lead_creates_report_record(self, auth_professional, db):
        client, _, lead_id = auth_professional
        resp = client.post(f'/api/lead/{lead_id}/report',
                           data=json.dumps({'notes': 'fuera de servicio'}),
                           content_type='application/json')
        assert resp.status_code == 200
        row = db.execute(
            'SELECT * FROM lead_reports WHERE lead_id = ?', (lead_id,)
        ).fetchone()
        assert row is not None
        assert row['reason'] == 'telefono_inexistente'
        assert row['status'] == 'pending'

    def test_report_lead_duplicate_rejected(self, auth_professional, db):
        client, _, lead_id = auth_professional
        client.post(f'/api/lead/{lead_id}/report',
                    data=json.dumps({'notes': 'primera vez'}),
                    content_type='application/json')
        resp = client.post(f'/api/lead/{lead_id}/report',
                           data=json.dumps({'notes': 'segunda vez'}),
                           content_type='application/json')
        assert resp.status_code == 400
        assert 'anteriormente' in resp.get_json()['error'].lower()
