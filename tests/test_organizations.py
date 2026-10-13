import uuid
import pytest
from werkzeug.security import generate_password_hash

import models


@pytest.fixture
def admin_client(client):
    from models import get_db_connection
    conn = get_db_connection()
    conn.execute("UPDATE users SET role = 'admin', is_active = 1 WHERE username = 'admin'")
    conn.commit()
    conn.close()
    with client.session_transaction() as sess:
        sess['user_id'] = 1
        sess['username'] = 'admin'
        sess['role'] = 'admin'
    return client


@pytest.fixture
def sample_org(db):
    org_id = models.create_organization('Inmobiliaria Sur', 'Organización de prueba')
    return org_id


@pytest.fixture
def sample_professional(db):
    unique = uuid.uuid4().hex[:8]
    pro_name = f'Pro {unique}'
    cursor = db.execute(
        'INSERT INTO users (username, email, hash, role, phone, phone_e164, is_active) VALUES (?, ?, ?, ?, ?, ?, ?)',
        (pro_name, f'pro_{unique}@test.com', generate_password_hash('pass'), 'professional', '+5491198765432', '+5491198765432', 1)
    )
    user_id = cursor.lastrowid
    db.execute(
        'INSERT INTO professionals (user_id, name, license, specialty, status) VALUES (?, ?, ?, ?, ?)',
        (user_id, pro_name, f'LIC-{unique}', 'arquitectura', 'approved')
    )
    db.commit()
    return user_id, pro_name


@pytest.fixture
def sample_lead(db):
    unique = uuid.uuid4().hex[:8]
    cursor = db.execute(
        '''INSERT INTO leads (type, property_type, zone, province, budget, currency, phone, email, user_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
        ('comprar', 'departamento', 'Palermo', 'Buenos Aires', '200000', 'USD', f'+54911123{unique[:4]}', f'lead_{unique}@test.com', 1)
    )
    db.commit()
    return cursor.lastrowid


class TestOrganizationCRUD:
    def test_create_organization(self, admin_client):
        resp = admin_client.post('/api/admin/organizations', json={
            'name': 'Nueva Org',
            'description': 'Descripción test'
        })
        data = resp.get_json()
        assert data['success'] is True
        assert 'id' in data

    def test_create_organization_requires_name(self, admin_client):
        resp = admin_client.post('/api/admin/organizations', json={
            'name': '',
            'description': 'test'
        })
        data = resp.get_json()
        assert data['success'] is False
        assert resp.status_code == 400

    def test_list_organizations(self, admin_client, sample_org):
        resp = admin_client.get('/api/admin/organizations')
        data = resp.get_json()
        assert data['success'] is True
        assert len(data['organizations']) >= 1

    def test_update_organization(self, admin_client, sample_org):
        resp = admin_client.put(f'/api/admin/organizations/{sample_org}', json={
            'name': 'Org Actualizada',
            'description': 'Nueva descripción'
        })
        data = resp.get_json()
        assert data['success'] is True
        org = models.get_organization_by_id(sample_org)
        assert org['name'] == 'Org Actualizada'

    def test_deactivate_organization(self, admin_client, sample_org):
        resp = admin_client.post(f'/api/admin/organizations/{sample_org}/deactivate')
        data = resp.get_json()
        assert data['success'] is True
        org = models.get_organization_by_id(sample_org)
        assert org['is_active'] == 0

    def test_deactivate_unassigns_professionals(self, admin_client, sample_org, sample_professional):
        user_id, _ = sample_professional
        models.set_professional_organization(user_id, sample_org)
        resp = admin_client.post(f'/api/admin/organizations/{sample_org}/deactivate')
        data = resp.get_json()
        assert data['success'] is True
        pro = models.get_professional_by_user_id(user_id)
        assert pro['org_id'] is None

    def test_deactivate_unassigns_leads(self, admin_client, sample_org, sample_lead):
        models.set_lead_organization(sample_lead, sample_org)
        resp = admin_client.post(f'/api/admin/organizations/{sample_org}/deactivate')
        data = resp.get_json()
        assert data['success'] is True
        lead = models.get_lead_by_id(sample_lead)
        assert lead['org_id'] is None

    def test_slug_dedup(self, db):
        org1_id = models.create_organization('Inmobiliaria Sur')
        org2_id = models.create_organization('Inmobiliaria Sur')
        org1 = models.get_organization_by_id(org1_id)
        org2 = models.get_organization_by_id(org2_id)
        assert org1['slug'] != org2['slug']
        assert org2['slug'].startswith('inmobiliaria-sur-')

    def test_non_admin_cannot_manage_orgs(self, client, sample_professional):
        user_id, pro_name = sample_professional
        with client.session_transaction() as sess:
            sess['user_id'] = user_id
            sess['username'] = pro_name
            sess['role'] = 'professional'
        resp = client.get('/api/admin/organizations')
        assert resp.status_code in [302, 401, 403]

    def test_delete_organization(self, admin_client, sample_org):
        resp = admin_client.delete(f'/api/admin/organizations/{sample_org}')
        data = resp.get_json()
        assert data['success'] is True
        org = models.get_organization_by_id(sample_org)
        assert org is None

    def test_set_professional_organization(self, admin_client, sample_org, sample_professional):
        user_id, _ = sample_professional
        resp = admin_client.put(f'/api/admin/professionals/{user_id}/organization', json={
            'org_id': sample_org
        })
        data = resp.get_json()
        assert data['success'] is True
        pro = models.get_professional_by_user_id(user_id)
        assert pro['org_id'] == sample_org

    def test_set_lead_organization(self, admin_client, sample_org, sample_lead):
        resp = admin_client.put(f'/api/admin/leads/{sample_lead}/organization', json={
            'org_id': sample_org
        })
        data = resp.get_json()
        assert data['success'] is True
        lead = models.get_lead_by_id(sample_lead)
        assert lead['org_id'] == sample_org

    def test_member_count(self, admin_client, sample_org, sample_professional):
        user_id, _ = sample_professional
        models.set_professional_organization(user_id, sample_org)
        resp = admin_client.get('/api/admin/organizations')
        data = resp.get_json()
        org = next(o for o in data['organizations'] if o['id'] == sample_org)
        assert org['member_count'] >= 1
