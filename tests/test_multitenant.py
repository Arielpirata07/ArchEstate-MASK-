import uuid

import pytest
from werkzeug.security import generate_password_hash

import models


@pytest.fixture
def admin_client(client):
    conn = models.get_db_connection()
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
    return models.create_organization('Org Test Multitenant', 'desc')


@pytest.fixture
def sample_professional(db):
    unique = uuid.uuid4().hex[:8]
    pro_name = f'ProMt {unique}'
    cursor = db.execute(
        'INSERT INTO users (username, email, hash, role, phone, phone_e164, is_active) VALUES (?, ?, ?, ?, ?, ?, ?)',
        (pro_name, f'promt_{unique}@test.com', generate_password_hash('pass'), 'professional', '+5491198765432', '+5491198765432', 1)
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
        ('comprar', 'departamento', 'Palermo', 'Buenos Aires', '200000', 'USD', f'+54911123{unique[:4]}', f'mt_{unique}@test.com', 1)
    )
    db.commit()
    return cursor.lastrowid


def login_as(client, user_id, username, role='professional'):
    with client.session_transaction() as sess:
        sess['user_id'] = user_id
        sess['username'] = username
        sess['role'] = role
    return client


class TestMultiTenant:
    def test_create_organization(self, admin_client):
        resp = admin_client.post('/api/admin/organizations', json={'name': 'Org MT', 'description': 'x'})
        assert resp.get_json()['success'] is True

    def test_duplicate_slug_returns_409(self, admin_client, sample_org):
        org = models.get_organization_by_id(sample_org)
        resp = admin_client.post('/api/admin/organizations', json={'name': 'Otra', 'slug': org['slug']})
        assert resp.status_code == 409

    def test_add_member(self, admin_client, sample_org, sample_professional):
        user_id, _ = sample_professional
        resp = admin_client.post(f'/api/admin/organizations/{sample_org}/members', json={'user_id': user_id, 'role': 'member'})
        assert resp.get_json()['success'] is True
        members = models.get_org_members(sample_org)
        assert any(m['user_id'] == user_id for m in members)

    def test_add_member_invalid_role(self, admin_client, sample_org, sample_professional):
        user_id, _ = sample_professional
        resp = admin_client.post(f'/api/admin/organizations/{sample_org}/members', json={'user_id': user_id, 'role': 'boss'})
        assert resp.status_code == 400

    def test_remove_member(self, admin_client, sample_org, sample_professional):
        user_id, _ = sample_professional
        models.add_org_member(sample_org, user_id, 'member')
        resp = admin_client.delete(f'/api/admin/organizations/{sample_org}/members/{user_id}')
        assert resp.get_json()['success'] is True
        assert not any(m['user_id'] == user_id for m in models.get_org_members(sample_org))

    def test_change_member_role(self, admin_client, sample_org, sample_professional):
        user_id, _ = sample_professional
        models.add_org_member(sample_org, user_id, 'member')
        resp = admin_client.put(f'/api/admin/organizations/{sample_org}/members/{user_id}', json={'role': 'admin'})
        assert resp.get_json()['success'] is True
        members = models.get_org_members(sample_org)
        assert next(m for m in members if m['user_id'] == user_id)['role'] == 'admin'

    def test_list_members(self, admin_client, sample_org, sample_professional):
        user_id, _ = sample_professional
        models.add_org_member(sample_org, user_id, 'owner')
        resp = admin_client.get(f'/api/admin/organizations/{sample_org}/members')
        data = resp.get_json()
        assert data['success'] is True
        assert any(m['role'] == 'owner' for m in data['members'])

    def test_deactivate_unassigns_members(self, admin_client, sample_org, sample_professional):
        user_id, _ = sample_professional
        models.add_org_member(sample_org, user_id, 'member')
        admin_client.post(f'/api/admin/organizations/{sample_org}/deactivate')
        assert models.get_org_members(sample_org) == []

    def test_my_org(self, client, sample_org, sample_professional):
        user_id, pro_name = sample_professional
        models.add_org_member(sample_org, user_id, 'admin')
        login_as(client, user_id, pro_name)
        resp = client.get('/api/professional/my-org')
        data = resp.get_json()
        assert data['success'] is True
        assert data['org']['id'] == sample_org

    def test_my_org_none(self, client, sample_professional):
        user_id, pro_name = sample_professional
        login_as(client, user_id, pro_name)
        resp = client.get('/api/professional/org-leads')
        data = resp.get_json()
        assert data['success'] is True
        assert data['total'] == 0

    def test_org_leads_visible_for_members(self, client, sample_org, sample_professional, sample_lead):
        user_id, pro_name = sample_professional
        models.add_org_member(sample_org, user_id, 'member')
        models.set_lead_organization(sample_lead, sample_org)
        login_as(client, user_id, pro_name)
        resp = client.get('/api/professional/org-leads')
        data = resp.get_json()
        assert data['success'] is True
        assert data['total'] >= 1

    def test_org_pool_in_my_leads(self, client, sample_org, sample_professional, sample_lead):
        user_id, pro_name = sample_professional
        models.add_org_member(sample_org, user_id, 'member')
        models.set_lead_organization(sample_lead, sample_org)
        login_as(client, user_id, pro_name)
        resp = client.get('/api/leads?my_leads=1&per_page=100')
        data = resp.get_json()
        assert data['success'] is True
        assert any(l['id'] == sample_lead for l in data['leads'])

    def test_lead_without_org_visible_for_all(self, client, sample_professional, sample_lead):
        user_id, pro_name = sample_professional
        login_as(client, user_id, pro_name)
        resp = client.get('/api/leads?my_leads=0&per_page=100')
        data = resp.get_json()
        assert data['success'] is True
        assert any(l['id'] == sample_lead for l in data['leads'])

    def test_set_professional_org_syncs_members(self, admin_client, sample_org, sample_professional):
        user_id, _ = sample_professional
        resp = admin_client.put(f'/api/admin/professionals/{user_id}/organization', json={'org_id': sample_org})
        assert resp.get_json()['success'] is True
        assert any(m['user_id'] == user_id for m in models.get_org_members(sample_org))

    def test_non_admin_cannot_manage_members(self, client, sample_org, sample_professional):
        user_id, pro_name = sample_professional
        login_as(client, user_id, pro_name)
        resp = client.post(f'/api/admin/organizations/{sample_org}/members', json={'user_id': user_id})
        assert resp.status_code in (302, 401, 403)
