"""
Capa de abstracción para el envío de OTP de verificación de teléfono.

Hoy: dos implementaciones simuladas (SmsSimulatedVerifier, WhatsAppSimulatedVerifier)
que sólo registran el envío en consola + audit log + consent_log.

Mañana: enchufar Twilio/360dialog/Meta Cloud API creando nuevas clases
(por ejemplo TwilioSmsVerifier, MetaWhatsAppVerifier) que respeten la
misma interfaz OTPChannel.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional

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
    def send(self, phone_e164: str, code: str, ttl_minutes: int = 10) -> SendResult:
        """
        Envía un OTP al número (en formato E.164) y devuelve un SendResult.
        No debe lanzar excepciones: fallos deben reflejarse en ok=False.
        """


class SmsSimulatedVerifier(OTPChannel):
    """Simula el envío de un SMS. Imprime en consola y registra en audit_log."""

    name = "sms"

    def __init__(self, audit_fn=None):
        self._audit = audit_fn

    def send(self, phone_e164, code, ttl_minutes=10):
        try:
            print(f"\n[SMS SIMULADO] -> {phone_e164}")
            print(f"[SMS SIMULADO] Codigo: {code} (valido {ttl_minutes} min)\n")
            if self._audit:
                self._audit("OTP enviado por SMS", f"phone_hash={hash_phone_digits(phone_e164)} channel=sms ttl={ttl_minutes}m")
            return SendResult(ok=True, channel=self.name,
                              message=f"Codigo enviado por SMS a {phone_e164}")
        except Exception as e:
            return SendResult(ok=False, channel=self.name,
                              message=f"Error al enviar SMS: {e}")


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

    def send(self, phone_e164, code, ttl_minutes=10):
        try:
            from urllib.parse import quote_plus
            digits = phone_e164.lstrip('+')
            text = quote_plus(f"Tu codigo de verificacion de ArchEstate es: {code} (valido {ttl_minutes} min)")
            link = f"{self._base_url}/{digits}?text={text}"
            print(f"\n[WHATSAPP SIMULADO] -> {phone_e164}")
            print(f"[WHATSAPP SIMULADO] Link wa.me con codigo prellenado (no enviado): {link}\n")
            if self._audit:
                self._audit("OTP enviado por WhatsApp",
                            f"phone_hash={hash_phone_digits(phone_e164)} channel=whatsapp ttl={ttl_minutes}m")
            meta = {"deep_link": link} if self._include_deep_link else None
            return SendResult(ok=True, channel=self.name,
                              message="Codigo enviado por WhatsApp",
                              meta=meta)
        except Exception as e:
            return SendResult(ok=False, channel=self.name,
                              message=f"Error al enviar WhatsApp: {e}")


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

    def send(self, phone_e164, code, ttl_minutes=10):
        try:
            body = f"Tu codigo de verificacion de ArchEstate es: {code} (valido {ttl_minutes} min)"
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
                              message=f"Codigo enviado por SMS a {phone_e164}")
        except Exception as e:
            error_str = str(e)
            print(f"\n[TWILIO SMS ERROR] -> {phone_e164} | Error: {error_str}")

            if '21608' in error_str or 'unverified' in error_str.lower():
                return SendResult(ok=False, channel=self.name,
                                  message="Tu cuenta de Twilio es de prueba. Verificá el número en twilio.com o comprá un número Twilio.")
            elif '21211' in error_str or 'invalid' in error_str.lower():
                return SendResult(ok=False, channel=self.name,
                                  message="El número de teléfono no es válido para Twilio.")
            elif '21614' in error_str or 'not a valid' in error_str.lower():
                return SendResult(ok=False, channel=self.name,
                                  message="El número no es un celular válido para SMS.")
            else:
                return SendResult(ok=False, channel=self.name,
                                  message="Error al enviar SMS. Intentá de nuevo.")


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

    def send(self, phone_e164, code, ttl_minutes=10):
        try:
            to_number = f"whatsapp:{phone_e164}"
            import json
            content_variables = json.dumps({"1": code, "2": f"{ttl_minutes}"})

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
                              message="Codigo enviado por WhatsApp")
        except Exception as e:
            error_str = str(e)
            print(f"\n[TWILIO WHATSAPP ERROR] -> {phone_e164} | Error: {error_str}")

            if '21608' in error_str or 'unverified' in error_str.lower():
                return SendResult(ok=False, channel=self.name,
                                  message="Tu cuenta de Twilio es de prueba. Verificá el número en twilio.com o comprá un número Twilio.")
            elif '21211' in error_str or 'invalid' in error_str.lower():
                return SendResult(ok=False, channel=self.name,
                                  message="El número de teléfono no es válido para Twilio.")
            elif '63030' in error_str or 'template' in error_str.lower():
                return SendResult(ok=False, channel=self.name,
                                  message="La plantilla de WhatsApp no está configurada. Contactá al administrador.")
            else:
                return SendResult(ok=False, channel=self.name,
                                  message="Error al enviar WhatsApp. Intentá de nuevo.")


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
                 ttl_minutes: int = 10) -> SendResult:
        """
        preferred_channel: 'sms' | 'whatsapp' | 'auto'.
        En 'auto', intenta WhatsApp si el número es WhatsApp-capable, si no SMS.
        """
        channel = (preferred_channel or "auto").lower()
        if channel == "whatsapp":
            return self._whatsapp.send(phone_e164, code, ttl_minutes)
        if channel == "sms":
            return self._sms.send(phone_e164, code, ttl_minutes)

        if self._is_wa(phone_e164):
            return self._whatsapp.send(phone_e164, code, ttl_minutes)
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

        if use_real and config.TWILIO_ACCOUNT_SID and config.TWILIO_AUTH_TOKEN and config.TWILIO_WHATSAPP_FROM and config.TWILIO_WHATSAPP_CONTENT_SID:
            whatsapp_verifier = TwilioWhatsAppVerifier(
                config.TWILIO_ACCOUNT_SID,
                config.TWILIO_AUTH_TOKEN,
                config.TWILIO_WHATSAPP_FROM,
                config.TWILIO_WHATSAPP_CONTENT_SID,
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
