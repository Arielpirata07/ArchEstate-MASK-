import json
import uuid

from werkzeug.security import generate_password_hash


class TestUserLeadsTracking:

    def _create_professional(self, db, suffix=''):
        """Crea un profesional aprobado y devuelve su user_id."""
        uname = f'pro_{uuid.uuid4().hex[:8]}{suffix}'
        cur = db.execute(
            'INSERT INTO users (username, email, hash, role, phone, phone_e164, phone_format_valid) '
            'VALUES (?, ?, ?, ?, ?, ?, 1)',
            (uname, f'{uname}@example.com', generate_password_hash('pro123'),
             'professional', '+5491111111111', '+5491111111111')
        )
        uid = cur.lastrowid
        db.execute(
            'INSERT INTO professionals (user_id, name, license, specialty, status) VALUES (?, ?, ?, ?, ?)',
            (uid, uname, f'LIC-{uname}', 'General', 'approved')
        )
        db.commit()
        return uid

    def _create_lead(self, db, user_id):
        """Crea un lead asociado al user_id y devuelve su id."""
        lead_id = db.execute(
            'INSERT INTO leads (type, zone, budget, currency, phone, email, user_id, phone_format_valid) '
            'VALUES (?, ?, ?, ?, ?, ?, ?, 1)',
            ('Comprar', 'Palermo', '500000', 'USD', '+5491111111111',
             f'user_{uuid.uuid4().hex[:8]}@test.com', user_id)
        ).lastrowid
        db.commit()
        return lead_id

    def _toggle_tracking(self, db, professional_id, lead_id, status_type, value=1):
        """Helper para insertar/actualizar lead_tracking."""
        tracking = db.execute(
            'SELECT id FROM lead_tracking WHERE professional_id = ? AND lead_id = ?',
            (professional_id, lead_id)
        ).fetchone()
        if tracking:
            db.execute(
                f'UPDATE lead_tracking SET {status_type} = ? WHERE professional_id = ? AND lead_id = ?',
                (value, professional_id, lead_id)
            )
        else:
            seen_val = 1 if status_type == 'seen' else 0
            contacted_val = 1 if status_type == 'contacted' else 0
            db.execute(
                'INSERT INTO lead_tracking (professional_id, lead_id, seen, contacted) VALUES (?, ?, ?, ?)',
                (professional_id, lead_id, seen_val, contacted_val)
            )
        db.commit()

    def test_leads_return_seen_count(self, auth_client, db):
        """seen_count refleja profesionales que marcaron Visto."""
        # Obtener el user_id del cliente logueado
        with auth_client.session_transaction() as sess:
            user_id = sess['user_id']

        lead_id = self._create_lead(db, user_id)
        pro1 = self._create_professional(db, 'a')
        pro2 = self._create_professional(db, 'b')

        self._toggle_tracking(db, pro1, lead_id, 'seen', 1)
        self._toggle_tracking(db, pro2, lead_id, 'seen', 1)

        resp = auth_client.get('/api/profile/leads')
        data = json.loads(resp.data)
        assert data['success'] is True
        leads = data['leads']
        assert len(leads) == 1
        assert leads[0]['seen_count'] == 2

    def test_leads_tracking_zero_when_no_views(self, auth_client, db):
        """Lead sin interacciones de profesionales → seen_count = 0."""
        with auth_client.session_transaction() as sess:
            user_id = sess['user_id']

        lead_id = self._create_lead(db, user_id)
        # No crear tracking entries

        resp = auth_client.get('/api/profile/leads')
        data = json.loads(resp.data)
        assert data['success'] is True
        lead = data['leads'][0]
        assert lead['seen_count'] == 0
        assert lead['contacted_count'] == 0

    def test_leads_tracking_counts_mixed(self, auth_client, db):
        """Mezcla: un profesional vio, otro contactó, otro sin acción."""
        with auth_client.session_transaction() as sess:
            user_id = sess['user_id']

        lead_id = self._create_lead(db, user_id)
        pro1 = self._create_professional(db, 'a')
        pro2 = self._create_professional(db, 'b')
        pro3 = self._create_professional(db, 'c')

        self._toggle_tracking(db, pro1, lead_id, 'seen', 1)
        self._toggle_tracking(db, pro2, lead_id, 'contacted', 1)
        # pro3 no hace nada

        resp = auth_client.get('/api/profile/leads')
        data = json.loads(resp.data)
        assert data['success'] is True
        lead = data['leads'][0]
        assert lead['seen_count'] == 1
        assert lead['contacted_count'] == 1

    def test_leads_tracking_multiple_leads(self, auth_client, db):
        """Múltiples leads con distintos niveles de tracking."""
        with auth_client.session_transaction() as sess:
            user_id = sess['user_id']

        lead1 = self._create_lead(db, user_id)
        lead2 = self._create_lead(db, user_id)
        pro = self._create_professional(db)

        self._toggle_tracking(db, pro, lead1, 'seen', 1)

        resp = auth_client.get('/api/profile/leads')
        data = json.loads(resp.data)
        assert data['success'] is True
        leads = {l['id']: l for l in data['leads']}
        assert leads[lead1]['seen_count'] == 1
        assert leads[lead2]['seen_count'] == 0

    def _make_professional(self, db, user_id):
        """Upgrade auth_client user to professional with approved status."""
        db.execute(
            'UPDATE users SET role = ? WHERE id = ?',
            ('professional', user_id)
        )
        db.execute(
            'INSERT OR IGNORE INTO professionals (user_id, name, license, specialty, status) '
            'VALUES (?, ?, ?, ?, ?)',
            (user_id, 'Test Pro', 'LIC-000', 'General', 'approved')
        )
        db.commit()

    def test_export_xlsx_returns_file(self, auth_client, db):
        """Export XLSX returns a workbook with correct content type."""
        with auth_client.session_transaction() as sess:
            user_id = sess['user_id']
        self._make_professional(db, user_id)

        lead = db.execute(
            'INSERT INTO leads (type, zone, budget, currency, phone, email, user_id, phone_format_valid) '
            'VALUES (?, ?, ?, ?, ?, ?, ?, 1)',
            ('Venta', 'Recoleta', '750000', 'USD', '+5491111111111', 'test@export.com', user_id)
        ).lastrowid
        db.execute(
            'INSERT INTO lead_tracking (professional_id, lead_id, seen, contacted, contacted_at) '
            'VALUES (?, ?, 1, 1, datetime(\'now\', \'-1 days\'))',
            (user_id, lead)
        )
        db.commit()

        resp = auth_client.get('/api/profile/professional/export/xlsx')
        assert resp.status_code == 200
        assert resp.content_type == 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        assert resp.headers['Content-Disposition'].startswith('attachment')
        assert len(resp.data) > 1000

    def test_export_pdf_returns_file(self, auth_client, db):
        """Export PDF returns a document with correct content type."""
        with auth_client.session_transaction() as sess:
            user_id = sess['user_id']
        self._make_professional(db, user_id)

        lead = db.execute(
            'INSERT INTO leads (type, zone, budget, currency, phone, email, user_id, phone_format_valid) '
            'VALUES (?, ?, ?, ?, ?, ?, ?, 1)',
            ('Alquiler', 'Belgrano', '4500', 'USD', '+5491111111112', 'test2@export.com', user_id)
        ).lastrowid
        db.execute(
            'INSERT INTO lead_tracking (professional_id, lead_id, seen, contacted, contacted_at) '
            'VALUES (?, ?, 1, 1, datetime(\'now\', \'-1 days\'))',
            (user_id, lead)
        )
        db.commit()

        resp = auth_client.get('/api/profile/professional/export/pdf')
        assert resp.status_code == 200
        assert resp.content_type == 'application/pdf'
        assert resp.headers['Content-Disposition'].startswith('attachment')
        assert len(resp.data) > 500

    def test_export_requires_professional_role(self, client):
        """Non-professional users get redirected."""
        resp = client.get('/api/profile/professional/export/xlsx')
        assert resp.status_code == 302

    def test_parse_budget_variants(self):
        """parse_budget handles AR and intl formats."""
        from utils import parse_budget
        assert parse_budget('$1,234.56') == 1234.56
        assert parse_budget('$1.234,56') == 1234.56
        assert parse_budget('500000') == 500000.0
        assert parse_budget('') == 0
        assert parse_budget(None) == 0
        assert parse_budget('Consultar') == 0
        assert parse_budget('USD 500,000') == 500000.0

    def test_build_export_stats_empty(self, auth_client):
        """_build_export_stats returns zeros for empty list."""
        from routes_profile import _build_export_stats
        stats = _build_export_stats([])
        assert stats['total'] == 0
        assert stats['avg_budget'] == 0
        assert stats['total_budget'] == 0
        assert stats['zone_count'] == 0
        assert stats['budget_by_currency'] == {}

    def test_build_export_stats_with_data(self):
        """_build_export_stats computes per-currency budgets correctly."""
        from routes_profile import _build_export_stats
        leads = [
            {'budget': '1000', 'zone': 'Palermo', 'currency': 'USD', 'type': 'Venta'},
            {'budget': '2000', 'zone': 'Recoleta', 'currency': 'USD', 'type': 'Venta'},
            {'budget': '3000', 'zone': 'Palermo', 'currency': 'ARS', 'type': 'Alquiler'},
        ]
        stats = _build_export_stats(leads)
        assert stats['total'] == 3
        assert stats['total_budget'] == 6000
        assert stats['zone_count'] == 2
        assert stats['budget_by_currency']['USD']['total'] == 3000
        assert stats['budget_by_currency']['USD']['count'] == 2
        assert stats['budget_by_currency']['ARS']['total'] == 3000
        assert stats['budget_by_currency']['ARS']['count'] == 1


class TestNotificationFiltersAPI:

    def _create_professional_auth_client(self, auth_client, db):
        """Convierte el auth_client en profesional."""
        with auth_client.session_transaction() as sess:
            user_id = sess['user_id']
            sess['role'] = 'professional'
        uid = uuid.uuid4().hex[:8]
        db.execute('UPDATE users SET role = ? WHERE id = ?', ('professional', user_id))
        db.execute(
            'INSERT INTO professionals (user_id, name, license, specialty, status) VALUES (?, ?, ?, ?, ?)',
            (user_id, f'Test Pro {uid}', f'LIC-{uid}', 'arquitectura', 'approved')
        )
        db.execute(
            'INSERT OR IGNORE INTO user_preferences (user_id, lead_alerts) VALUES (?, 1)',
            (user_id,)
        )
        db.commit()
        return auth_client

    def test_get_filters_defaults(self, auth_client, db):
        client = self._create_professional_auth_client(auth_client, db)
        resp = client.get('/api/profile/notification-filters')
        data = resp.get_json()
        assert data['success'] is True
        assert data['filters'] == {}
        assert data['budget_min'] == 0
        assert data['budget_max'] == 0

    def test_update_filters(self, auth_client, db):
        client = self._create_professional_auth_client(auth_client, db)
        resp = client.put('/api/profile/notification-filters',
            json={'types': ['Comprar Propiedad'], 'property_types': ['departamento'], 'budget_min': 100000, 'budget_max': 500000})
        data = resp.get_json()
        assert data['success'] is True
        assert data['filters'] == {'types': ['Comprar Propiedad'], 'property_types': ['departamento']}
        assert data['budget_min'] == 100000
        assert data['budget_max'] == 500000

    def test_update_filters_validates_types(self, auth_client, db):
        client = self._create_professional_auth_client(auth_client, db)
        resp = client.put('/api/profile/notification-filters',
            json={'types': ['invalid_type'], 'property_types': ['invalid_prop']})
        data = resp.get_json()
        assert data['success'] is True
        assert data['filters']['types'] == []
        assert data['filters']['property_types'] == []

    def test_get_filters_after_update(self, auth_client, db):
        client = self._create_professional_auth_client(auth_client, db)
        client.put('/api/profile/notification-filters',
            json={'types': ['Comprar Propiedad'], 'property_types': ['departamento'], 'budget_min': 200000})
        resp = client.get('/api/profile/notification-filters')
        data = resp.get_json()
        assert data['filters'] == {'types': ['Comprar Propiedad'], 'property_types': ['departamento']}
        assert data['budget_min'] == 200000


class TestNotificationChannelAPI:

    def _create_professional_auth_client(self, auth_client, db):
        with auth_client.session_transaction() as sess:
            user_id = sess['user_id']
            sess['role'] = 'professional'
        uid = uuid.uuid4().hex[:8]
        db.execute('UPDATE users SET role = ? WHERE id = ?', ('professional', user_id))
        db.execute(
            'INSERT INTO professionals (user_id, name, license, specialty, status) VALUES (?, ?, ?, ?, ?)',
            (user_id, f'Test Pro {uid}', f'LIC-{uid}', 'arquitectura', 'approved')
        )
        db.execute(
            'INSERT OR IGNORE INTO user_preferences (user_id, lead_alerts) VALUES (?, 1)',
            (user_id,)
        )
        db.commit()
        return auth_client

    def test_get_channel_default(self, auth_client, db):
        client = self._create_professional_auth_client(auth_client, db)
        resp = client.get('/api/profile/notification-channel')
        data = resp.get_json()
        assert data['success'] is True
        assert data['channel'] == 'auto'

    def test_update_channel_valid(self, auth_client, db):
        client = self._create_professional_auth_client(auth_client, db)
        resp = client.put('/api/profile/notification-channel',
            json={'channel': 'whatsapp'})
        data = resp.get_json()
        assert data['success'] is True
        assert data['channel'] == 'whatsapp'

    def test_update_channel_invalid(self, auth_client, db):
        client = self._create_professional_auth_client(auth_client, db)
        resp = client.put('/api/profile/notification-channel',
            json={'channel': 'fax'})
        data = resp.get_json()
        assert data['success'] is False
        assert resp.status_code == 400

    def test_update_channel_persists(self, auth_client, db):
        client = self._create_professional_auth_client(auth_client, db)
        client.put('/api/profile/notification-channel', json={'channel': 'ambos'})
        resp = client.get('/api/profile/notification-channel')
        data = resp.get_json()
        assert data['channel'] == 'ambos'
