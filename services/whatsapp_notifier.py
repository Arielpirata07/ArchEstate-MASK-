"""
WhatsApp Lead Notifier.

Envía notificaciones de leads por WhatsApp usando Twilio Content API.
Usa un template pre-aprobado con variables {{1}}..{{5}}.
Si TWILIO_SIMULATE=True, logea a consola en vez de enviar.
"""

import json
import logging

import config


logger = logging.getLogger(__name__)


LEAD_VARIABLE_MAP = {
    1: 'type',
    2: 'zone',
    3: 'budget_formatted',
    4: 'property_type',
    5: 'province',
}


class WhatsAppLeadNotifier:
    """Sends lead notifications via WhatsApp using Twilio Content API."""

    def __init__(self, simulate=None):
        self._simulate = simulate if simulate is not None else config.TWILIO_SIMULATE
        self._client = None
        if not self._simulate:
            try:
                from twilio.rest import Client
                self._client = Client(config.TWILIO_ACCOUNT_SID, config.TWILIO_AUTH_TOKEN)
            except Exception:
                logger.warning('Failed to init Twilio client, falling back to simulate', exc_info=True)
                self._simulate = True

    def is_available(self):
        if self._simulate:
            return False
        if not config.TWILIO_WHATSAPP_FROM or not config.TWILIO_WHATSAPP_LEAD_CONTENT_SID:
            return False
        return self._client is not None

    def send_lead_alert(self, phone_e164, lead_data):
        """Send a WhatsApp lead notification. Returns True on success."""
        if not phone_e164:
            logger.warning('WhatsApp: no phone provided')
            return False

        variables = self._build_variables(lead_data)

        if self._simulate:
            logger.info(
                '[SIMULATED WhatsApp] To: %s | Variables: %s',
                phone_e164, json.dumps(variables, ensure_ascii=False)
            )
            return True

        try:
            to_number = f'whatsapp:{phone_e164}'
            from_number = f'whatsapp:{config.TWILIO_WHATSAPP_FROM}'
            content_variables = json.dumps(variables)

            self._client.messages.create(
                from_=from_number,
                content_sid=config.TWILIO_WHATSAPP_LEAD_CONTENT_SID,
                content_variables=content_variables,
                to=to_number,
            )
            logger.info('WhatsApp lead alert sent to %s', phone_e164)
            return True
        except Exception:
            logger.exception('WhatsApp send failed for %s', phone_e164)
            return False

    def _build_variables(self, lead_data):
        """Build content_variables dict from lead data."""
        raw_budget = lead_data.get('budget', '')
        try:
            budget_num = float(str(raw_budget).replace('$', '').replace(',', '').strip())
            budget_str = f'${budget_num:,.2f}'
        except (ValueError, TypeError):
            budget_str = str(raw_budget) if raw_budget else '-'

        currency = lead_data.get('currency', 'USD') or 'USD'
        budget_formatted = f'{budget_str} {currency}'

        variables = {
            '1': str(lead_data.get('type', '') or ''),
            '2': str(lead_data.get('zone', '') or ''),
            '3': budget_formatted,
            '4': str(lead_data.get('property_type', '') or ''),
            '5': str(lead_data.get('province', '') or ''),
        }
        return variables
