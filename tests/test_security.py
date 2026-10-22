import re
import uuid

import pytest
from werkzeug.security import generate_password_hash

import models

# Campos controlados por usuarios que JAMÁS deben interpolarse sin escapeHtml.
# Cada ocurrencia en JS debe estar dentro de escapeHtml(...).
USER_CONTROLLED_FIELDS = [
    'pro.name', 'pro.specialty', 'pro.license',
    'o.category', 'o.value', 'o.label', 'o.icon',
    'c.code', 'c.city', 'c.province', 'c.country', 'c.country_code',
    'm.username', 'm.email',
    'n.title', 'n.recipient_username',
    'lead.zone', 'lead.type', 'lead.property_type', 'lead.province',
    'lead.pool', 'lead.elevator', 'lead.floor_block',
    'it.label', 'a.trim()',
]

JS_FILES = [
    'static/js/admin.js', 'static/js/professional.js', 'static/js/profile.js',
    'static/js/user.js', 'static/js/forms.js', 'static/js/toasts.js',
    'static/js/modals.js', 'static/js/budget.js', 'static/js/scroll.js',
    'static/js/usermgmt.js', 'static/js/landing.js',
]


class TestXssEscaping:
    @pytest.mark.parametrize('field', USER_CONTROLLED_FIELDS)
    def test_user_controlled_fields_escaped(self, field):
        offenders = []
        for path in JS_FILES:
            src = open(path, encoding='utf-8').read()
            for i, line in enumerate(src.splitlines(), 1):
                stripped = line.strip()
                if not re.search(re.escape(field), line):
                    continue
                if stripped.startswith(('<!--', '//', '*')):
                    continue
                # Solo importa si la línea construye HTML (comparaciones y
                # lecturas .value son lógica, no interpolación)
                if '<' not in line:
                    continue
                # La interpolación debe estar envuelta en un escaper en la misma línea
                # (escapeHtml o el equivalente local escapePipelineHtml)
                if 'escapeHtml(' not in line and 'escapePipelineHtml(' not in line:
                    offenders.append(f'{path}:{i}: {stripped[:100]}')
        assert not offenders, 'Interpolación sin escapeHtml:\n' + '\n'.join(offenders)


def _make_user(db):
    unique = uuid.uuid4().hex[:8]
    cursor = db.execute(
        'INSERT INTO users (username, email, hash, role, phone, phone_format_valid) VALUES (?, ?, ?, ?, ?, 1)',
        (f'sec_{unique}', f'{unique}@example.com', generate_password_hash('x'), 'client', '+5491112345678')
    )
    user_id = cursor.lastrowid
    db.commit()
    return user_id


class TestAtomicLeadUpdate:
    def test_version_and_update_commit_together(self, db):
        user_id = _make_user(db)
        lead_id = db.execute(
            "INSERT INTO leads (type, property_type, zone, budget, currency, phone, email, user_id) VALUES ('comprar', 'departamento', 'Palermo', '100', 'USD', '+5491112345678', 'a@b.com', ?)",
            (user_id,)
        ).lastrowid
        db.commit()
        ok = models.update_lead_versioned(lead_id, {'zone': 'Recoleta'}, user_id, '{"zone": "Palermo"}')
        assert ok is True
        lead = db.execute('SELECT zone FROM leads WHERE id = ?', (lead_id,)).fetchone()
        assert lead['zone'] == 'Recoleta'
        n = db.execute('SELECT COUNT(*) FROM lead_versions WHERE lead_id = ?', (lead_id,)).fetchone()[0]
        assert n == 1

    def test_sequential_updates_version_incrementally(self, db):
        user_id = _make_user(db)
        lead_id = db.execute(
            "INSERT INTO leads (type, property_type, zone, budget, currency, phone, email, user_id) VALUES ('comprar', 'departamento', 'Palermo', '100', 'USD', '+5491112345678', 'a@b.com', ?)",
            (user_id,)
        ).lastrowid
        db.commit()
        models.update_lead_versioned(lead_id, {'zone': 'A'}, user_id, '{}')
        models.update_lead_versioned(lead_id, {'zone': 'B'}, user_id, '{}')
        versions = [r['version'] for r in db.execute(
            'SELECT version FROM lead_versions WHERE lead_id = ? ORDER BY version', (lead_id,)).fetchall()]
        assert versions == [1, 2]

    def test_empty_update_returns_false(self, db):
        assert models.update_lead_versioned(1, {}, 1, '{}') is False


class TestAtomicAccountUpdate:
    def test_email_and_profile_commit_together(self, db):
        user_id = _make_user(db)
        ok = models.update_user_account(user_id, 'nuevo@example.com', '',
                                        {'first_name': 'Ana', 'bio': 'Hola'})
        assert ok is True
        row = db.execute('SELECT email FROM users WHERE id = ?', (user_id,)).fetchone()
        assert row['email'] == 'nuevo@example.com'
        prof = db.execute('SELECT first_name FROM user_profiles WHERE user_id = ?', (user_id,)).fetchone()
        assert prof['first_name'] == 'Ana'

    def test_empty_profile_still_updates_email(self, db):
        user_id = _make_user(db)
        assert models.update_user_account(user_id, 'otro@example.com', '', {}) is True


class TestUploadAndHeaderSecurity:
    def test_max_content_length_configured(self, app):
        import config
        assert app.config['MAX_CONTENT_LENGTH'] == config.MAX_UPLOAD_SIZE + 1024 * 1024

    def test_oversized_request_rejected_413(self, app, client, monkeypatch):
        monkeypatch.setitem(app.config, 'MAX_CONTENT_LENGTH', 1024)
        resp = client.post(
            '/login',
            data=b'x' * 4096,
            content_type='application/x-www-form-urlencoded',
            headers={'Accept': 'application/json'},
        )
        assert resp.status_code == 413
        assert resp.get_json()['error'] is not None

    def test_nosniff_applies_to_static_uploads(self, client):
        resp = client.get('/static/uploads/portfolio/no-such-file.png')
        assert resp.headers.get('X-Content-Type-Options') == 'nosniff'
