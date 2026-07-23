"""
Capa de abstracción para el envío de OTP de verificación de teléfono.

Hoy: dos implementaciones simuladas (SmsSimulatedVerifier, WhatsAppSimulatedVerifier)
que sólo registran el envío en consola + audit log + consent_log.

Mañana: enchufar Twilio/360dialog/Meta Cloud API creando nuevas clases
(por ejemplo TwilioSmsVerifier, MetaWhatsAppVerifier) que respeten la
misma interfaz OTPChannel.
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional

from i18n import t, get_language

logger = logging.getLogger(__name__)

from utils import hash_phone_digits


@dataclass
class SendResult:
    ok: bool
    channel: str
    message: str
    meta: Optional[dict] = None


class OTPChannel(ABC):
    """Interfaz que cualquier proveedor real de SMS/WhatsApp debe implementar."""

    name: str = "abstract"

    @abstractmethod
    def send(self, phone_e164: str, code: str, ttl_minutes: int = 10, username: str = None) -> SendResult:
        """
        Envía un OTP al número (en formato E.164) y devuelve un SendResult.
        username: se incluye como {{3}} en el template de WhatsApp cuando está presente.
        No debe lanzar excepciones: fallos deben reflejarse en ok=False.
        """


class SmsSimulatedVerifier(OTPChannel):
    """Simula el envío de un SMS. Imprime en consola y registra en audit_log."""

    name = "sms"

    def __init__(self, audit_fn=None):
        self._audit = audit_fn

    def send(self, phone_e164, code, ttl_minutes=10, username=None):
        lang = get_language()
        try:
            print(f"\n[SMS SIMULADO] -> {phone_e164}")
            print(f"[SMS SIMULADO] Código: {code} (válido {ttl_minutes} min)\n")
            if self._audit:
                self._audit("OTP enviado por SMS", f"phone_hash={hash_phone_digits(phone_e164)} channel=sms ttl={ttl_minutes}m")
            return SendResult(ok=True, channel=self.name,
                              message=t('verifier.sms_sent', lang, phone=phone_e164))
        except Exception as e:
            return SendResult(ok=False, channel=self.name,
                              message=t('verifier.sms_error', lang, error=str(e)))


class WhatsAppSimulatedVerifier(OTPChannel):
    """
    Simula el envío de un OTP por WhatsApp. Genera un link wa.me con el código
    prellenado (sólo válido en la sesión local, no se envía nada al cliente real).

    include_deep_link: si True, expone el link wa.me con el código en SendResult.meta.
    Por defecto False — sólo en debug se devuelve el deep_link al cliente.
    En producción, este link NO debe llegar al cliente.
    """

    name = "whatsapp"

    def __init__(self, audit_fn=None, base_url: str = "https://wa.me", include_deep_link: bool = False):
        self._audit = audit_fn
        self._base_url = base_url
        self._include_deep_link = include_deep_link

    def send(self, phone_e164, code, ttl_minutes=10, username=None):
        lang = get_language()
        try:
            from urllib.parse import quote_plus
            digits = phone_e164.lstrip('+')
            label = f" {username}," if username else ""
            text = quote_plus(t('verifier.wa_otp_text', lang, label=label, code=code, ttl=ttl_minutes))
            link = f"{self._base_url}/{digits}?text={text}"
            print(f"\n[WHATSAPP SIMULADO] -> {phone_e164}")
            print(f"[WHATSAPP SIMULADO] Link wa.me con código prellenado (no enviado): {link}\n")
            if self._audit:
                self._audit("OTP enviado por WhatsApp",
                            f"phone_hash={hash_phone_digits(phone_e164)} channel=whatsapp ttl={ttl_minutes}m")
            meta = {"deep_link": link} if self._include_deep_link else None
            return SendResult(ok=True, channel=self.name,
                              message=t('verifier.wa_sent', lang),
                              meta=meta)
        except Exception as e:
            return SendResult(ok=False, channel=self.name,
                              message=t('verifier.wa_error', lang, error=str(e)))


class TwilioSmsVerifier(OTPChannel):
    """
    Envía SMS reales via Twilio. Requiere TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN
    y TWILIO_PHONE_NUMBER configurados en el entorno.
    """

    name = "sms"

    def __init__(self, account_sid, auth_token, from_number, audit_fn=None):
        from twilio.rest import Client
        self._client = Client(account_sid, auth_token)
        self._from = from_number
        self._audit = audit_fn

    def send(self, phone_e164, code, ttl_minutes=10, username=None):
        lang = get_language()
        try:
            body = t('verifier.twilio_sms_body', lang, code=code, ttl=ttl_minutes)
            message = self._client.messages.create(
                body=body,
                from_=self._from,
                to=phone_e164
            )
            print(f"\n[TWILIO SMS] -> {phone_e164} | SID: {message.sid}")
            if self._audit:
                self._audit("OTP enviado por SMS (Twilio)",
                            f"phone_hash={hash_phone_digits(phone_e164)} channel=sms sid={message.sid} ttl={ttl_minutes}m")
            return SendResult(ok=True, channel=self.name,
                              message=t('verifier.sms_sent', lang, phone=phone_e164))
        except Exception as e:
            error_str = str(e)
            logger.exception('[TWILIO SMS ERROR] -> %s', phone_e164)

            if '21608' in error_str or 'unverified' in error_str.lower():
                return SendResult(ok=False, channel=self.name,
                                  message=t('verifier.twilio_trial', lang))
            elif '21211' in error_str or 'invalid' in error_str.lower():
                return SendResult(ok=False, channel=self.name,
                                  message=t('verifier.twilio_invalid', lang))
            elif '21614' in error_str or 'not a valid' in error_str.lower():
                return SendResult(ok=False, channel=self.name,
                                  message=t('verifier.twilio_not_mobile', lang))
            else:
                return SendResult(ok=False, channel=self.name,
                                  message=t('verifier.sms_retry', lang))


class TwilioWhatsAppVerifier(OTPChannel):
    """
    Envía WhatsApp reales via Twilio. Requiere TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN,
    TWILIO_WHATSAPP_FROM y TWILIO_WHATSAPP_CONTENT_SID configurados en el entorno.
    Usa plantillas de WhatsApp aprobadas por Meta (content_sid).
    """

    name = "whatsapp"

    def __init__(self, account_sid, auth_token, from_number, content_sid, audit_fn=None):
        from twilio.rest import Client
        self._client = Client(account_sid, auth_token)
        self._from = f"whatsapp:{from_number}"
        self._content_sid = content_sid
        self._audit = audit_fn

    def send(self, phone_e164, code, ttl_minutes=10, username=None):
        lang = get_language()
        try:
            to_number = f"whatsapp:{phone_e164}"
            import json
            variables = {"1": code, "2": f"{ttl_minutes}"}
            if username:
                variables["3"] = username
            content_variables = json.dumps(variables)

            message = self._client.messages.create(
                from_=self._from,
                content_sid=self._content_sid,
                content_variables=content_variables,
                to=to_number
            )
            print(f"\n[TWILIO WHATSAPP] -> {phone_e164} | SID: {message.sid}")
            if self._audit:
                self._audit("OTP enviado por WhatsApp (Twilio)",
                            f"phone_hash={hash_phone_digits(phone_e164)} channel=whatsapp sid={message.sid} ttl={ttl_minutes}m")
            return SendResult(ok=True, channel=self.name,
                              message=t('verifier.wa_sent', lang))
        except Exception as e:
            error_str = str(e)
            logger.exception('[TWILIO WHATSAPP ERROR] -> %s', phone_e164)

            if '21608' in error_str or 'unverified' in error_str.lower():
                return SendResult(ok=False, channel=self.name,
                                  message=t('verifier.twilio_trial', lang))
            elif '21211' in error_str or 'invalid' in error_str.lower():
                return SendResult(ok=False, channel=self.name,
                                  message=t('verifier.twilio_invalid', lang))
            elif '63030' in error_str or 'template' in error_str.lower():
                return SendResult(ok=False, channel=self.name,
                                  message=t('verifier.wa_template_missing', lang))
            else:
                return SendResult(ok=False, channel=self.name,
                                  message=t('verifier.wa_retry', lang))


class VerifierRouter:
    """
    Selecciona el canal según la preferencia del usuario y la disponibilidad
    técnica del número. Fallback automático: WhatsApp -> SMS.
    """

    def __init__(self, sms_verifier: OTPChannel, whatsapp_verifier: OTPChannel, is_whatsapp_capable_fn=None):
        self._sms = sms_verifier
        self._whatsapp = whatsapp_verifier
        self._is_wa = is_whatsapp_capable_fn or (lambda p: False)

    def send_otp(self, phone_e164: str, code: str, preferred_channel: str = "auto",
                 ttl_minutes: int = 10, username: str = None) -> SendResult:
        """
        preferred_channel: 'sms' | 'whatsapp' | 'auto'.
        En 'auto', intenta WhatsApp si el número es WhatsApp-capable, si no SMS.
        username: se incluye como {{3}} en el template de WhatsApp cuando está presente.
        """
        channel = (preferred_channel or "auto").lower()
        if channel == "whatsapp":
            return self._whatsapp.send(phone_e164, code, ttl_minutes, username=username)
        if channel == "sms":
            return self._sms.send(phone_e164, code, ttl_minutes)

        if self._is_wa(phone_e164):
            return self._whatsapp.send(phone_e164, code, ttl_minutes, username=username)
        return self._sms.send(phone_e164, code, ttl_minutes)


_default_router: Optional[VerifierRouter] = None


def get_default_router() -> VerifierRouter:
    """
    Singleton lazy: el primer acceso instancia los verificadores.
    Si TWILIO_SIMULATE=true, usa verificadores simulados aunque haya credenciales.
    Si TWILIO_ACCOUNT_SID está configurado y no hay simulate, usa Twilio real.
    Si no, usa verificadores simulados (fallback para desarrollo).
    """
    global _default_router
    if _default_router is None:
        from utils import log_action, is_whatsapp_capable
        import config
        try:
            from flask import current_app
            debug = bool(current_app.debug)
        except Exception:
            debug = False

        use_real = not config.TWILIO_SIMULATE

        if use_real and config.TWILIO_ACCOUNT_SID and config.TWILIO_AUTH_TOKEN and config.TWILIO_PHONE_NUMBER:
            sms_verifier = TwilioSmsVerifier(
                config.TWILIO_ACCOUNT_SID,
                config.TWILIO_AUTH_TOKEN,
                config.TWILIO_PHONE_NUMBER,
                audit_fn=log_action
            )
        else:
            sms_verifier = SmsSimulatedVerifier(audit_fn=log_action)

        if use_real and config.TWILIO_ACCOUNT_SID and config.TWILIO_AUTH_TOKEN and config.TWILIO_WHATSAPP_FROM and (config.TWILIO_WHATSAPP_BUTTON_CONTENT_SID or config.TWILIO_WHATSAPP_CONTENT_SID):
            content_sid = config.TWILIO_WHATSAPP_BUTTON_CONTENT_SID or config.TWILIO_WHATSAPP_CONTENT_SID
            whatsapp_verifier = TwilioWhatsAppVerifier(
                config.TWILIO_ACCOUNT_SID,
                config.TWILIO_AUTH_TOKEN,
                config.TWILIO_WHATSAPP_FROM,
                content_sid,
                audit_fn=log_action
            )
        else:
            whatsapp_verifier = WhatsAppSimulatedVerifier(
                audit_fn=log_action,
                include_deep_link=debug,
            )

        _default_router = VerifierRouter(
            sms_verifier=sms_verifier,
            whatsapp_verifier=whatsapp_verifier,
            is_whatsapp_capable_fn=is_whatsapp_capable,
        )
    return _default_router


def reset_default_router():
    """Útil para tests que necesitan resetear el singleton."""
    global _default_router
    _default_router = None
