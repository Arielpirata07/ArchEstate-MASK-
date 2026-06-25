import uuid
import pytest
from werkzeug.security import generate_password_hash

import models


@pytest.fixture
def pro_user_with_zone(db):
    """Professional user with province and zone set."""
    unique = uuid.uuid4().hex[:8]
    pro_name = f'Pro {unique}'
    cursor = db.execute(
        'INSERT INTO users (username, email, hash, role, phone, phone_e164, is_active) VALUES (?, ?, ?, ?, ?, ?, ?)',
        (pro_name, f'pro_{unique}@test.com', generate_password_hash('pass'), 'professional', '+5491198765432', '+5491198765432', 1)
    )
    db.commit()
    user_id = cursor.lastrowid
    db.execute(
        'INSERT INTO professionals (user_id, name, license, specialty, status, province, zone) VALUES (?, ?, ?, ?, ?, ?, ?)',
        (user_id, pro_name, f'LIC-{unique}', 'arquitectura', 'approved', 'Buenos Aires', 'Palermo')
    )
    db.commit()
    return user_id, pro_name


@pytest.fixture
def pro_user_no_zone(db):
    """Professional user without province/zone set."""
    unique = uuid.uuid4().hex[:8]
    pro_name = f'Pro {unique}'
    cursor = db.execute(
        'INSERT INTO users (username, email, hash, role, phone, phone_e164, is_active) VALUES (?, ?, ?, ?, ?, ?, ?)',
        (pro_name, f'pro_{unique}@test.com', generate_password_hash('pass'), 'professional', '+5491198765432', '+5491198765432', 1)
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
def lead_buenos_aires(db):
    """Lead in Buenos Aires, Palermo."""
    unique = uuid.uuid4().hex[:8]
    cursor = db.execute(
        '''INSERT INTO leads (type, property_type, zone, province, budget, currency, phone, email, user_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
        ('comprar', 'departamento', 'Palermo', 'Buenos Aires', '200000', 'USD', f'+54911123{unique[:4]}', f'lead_{unique}@test.com', 1)
    )
    db.commit()
    return cursor.lastrowid


@pytest.fixture
def lead_caba(db):
    """Lead in CABA, Recoleta."""
    unique = uuid.uuid4().hex[:8]
    cursor = db.execute(
        '''INSERT INTO leads (type, property_type, zone, province, budget, currency, phone, email, user_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
        ('comprar', 'casa', 'Recoleta', 'CABA', '500000', 'USD', f'+54911987{unique[:4]}', f'lead2_{unique}@test.com', 1)
    )
    db.commit()
    return cursor.lastrowid


class TestMyLeadsFilter:
    def test_my_leads_filters_by_province_and_zone(self, client, pro_user_with_zone, lead_buenos_aires, lead_caba):
        """Professional with Buenos Aires/Palermo should only see matching leads."""
        user_id, pro_name = pro_user_with_zone
        with client.session_transaction() as sess:
            sess['user_id'] = user_id
            sess['username'] = pro_name
            sess['role'] = 'professional'

        resp = client.get('/api/leads?my_leads=1')
        data = resp.get_json()
        assert data['success'] is True
        lead_ids = [l['id'] for l in data['leads']]
        assert lead_buenos_aires in lead_ids
        assert lead_caba not in lead_ids

    def test_my_leads_shows_all_when_no_zone_set(self, client, pro_user_no_zone, lead_buenos_aires, lead_caba):
        """Professional without province/zone should see all leads."""
        user_id, pro_name = pro_user_no_zone
        with client.session_transaction() as sess:
            sess['user_id'] = user_id
            sess['username'] = pro_name
            sess['role'] = 'professional'

        resp = client.get('/api/leads?my_leads=1')
        data = resp.get_json()
        assert data['success'] is True
        lead_ids = [l['id'] for l in data['leads']]
        assert lead_buenos_aires in lead_ids
        assert lead_caba in lead_ids

    def test_my_leads_zero_shows_all(self, client, pro_user_with_zone, lead_buenos_aires, lead_caba):
        """my_leads=0 should show all leads regardless of province/zone."""
        user_id, pro_name = pro_user_with_zone
        with client.session_transaction() as sess:
            sess['user_id'] = user_id
            sess['username'] = pro_name
            sess['role'] = 'professional'

        resp = client.get('/api/leads?my_leads=0')
        data = resp.get_json()
        assert data['success'] is True
        lead_ids = [l['id'] for l in data['leads']]
        assert lead_buenos_aires in lead_ids
        assert lead_caba in lead_ids

    def test_my_leads_default_is_one(self, client, pro_user_with_zone, lead_buenos_aires, lead_caba):
        """Default my_leads should be 1 (only my leads)."""
        user_id, pro_name = pro_user_with_zone
        with client.session_transaction() as sess:
            sess['user_id'] = user_id
            sess['username'] = pro_name
            sess['role'] = 'professional'

        resp = client.get('/api/leads')
        data = resp.get_json()
        assert data['success'] is True
        lead_ids = [l['id'] for l in data['leads']]
        assert lead_buenos_aires in lead_ids
        assert lead_caba not in lead_ids

    def test_my_leads_zone_is_partial_match(self, client, db, lead_buenos_aires):
        """Zone filter should be partial (LIKE) match."""
        unique = uuid.uuid4().hex[:8]
        pro_name = f'Pro {unique}'
        cursor = db.execute(
            'INSERT INTO users (username, email, hash, role, phone, phone_e164, is_active) VALUES (?, ?, ?, ?, ?, ?, ?)',
            (pro_name, f'pro_{unique}@test.com', generate_password_hash('pass'), 'professional', '+5491198765432', '+5491198765432', 1)
        )
        db.commit()
        user_id = cursor.lastrowid
        db.execute(
            'INSERT INTO professionals (user_id, name, license, specialty, status, province, zone) VALUES (?, ?, ?, ?, ?, ?, ?)',
            (user_id, pro_name, f'LIC-{unique}', 'arquitectura', 'approved', 'Buenos Aires', 'Palerm')
        )
        db.commit()

        with client.session_transaction() as sess:
            sess['user_id'] = user_id
            sess['username'] = pro_name
            sess['role'] = 'professional'

        resp = client.get('/api/leads?my_leads=1')
        data = resp.get_json()
        assert data['success'] is True
        lead_ids = [l['id'] for l in data['leads']]
        assert lead_buenos_aires in lead_ids


class TestProfessionalZoneUpdate:
    def test_update_professional_zone(self, client, pro_user_with_zone):
        """Professional can update province and zone via API."""
        user_id, pro_name = pro_user_with_zone
        with client.session_transaction() as sess:
            sess['user_id'] = user_id
            sess['username'] = pro_name
            sess['role'] = 'professional'

        resp = client.put('/api/profile/professional', json={
            'province': 'CABA',
            'zone': 'Recoleta'
        })
        data = resp.get_json()
        assert data['status'] == 'success'

        conn = models.get_db_connection()
        pro = conn.execute('SELECT province, zone FROM professionals WHERE user_id = ?', (user_id,)).fetchone()
        conn.close()
        assert pro['province'] == 'CABA'
        assert pro['zone'] == 'Recoleta'

    def test_update_professional_zone_validates_fields(self, client, pro_user_with_zone):
        """Only allowed fields should be updated."""
        user_id, pro_name = pro_user_with_zone
        with client.session_transaction() as sess:
            sess['user_id'] = user_id
            sess['username'] = pro_name
            sess['role'] = 'professional'

        resp = client.put('/api/profile/professional', json={
            'province': 'CABA',
            'license': 'HACKED-123'
        })
        data = resp.get_json()
        assert data['status'] == 'success'

        conn = models.get_db_connection()
        pro = conn.execute('SELECT license, province FROM professionals WHERE user_id = ?', (user_id,)).fetchone()
        conn.close()
        assert pro['province'] == 'CABA'
        assert pro['license'] != 'HACKED-123'
