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
    Singleton lazy: el primer acceso instancia los verificadores simulados
    con audit_fn = utils.log_action. Tests pueden sobreescribir el módulo.

    El deep_link sólo se expone en modo debug (no producción).
    """
    global _default_router
    if _default_router is None:
        from utils import log_action, is_whatsapp_capable
        try:
            from flask import current_app
            debug = bool(current_app.debug)
        except Exception:
            debug = False
        _default_router = VerifierRouter(
            sms_verifier=SmsSimulatedVerifier(audit_fn=log_action),
            whatsapp_verifier=WhatsAppSimulatedVerifier(
                audit_fn=log_action,
                include_deep_link=debug,
            ),
            is_whatsapp_capable_fn=is_whatsapp_capable,
        )
    return _default_router


def reset_default_router():
    """Útil para tests que necesitan resetear el singleton."""
    global _default_router
    _default_router = None
