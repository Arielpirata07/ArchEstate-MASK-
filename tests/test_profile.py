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
