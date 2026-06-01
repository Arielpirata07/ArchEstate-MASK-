"""
Tests para el VerifierRouter y los canales OTP simulados.
"""

import pytest
from unittest.mock import patch, MagicMock

from services import verifier
from services.verifier import (
    OTPChannel,
    SendResult,
    SmsSimulatedVerifier,
    WhatsAppSimulatedVerifier,
    VerifierRouter,
    get_default_router,
    reset_default_router,
)


@pytest.fixture(autouse=True)
def _reset_singleton():
    reset_default_router()
    yield
    reset_default_router()


def test_sms_simulated_returns_ok(capsys):
    audit = MagicMock()
    v = SmsSimulatedVerifier(audit_fn=audit)
    res = v.send("+5491144445555", "123456", ttl_minutes=10)
    assert res.ok is True
    assert res.channel == "sms"
    assert "5491144445555" in res.message
    audit.assert_called_once()


def test_sms_simulated_prints_to_console(capsys):
    v = SmsSimulatedVerifier()
    v.send("+5491144445555", "123456")
    captured = capsys.readouterr()
    assert "[SMS SIMULADO]" in captured.out
    assert "123456" in captured.out


def test_whatsapp_simulated_returns_ok_with_deep_link():
    audit = MagicMock()
    v = WhatsAppSimulatedVerifier(audit_fn=audit)
    res = v.send("+5491144445555", "654321", ttl_minutes=10)
    assert res.ok is True
    assert res.channel == "whatsapp"
    assert res.meta is not None
    assert res.meta["deep_link"].startswith("https://wa.me/5491144445555?text=")
    assert "654321" in res.meta["deep_link"]
    audit.assert_called_once()


def test_whatsapp_simulated_url_encodes_otp():
    v = WhatsAppSimulatedVerifier()
    res = v.send("+5491144445555", "111222")
    from urllib.parse import urlparse, parse_qs
    parsed = urlparse(res.meta["deep_link"])
    qs = parse_qs(parsed.query)
    assert "111222" in qs["text"][0]


def test_router_explicit_sms():
    sms = MagicMock(spec=OTPChannel)
    sms.name = "sms"
    sms.send.return_value = SendResult(ok=True, channel="sms", message="ok")
    wa = MagicMock(spec=OTPChannel)
    wa.name = "whatsapp"
    router = VerifierRouter(sms_verifier=sms, whatsapp_verifier=wa)
    res = router.send_otp("+5491144445555", "123", preferred_channel="sms")
    sms.send.assert_called_once()
    wa.send.assert_not_called()
    assert res.channel == "sms"


def test_router_explicit_whatsapp():
    sms = MagicMock(spec=OTPChannel)
    sms.name = "sms"
    wa = MagicMock(spec=OTPChannel)
    wa.name = "whatsapp"
    wa.send.return_value = SendResult(ok=True, channel="whatsapp", message="ok")
    router = VerifierRouter(sms_verifier=sms, whatsapp_verifier=wa)
    res = router.send_otp("+5491144445555", "123", preferred_channel="whatsapp")
    wa.send.assert_called_once()
    sms.send.assert_not_called()
    assert res.channel == "whatsapp"


def test_router_auto_uses_whatsapp_when_capable():
    sms = MagicMock(spec=OTPChannel)
    sms.name = "sms"
    sms.send.return_value = SendResult(ok=True, channel="sms", message="ok")
    wa = MagicMock(spec=OTPChannel)
    wa.name = "whatsapp"
    wa.send.return_value = SendResult(ok=True, channel="whatsapp", message="ok")
    router = VerifierRouter(
        sms_verifier=sms, whatsapp_verifier=wa,
        is_whatsapp_capable_fn=lambda p: True
    )
    res = router.send_otp("+5491144445555", "123", preferred_channel="auto")
    wa.send.assert_called_once()
    sms.send.assert_not_called()
    assert res.channel == "whatsapp"


def test_router_auto_falls_back_to_sms_when_not_capable():
    sms = MagicMock(spec=OTPChannel)
    sms.name = "sms"
    sms.send.return_value = SendResult(ok=True, channel="sms", message="ok")
    wa = MagicMock(spec=OTPChannel)
    wa.name = "whatsapp"
    router = VerifierRouter(
        sms_verifier=sms, whatsapp_verifier=wa,
        is_whatsapp_capable_fn=lambda p: False
    )
    res = router.send_otp("+5491144445555", "123", preferred_channel="auto")
    sms.send.assert_called_once()
    wa.send.assert_not_called()
    assert res.channel == "sms"


def test_router_handles_send_failure_gracefully():
    sms = MagicMock(spec=OTPChannel)
    sms.name = "sms"
    sms.send.return_value = SendResult(ok=False, channel="sms", message="error")
    wa = MagicMock(spec=OTPChannel)
    wa.name = "whatsapp"
    wa.send.return_value = SendResult(ok=False, channel="whatsapp", message="boom")
    router = VerifierRouter(
        sms_verifier=sms, whatsapp_verifier=wa,
        is_whatsapp_capable_fn=lambda p: True
    )
    res = router.send_otp("+5491144445555", "123", preferred_channel="whatsapp")
    assert res.ok is False
    assert res.channel == "whatsapp"
    assert res.message == "boom"


def test_default_router_is_singleton():
    r1 = get_default_router()
    r2 = get_default_router()
    assert r1 is r2


def test_default_router_uses_real_phonenumbers_for_fallback():
    """El router por defecto debe usar utils.is_whatsapp_capable (phonenumbers)."""
    from utils import is_whatsapp_capable
    router = get_default_router()
    assert router._is_wa is is_whatsapp_capable
