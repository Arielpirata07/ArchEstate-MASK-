'''Regresiones de la segunda pasada de revisión.

Cubre: normalización de canal de notificación, lookup de profesional por
user_id, revocación de remember-me al cambiar contraseña, respuesta JSON para
usuarios inactivos, reintento de los índices únicos v8 y orden de guardado del
avatar.
'''
import io
import os
import sqlite3
import uuid

import pytest
from werkzeug.datastructures import FileStorage
from werkzeug.security import generate_password_hash

import db_migrations
import models
import utils
from services import notifications as notif_service


def _make_user(conn, role='client', username=None, email=None):
    '''Crea un usuario y devuelve (user_id, username).'''
    unique = uuid.uuid4().hex[:8]
    username = username or f'sp_{unique}'
    email = email or f'sp_{unique}@example.com'
    cursor = conn.execute(
        'INSERT INTO users (username, email, hash, role, phone, phone_format_valid) '
        'VALUES (?, ?, ?, ?, ?, 1)',
        (username, email, generate_password_hash('abc123'), role, '+5491112345678')
    )
    conn.commit()
    return cursor.lastrowid, username


def _token_row(user_id, selector):
    return (
        'INSERT INTO remember_tokens (user_id, selector, validator_hash, expires_at) '
        'VALUES (?, ?, ?, ?)',
        (user_id, selector, 'hash-' + selector, '2999-01-01T00:00:00')
    )


class TestLeadChannelNormalization:
    '''El selector OTP (sms/whatsapp/auto) y el de notificaciones de leads
    (email/whatsapp/ambos/auto) escriben la misma columna.'''

    def test_lead_vocabulary_is_preserved(self):
        assert notif_service._normalize_lead_channel('email') == 'email'
        assert notif_service._normalize_lead_channel('whatsapp') == 'whatsapp'
        assert notif_service._normalize_lead_channel('ambos') == 'ambos'
        assert notif_service._normalize_lead_channel('auto') == 'auto'

    def test_otp_sms_maps_to_email(self):
        # Regresión: guardar 'sms' desde el selector OTP dejaba al profesional
        # sin email ni WhatsApp (ninguna rama del dispatch lo cubría).
        assert notif_service._normalize_lead_channel('sms') == 'email'
        assert notif_service._normalize_lead_channel('  SMS ') == 'email'

    def test_unknown_or_empty_falls_back_to_auto(self):
        assert notif_service._normalize_lead_channel('telepatia') == 'auto'
        assert notif_service._normalize_lead_channel('') == 'auto'
        assert notif_service._normalize_lead_channel(None) == 'auto'


class TestProfessionalStatusLookup:
    '''Lookup por FK user_id con fallback legacy por nombre.'''

    def test_prefers_user_id_when_name_drifted(self, db):
        user_id, username = _make_user(db, role='professional')
        unique = uuid.uuid4().hex[:8]
        db.execute(
            'INSERT INTO professionals (user_id, name, license, specialty, status) '
            'VALUES (?, ?, ?, ?, ?)',
            (user_id, f'Nombre Renombrado {unique}', f'LIC-{unique}', 'arquitectura', 'approved')
        )
        db.commit()
        # El username ya no coincide con professionals.name: antes daba 403.
        assert models.get_professional_status(db, user_id, username) == 'approved'

    def test_legacy_row_without_user_id_uses_name(self, db):
        user_id, username = _make_user(db, role='professional')
        unique = uuid.uuid4().hex[:8]
        db.execute(
            'INSERT INTO professionals (user_id, name, license, specialty, status) '
            'VALUES (NULL, ?, ?, ?, ?)',
            (username, f'LIC-{unique}', 'arquitectura', 'pending')
        )
        db.commit()
        assert models.get_professional_status(db, user_id, username) == 'pending'

    def test_unknown_professional_returns_none(self, db):
        assert models.get_professional_status(db, 99999999, 'nadie') is None


class TestRememberTokenRevocation:
    def test_helper_deletes_all_tokens_for_user(self, db):
        user_id, _ = _make_user(db)
        db.execute(*_token_row(user_id, 'sel-a-' + uuid.uuid4().hex[:6]))
        db.execute(*_token_row(user_id, 'sel-b-' + uuid.uuid4().hex[:6]))
        db.commit()

        assert utils.revoke_user_remember_tokens(user_id) == 2
        remaining = db.execute(
            'SELECT COUNT(*) FROM remember_tokens WHERE user_id = ?', (user_id,)
        ).fetchone()[0]
        assert remaining == 0

    def test_helper_without_tokens_returns_zero(self, db):
        user_id, _ = _make_user(db)
        assert utils.revoke_user_remember_tokens(user_id) == 0

    def test_password_change_revokes_remember_tokens(self, client, db):
        user_id, username = _make_user(db)
        db.execute(*_token_row(user_id, 'sel-profile-' + uuid.uuid4().hex[:6]))
        db.commit()
        with client.session_transaction() as sess:
            sess['user_id'] = user_id
            sess['username'] = username
            sess['role'] = 'client'

        resp = client.put('/api/profile/user/password', json={
            'current_password': 'abc123',
            'new_password': 'Nueva123',
        })
        assert resp.status_code == 200
        remaining = db.execute(
            'SELECT COUNT(*) FROM remember_tokens WHERE user_id = ?', (user_id,)
        ).fetchone()[0]
        assert remaining == 0


class TestInactiveUserResponses:
    def test_inactive_user_gets_json_401_on_api(self, client, db):
        user_id, username = _make_user(db)
        db.execute('UPDATE users SET is_active = 0 WHERE id = ?', (user_id,))
        db.commit()
        with client.session_transaction() as sess:
            sess['user_id'] = user_id
            sess['username'] = username
            sess['role'] = 'client'

        resp = client.get('/api/profile/settings', headers={'Accept': 'application/json'})
        assert resp.status_code == 401
        assert resp.get_json().get('error')


class _MemCursorMixin:
    def _memory_cursor(self):
        conn = sqlite3.connect(':memory:')
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute('CREATE TABLE lead_versions (id INTEGER PRIMARY KEY, lead_id INTEGER, version INTEGER)')
        cur.execute('CREATE TABLE professionals (id INTEGER PRIMARY KEY, user_id INTEGER, name TEXT)')
        cur.execute('CREATE TABLE users (id INTEGER PRIMARY KEY, email TEXT)')
        return conn, cur

    @staticmethod
    def _index_names(cur):
        return {row[0] for row in cur.execute(
            "SELECT name FROM sqlite_master WHERE type = 'index'"
        ).fetchall()}


class TestUniqueIndexMigrationRetry(_MemCursorMixin):
    def test_duplicates_skip_indexes_and_report_failure(self):
        conn, cur = self._memory_cursor()
        try:
            cur.execute("INSERT INTO users (email) VALUES ('dup@test.com'), ('DUP@test.com')")
            # False => apply_migrations NO marca v8 y reintenta en el próximo boot.
            assert db_migrations._dedupe_and_unique_indexes(cur) is False
            assert 'idx_users_email_unique' not in self._index_names(cur)
        finally:
            conn.close()

    def test_clean_data_creates_indexes_and_reports_success(self):
        conn, cur = self._memory_cursor()
        try:
            cur.execute("INSERT INTO users (email) VALUES ('a@test.com'), ('')")
            cur.execute("INSERT INTO professionals (user_id, name) VALUES (NULL, 'legacy')")
            assert db_migrations._dedupe_and_unique_indexes(cur) is True
            names = self._index_names(cur)
            assert 'idx_users_email_unique' in names
            assert 'idx_professionals_user_unique' in names
            assert 'idx_lead_versions_lead_version' in names
        finally:
            conn.close()


class TestUserEmailLookup:
    def test_lookup_is_case_insensitive(self, db):
        user_id, _ = _make_user(db, email='MiXeD.Case@Example.com')
        assert models.get_user_by_email('mixed.case@example.com')['id'] == user_id
        assert models.get_user_by_email('  MIXED.CASE@EXAMPLE.COM ')['id'] == user_id

    def test_lookup_handles_missing_and_empty_values(self, db):
        missing = f"nadie-{uuid.uuid4().hex}@example.com"
        assert models.get_user_by_email(missing) is None
        assert models.get_user_by_email('') is None
        assert models.get_user_by_email(None) is None


class TestStartupDirectories:
    def test_dirs_created_under_app_root_not_cwd(self, test_db_path, monkeypatch, tmp_path):
        from factory import create_app
        monkeypatch.chdir(tmp_path)
        flask_app = create_app()
        # init_db crea los directorios colgando de app.root_path...
        assert os.path.isdir(flask_app.config['AVATAR_FOLDER'])
        assert os.path.isdir(flask_app.config['PORTFOLIO_FOLDER'])
        assert os.path.isdir(flask_app.config['UPLOAD_FOLDER'])
        # ...y no un árbol static/ relativo al CWD del proceso.
        assert not (tmp_path / 'static').exists()


class TestAvatarUploadOrdering:
    def test_failed_save_keeps_previous_avatar(self, client, db, app, monkeypatch):
        user_id, username = _make_user(db)
        avatar_dir = app.config['AVATAR_FOLDER']
        os.makedirs(avatar_dir, exist_ok=True)
        filename = f'user_{user_id}_avatar.png'
        old_file = os.path.join(avatar_dir, filename)
        with open(old_file, 'wb') as fh:
            fh.write(b'avatar-viejo')
        old_rel = f'uploads/avatars/{filename}'
        assert models.update_user_avatar(user_id, old_rel) is True

        with client.session_transaction() as sess:
            sess['user_id'] = user_id
            sess['username'] = username
            sess['role'] = 'client'

        def _boom(self, dst, buffer_size=16384):
            raise OSError('disco lleno')

        monkeypatch.setattr(FileStorage, 'save', _boom)

        png = b'\x89PNG\r\n\x1a\n' + b'\x00' * 32
        try:
            resp = client.post(
                '/api/profile/user/avatar',
                data={'avatar': (io.BytesIO(png), 'nuevo.png')},
                content_type='multipart/form-data',
            )
            assert resp.status_code == 500
            # El avatar anterior sigue en disco y en la DB.
            assert os.path.exists(old_file)
            assert models.get_user_avatar_path(user_id) == old_rel
        finally:
            if os.path.exists(old_file):
                os.remove(old_file)
