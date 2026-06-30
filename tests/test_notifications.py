import os
import uuid
import pytest
from unittest.mock import patch, MagicMock

from werkzeug.security import generate_password_hash

import models
from services.notifications import (
    notify_lead_created,
    notify_lead_status_change,
    notify_professional_status_change,
    notify_report_deleted,
    _send_email_notification,
    _send_sms_notification,
    _get_admin_users,
)


@pytest.fixture
def admin_user(db):
    unique = uuid.uuid4().hex[:8]
    cursor = db.execute(
        'INSERT INTO users (username, email, hash, role, phone, phone_e164, is_active) VALUES (?, ?, ?, ?, ?, ?, ?)',
        (f'admin_{unique}', f'admin_{unique}@test.com', generate_password_hash('pass'), 'admin', '+5491112345678', '+5491112345678', 1)
    )
    db.commit()
    return cursor.lastrowid


@pytest.fixture
def professional_user(db):
    unique = uuid.uuid4().hex[:8]
    cursor = db.execute(
        'INSERT INTO users (username, email, hash, role, phone, phone_e164, is_active) VALUES (?, ?, ?, ?, ?, ?, ?)',
        (f'pro_{unique}', f'pro_{unique}@test.com', generate_password_hash('pass'), 'professional', '+5491198765432', '+5491198765432', 1)
    )
    db.commit()
    user_id = cursor.lastrowid
    db.execute(
        'INSERT INTO professionals (user_id, name, license, specialty, status) VALUES (?, ?, ?, ?, ?)',
        (user_id, f'Pro {unique}', f'LIC-{unique}', 'arquitectura', 'approved')
    )
    db.commit()
    return user_id


@pytest.fixture
def sample_lead(db, admin_user):
    cursor = db.execute(
        '''INSERT INTO leads (type, property_type, zone, budget, currency, phone, email, user_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
        ('comprar', 'departamento', 'Palermo', '200000', 'USD', '+5491112345678', 'test@test.com', admin_user)
    )
    db.commit()
    return cursor.lastrowid


@pytest.fixture
def sample_report(db, admin_user, sample_lead):
    cursor = db.execute(
        'INSERT INTO lead_reports (lead_id, reported_by, reason, notes, status) VALUES (?, ?, ?, ?, ?)',
        (sample_lead, admin_user, 'telefono_inexistente', 'Test report', 'pending')
    )
    db.commit()
    return cursor.lastrowid


class TestSendEmailNotification:
    @patch('services.notifications.get_email_sender')
    def test_sends_when_enabled(self, mock_sender, db, admin_user):
        mock_sender.return_value.send.return_value = True
        db.execute('INSERT INTO user_preferences (user_id, email_notifications) VALUES (?, 1)', (admin_user,))
        db.commit()

        result = _send_email_notification(admin_user, 'Test', '<p>Hi</p>')
        assert result is True
        mock_sender.return_value.send.assert_called_once()

    @patch('services.notifications.get_email_sender')
    def test_skips_when_disabled(self, mock_sender, db, admin_user):
        db.execute('INSERT INTO user_preferences (user_id, email_notifications) VALUES (?, 0)', (admin_user,))
        db.commit()

        result = _send_email_notification(admin_user, 'Test', '<p>Hi</p>')
        assert result is False
        mock_sender.return_value.send.assert_not_called()

    @patch('services.notifications.get_email_sender')
    def test_skips_when_no_email(self, mock_sender, db):
        cursor = db.execute(
            'INSERT INTO users (username, email, hash, role, is_active) VALUES (?, ?, ?, ?, ?)',
            ('noemail', '', generate_password_hash('pass'), 'client', 1)
        )
        db.commit()
        user_id = cursor.lastrowid
        db.execute('INSERT INTO user_preferences (user_id, email_notifications) VALUES (?, 1)', (user_id,))
        db.commit()

        result = _send_email_notification(user_id, 'Test', '<p>Hi</p>')
        assert result is False


class TestNotifyLeadCreated:
    @patch('services.notifications._send_email_notification')
    def test_notifies_approved_professionals(self, mock_email, db, professional_user, sample_lead):
        notify_lead_created(sample_lead)
        assert mock_email.call_count >= 1

    @patch('services.notifications._send_email_notification')
    def test_skips_professionals_with_alerts_disabled(self, mock_email, db, professional_user, sample_lead):
        db.execute('INSERT INTO user_preferences (user_id, lead_alerts) VALUES (?, 0)', (professional_user,))
        db.commit()

        # Get the professional's user_id from the professionals table
        pro = db.execute('SELECT user_id FROM professionals WHERE user_id = ?', (professional_user,)).fetchone()
        if pro:
            # Verify the preference was set correctly
            prefs = models.get_user_preferences(professional_user)
            assert prefs.get('lead_alerts') == 0

        # Mock to track calls but let the real function run
        mock_email.reset_mock()
        notify_lead_created(sample_lead)
        # The professional with lead_alerts=0 should NOT receive email
        # Check that the professional's id was NOT in the call args
        for call in mock_email.call_args_list:
            assert call[0][0] != professional_user

    @patch('services.notifications._send_email_notification')
    def test_skips_nonexistent_lead(self, mock_email, db):
        notify_lead_created(99999)
        mock_email.assert_not_called()

    @patch('services.notifications._send_email_notification')
    @patch('services.notifications._send_lead_whatsapp')
    def test_budget_matching_in_range(self, mock_whatsapp, mock_email, db, professional_user, sample_lead):
        db.execute(
            'INSERT INTO user_preferences (user_id, lead_alerts, budget_min, budget_max) VALUES (?, 1, 100000, 300000)',
            (professional_user,)
        )
        db.commit()
        notify_lead_created(sample_lead)
        assert mock_email.call_count >= 1

    @patch('services.notifications._send_email_notification')
    def test_budget_matching_below_min(self, mock_email, db, professional_user, sample_lead):
        db.execute(
            'INSERT INTO user_preferences (user_id, lead_alerts, budget_min, budget_max) VALUES (?, 1, 300000, 500000)',
            (professional_user,)
        )
        db.commit()
        notify_lead_created(sample_lead)
        # The professional with budget_min=300k should not receive email for a 200k lead
        for call_args, _ in mock_email.call_args_list:
            assert call_args[0] != professional_user

    @patch('services.notifications._send_email_notification')
    def test_budget_matching_above_max(self, mock_email, db, professional_user, sample_lead):
        db.execute(
            'INSERT INTO user_preferences (user_id, lead_alerts, budget_min, budget_max) VALUES (?, 1, 10000, 50000)',
            (professional_user,)
        )
        db.commit()
        notify_lead_created(sample_lead)
        for call_args, _ in mock_email.call_args_list:
            assert call_args[0] != professional_user

    @patch('services.notifications._send_email_notification')
    def test_budget_matching_zero_bounds(self, mock_email, db, professional_user, sample_lead):
        """budget_min=0 o budget_max=0 no deben filtrar."""
        db.execute(
            'INSERT INTO user_preferences (user_id, lead_alerts, budget_min, budget_max) VALUES (?, 1, 0, 0)',
            (professional_user,)
        )
        db.commit()
        notify_lead_created(sample_lead)
        # professional with zero bounds should receive notification
        found = any(call_args[0] == professional_user for call_args, _ in mock_email.call_args_list)
        assert found, f'Professional {professional_user} should have been notified'

    @patch('services.notifications._send_email_notification')
    @patch('services.notifications._send_lead_whatsapp')
    def test_channel_email_only(self, mock_whatsapp, mock_email, db, professional_user, sample_lead):
        db.execute(
            'INSERT INTO user_preferences (user_id, lead_alerts, preferred_channel) VALUES (?, 1, \'email\')',
            (professional_user,)
        )
        db.commit()
        notify_lead_created(sample_lead)
        found_email = any(call_args[0] == professional_user for call_args, _ in mock_email.call_args_list)
        assert found_email
        # whatsapp should not be called for this professional
        for call_args, _ in mock_whatsapp.call_args_list:
            assert call_args[0] != professional_user

    @patch('services.notifications._send_email_notification')
    @patch('services.notifications._send_lead_whatsapp')
    def test_channel_whatsapp_only(self, mock_whatsapp, mock_email, db, professional_user, sample_lead):
        db.execute(
            'INSERT INTO user_preferences (user_id, lead_alerts, preferred_channel) VALUES (?, 1, \'whatsapp\')',
            (professional_user,)
        )
        db.commit()
        notify_lead_created(sample_lead)
        for call_args, _ in mock_email.call_args_list:
            assert call_args[0] != professional_user
        found_wa = any(call_args[0] == professional_user for call_args, _ in mock_whatsapp.call_args_list)
        assert found_wa

    @patch('services.notifications._send_email_notification')
    @patch('services.notifications._send_lead_whatsapp')
    def test_channel_ambos(self, mock_whatsapp, mock_email, db, professional_user, sample_lead):
        db.execute(
            'INSERT INTO user_preferences (user_id, lead_alerts, preferred_channel) VALUES (?, 1, \'ambos\')',
            (professional_user,)
        )
        db.commit()
        notify_lead_created(sample_lead)
        found_email = any(call_args[0] == professional_user for call_args, _ in mock_email.call_args_list)
        found_wa = any(call_args[0] == professional_user for call_args, _ in mock_whatsapp.call_args_list)
        assert found_email
        assert found_wa


class TestNotifyLeadStatusChange:
    @patch('services.notifications._send_email_notification')
    def test_notifies_admins(self, mock_email, db, admin_user, professional_user, sample_lead):
        notify_lead_status_change(sample_lead, professional_user, 'seen')
        assert mock_email.call_count >= 1

    @patch('services.notifications._send_email_notification')
    def test_includes_correct_status_label(self, mock_email, db, admin_user, professional_user, sample_lead):
        notify_lead_status_change(sample_lead, professional_user, 'contacted')
        call_args = mock_email.call_args
        assert 'contactado' in call_args[0][1]


class TestNotifyProfessionalStatusChange:
    @patch('services.notifications._send_email_notification')
    def test_notifies_on_approval(self, mock_email, db, professional_user):
        conn = models.get_db_connection()
        pro = conn.execute('SELECT id FROM professionals WHERE user_id = ?', (professional_user,)).fetchone()
        conn.close()

        notify_professional_status_change(pro['id'], 'approved')
        assert mock_email.call_count >= 1

    @patch('services.notifications._send_email_notification')
    def test_notifies_on_rejection(self, mock_email, db, professional_user):
        conn = models.get_db_connection()
        pro = conn.execute('SELECT id FROM professionals WHERE user_id = ?', (professional_user,)).fetchone()
        conn.close()

        notify_professional_status_change(pro['id'], 'rejected')
        assert mock_email.call_count >= 1
        call_args = mock_email.call_args
        assert 'rechazada' in call_args[0][1]


class TestNotifyReportDeleted:
    @patch('services.notifications._send_email_notification')
    def test_notifies_reporter(self, mock_email, db, admin_user, sample_report, sample_lead):
        notify_report_deleted(sample_lead, admin_user)
        assert mock_email.call_count >= 1


class TestGetAdminUsers:
    def test_returns_active_admins(self, db, admin_user):
        admins = _get_admin_users()
        assert len(admins) >= 1
        assert any(a['id'] == admin_user for a in admins)

    def test_excludes_inactive_admins(self, db, admin_user):
        db.execute('UPDATE users SET is_active = 0 WHERE id = ?', (admin_user,))
        db.commit()
        admins = _get_admin_users()
        assert not any(a['id'] == admin_user for a in admins)
