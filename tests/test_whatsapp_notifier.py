import pytest
from unittest.mock import patch, MagicMock

import config


class TestWhatsAppLeadNotifier:

    def _notifier(self, simulate=True):
        from services.whatsapp_notifier import WhatsAppLeadNotifier
        return WhatsAppLeadNotifier(simulate=simulate)

    def test_simulate_mode(self):
        n = self._notifier(simulate=True)
        assert n.is_available() is False
        result = n.send_lead_alert('+5491112345678', {'type': 'comprar', 'zone': 'Palermo'})
        assert result is True

    def test_no_phone_returns_false(self):
        n = self._notifier(simulate=True)
        result = n.send_lead_alert(None, {})
        assert result is False

    @patch('services.whatsapp_notifier.config.TWILIO_SIMULATE', False)
    def test_is_available_false_when_no_creds(self):
        n = self._notifier(simulate=True)
        assert n.is_available() is False

    @patch('services.whatsapp_notifier.config.TWILIO_SIMULATE', True)
    def test_simulate_flag_from_config(self):
        from services.whatsapp_notifier import WhatsAppLeadNotifier
        n = WhatsAppLeadNotifier()
        assert n.is_available() is False

    def test_build_variables(self):
        n = self._notifier(simulate=True)
        vars = n._build_variables({
            'type': 'comprar',
            'zone': 'Palermo',
            'budget': '200000',
            'property_type': 'departamento',
            'province': 'CABA',
        })
        assert vars['1'] == 'comprar'
        assert vars['2'] == 'Palermo'
        assert '$200,000.00' in vars['3']
        assert 'USD' in vars['3']
        assert vars['4'] == 'departamento'
        assert vars['5'] == 'CABA'

    def test_build_variables_empty_budget(self):
        n = self._notifier(simulate=True)
        vars = n._build_variables({'type': 'alquilar', 'budget': None, 'currency': None})
        assert vars['3'] == '- USD'

    def test_build_variables_non_numeric_budget(self):
        n = self._notifier(simulate=True)
        vars = n._build_variables({'type': 'alquilar', 'budget': 'Consultar', 'currency': 'USD'})
        assert vars['3'] == 'Consultar USD'
