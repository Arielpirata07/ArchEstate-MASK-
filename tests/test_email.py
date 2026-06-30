import os
import pytest
from unittest.mock import patch, MagicMock

from services.email import SMTPEmailSender, get_email_sender, reset_email_sender


class TestSMTPEmailSender:
    """Tests for the SMTPEmailSender class."""

    def test_not_configured_returns_true_with_console_output(self, capsys):
        sender = SMTPEmailSender(host='', from_addr='')
        result = sender.send('test@example.com', 'Test Subject', '<p>Hello</p>')
        assert result is True
        captured = capsys.readouterr()
        assert '[EMAIL SIMULADO]' in captured.out

    def test_is_configured_false_when_no_host(self):
        sender = SMTPEmailSender(host='', from_addr='test@test.com')
        assert sender.is_configured is False

    def test_is_configured_false_when_no_from(self):
        sender = SMTPEmailSender(host='smtp.test.com', from_addr='')
        assert sender.is_configured is False

    def test_is_configured_true_when_both_set(self):
        sender = SMTPEmailSender(host='smtp.test.com', from_addr='test@test.com')
        assert sender.is_configured is True

    @patch('services.email.smtplib.SMTP')
    def test_send_success_with_smtp(self, mock_smtp):
        mock_server = MagicMock()
        mock_smtp.return_value.__enter__ = MagicMock(return_value=mock_server)
        mock_smtp.return_value.__exit__ = MagicMock(return_value=False)

        sender = SMTPEmailSender(
            host='smtp.test.com', port=587,
            user='user@test.com', password='pass',
            from_addr='sender@test.com', use_tls=True
        )
        result = sender.send('recipient@test.com', 'Subject', '<p>Body</p>')

        assert result is True
        mock_smtp.assert_called_once_with('smtp.test.com', 587, timeout=15)

    @patch('services.email.smtplib.SMTP')
    def test_send_failure_returns_false(self, mock_smtp, caplog):
        mock_smtp.side_effect = Exception('Connection refused')

        sender = SMTPEmailSender(
            host='smtp.test.com', port=587,
            from_addr='sender@test.com'
        )
        result = sender.send('recipient@test.com', 'Subject', '<p>Body</p>')

        assert result is False
        assert 'Error al enviar email a' in caplog.text

    def test_send_includes_text_and_html(self, capsys):
        sender = SMTPEmailSender(host='', from_addr='')
        result = sender.send(
            'test@example.com', 'Subject',
            '<p>HTML body</p>', text_body='Text body'
        )
        assert result is True


class TestEmailSenderSingleton:
    """Tests for the email sender singleton."""

    def setup_method(self):
        reset_email_sender()

    def teardown_method(self):
        reset_email_sender()

    def test_singleton_returns_same_instance(self):
        s1 = get_email_sender()
        s2 = get_email_sender()
        assert s1 is s2

    def test_reset_creates_new_instance(self):
        s1 = get_email_sender()
        reset_email_sender()
        s2 = get_email_sender()
        assert s1 is not s2
