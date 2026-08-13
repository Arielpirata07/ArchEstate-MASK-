import uuid

import pytest
from werkzeug.security import generate_password_hash

import models
from services.assignment import auto_assign_lead


@pytest.fixture
def professional(db):
    unique = uuid.uuid4().hex[:8]
    cursor = db.execute(
        'INSERT INTO users (username, email, hash, role, phone, is_active) VALUES (?, ?, ?, ?, ?, ?)',
        (f'pro_{unique}', f'pro_{unique}@test.com', generate_password_hash('pass'), 'professional', '+5491111111111', 1)
    )
    db.commit()
    user_id = cursor.lastrowid
    db.execute(
        'INSERT INTO professionals (user_id, name, license, specialty, province, zone, status) VALUES (?, ?, ?, ?, ?, ?, ?)',
        (user_id, f'Pro {unique}', f'LIC-{unique}', 'departamento', 'Córdoba', 'Nueva Córdoba', 'approved')
    )
    db.commit()
    return user_id


@pytest.fixture
def lead(db, professional):
    cursor = db.execute(
        '''INSERT INTO leads (type, property_type, zone, province, budget, currency, phone, email, user_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
        ('comprar', 'departamento', 'Nueva Córdoba', 'Córdoba', '200000', 'USD', '+5491111111111', 'lead@test.com', professional)
    )
    db.commit()
    return cursor.lastrowid


class TestAutoAssignLead:
    @staticmethod
    def _only_approved(db, *user_ids):
        db.execute('UPDATE professionals SET status = ?', ('rejected',))
        placeholders = ','.join('?' for _ in user_ids)
        db.execute(
            f'UPDATE professionals SET status = ? WHERE user_id IN ({placeholders})',
            ('approved', *user_ids)
        )
        db.commit()

    def test_assigns_best_match(self, db, professional, lead):
        self._only_approved(db, professional)
        assigned = auto_assign_lead(lead)
        assert assigned == professional

    def test_lead_is_persisted(self, db, professional, lead):
        self._only_approved(db, professional)
        auto_assign_lead(lead)
        row = db.execute('SELECT assigned_to FROM leads WHERE id = ?', (lead,)).fetchone()
        assert row['assigned_to'] == professional

    def test_returns_existing_assignment(self, db, professional, lead):
        other = db.execute(
            'INSERT INTO users (username, email, hash, role, phone, is_active) VALUES (?, ?, ?, ?, ?, ?)',
            (f'other_{uuid.uuid4().hex[:8]}', 'other@test.com', generate_password_hash('pass'), 'professional', '+5491222222222', 1)
        )
        db.commit()
        other_id = other.lastrowid
        db.execute('UPDATE leads SET assigned_to = ? WHERE id = ?', (other_id, lead))
        db.commit()

        result = auto_assign_lead(lead)
        assert result == other_id

    def test_returns_none_for_missing_lead(self, db):
        assert auto_assign_lead(999999) is None

    def test_returns_none_without_professionals(self, db, lead):
        db.execute('UPDATE professionals SET status = ?', ('rejected',))
        db.commit()
        assert auto_assign_lead(lead) is None

    def test_returns_none_when_nobody_matches(self, db, professional):
        """Un lead que no coincide con ninguna cobertura configurada debe
        quedar sin asignar, en vez de forzarse a quien tenga menos carga."""
        self._only_approved(db, professional)
        cursor = db.execute(
            '''INSERT INTO leads (type, property_type, zone, province, budget, currency, phone, email, user_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
            ('comprar', 'campo', 'Villa Carlos Paz', 'Mendoza', '50000', 'USD',
             '+5491111111199', 'nomatch@test.com', professional)
        )
        db.commit()
        unmatched_lead = cursor.lastrowid

        assigned = auto_assign_lead(unmatched_lead)
        assert assigned is None
        row = db.execute('SELECT assigned_to FROM leads WHERE id = ?', (unmatched_lead,)).fetchone()
        assert row['assigned_to'] is None

    def test_multi_zone_coverage_matches(self, db, professional, lead):
        """Un profesional que configuro varias zonas en professional_coverage
        debe matchear un lead en cualquiera de ellas, no solo en la legacy."""
        db.execute(
            "INSERT INTO professional_coverage (user_id, coverage_type, value) VALUES (?, 'zone', ?)",
            (professional, 'Villa Carlos Paz')
        )
        db.execute(
            "INSERT INTO professional_coverage (user_id, coverage_type, value) VALUES (?, 'zone', ?)",
            (professional, 'Nueva Córdoba')
        )
        db.commit()
        self._only_approved(db, professional)

        assigned = auto_assign_lead(lead)
        assert assigned == professional

    def test_specialty_match_outweighs_zone(self, db, professional, lead):
        unique = uuid.uuid4().hex[:8]
        cursor = db.execute(
            'INSERT INTO users (username, email, hash, role, phone, is_active) VALUES (?, ?, ?, ?, ?, ?)',
            (f'pro2_{unique}', f'pro2_{unique}@test.com', generate_password_hash('pass'), 'professional', '+5491333333333', 1)
        )
        db.commit()
        user2 = cursor.lastrowid
        db.execute(
            'INSERT INTO professionals (user_id, name, license, specialty, province, zone, status) VALUES (?, ?, ?, ?, ?, ?, ?)',
            (user2, 'Pro 2', f'LIC2-{unique}', 'departamento', 'CABA', 'Belgrano', 'approved')
        )
        db.commit()
        self._only_approved(db, professional, user2)

        assigned = auto_assign_lead(lead)
        assert assigned == professional

    def test_workload_penalizes_overloaded(self, db, professional, lead):
        other = db.execute(
            'INSERT INTO users (username, email, hash, role, phone, is_active) VALUES (?, ?, ?, ?, ?, ?)',
            (f'pro3_{uuid.uuid4().hex[:8]}', 'pro3@test.com', generate_password_hash('pass'), 'professional', '+5491444444444', 1)
        )
        db.commit()
        other_id = other.lastrowid
        db.execute(
            'INSERT INTO professionals (user_id, name, license, specialty, province, zone, status) VALUES (?, ?, ?, ?, ?, ?, ?)',
            (other_id, 'Pro 3', 'LIC3', 'departamento', 'Córdoba', 'Nueva Córdoba', 'approved')
        )
        db.commit()
        self._only_approved(db, professional, other_id)
        for i in range(3):
            db.execute(
                'INSERT INTO lead_tracking (lead_id, professional_id, contacted) VALUES (?, ?, ?)',
                (999998 - i, other_id, 1)
            )
        db.commit()

        assigned = auto_assign_lead(lead)
        assert assigned == professional
