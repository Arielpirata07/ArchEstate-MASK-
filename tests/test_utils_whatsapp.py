"""
Tests para las utilidades de WhatsApp: normalización E.164, detección de móvil,
construcción de mensajes y URLs wa.me.
"""

import pytest

import utils


@pytest.mark.parametrize("phone,expected_e164", [
    ("+5491144445555", "+5491144445555"),
    ("+54 9 11 4444-5555", "+5491144445555"),
    ("+54 9 11 4444 5555", "+5491144445555"),
    ("+5491144445555",  "+5491144445555"),
    ("5491144445555",   "+5491144445555"),
    ("+59899123456",    "+59899123456"),
    ("+5511987654321",  "+5511987654321"),
    ("+525512345678",   "+525512345678"),
    ("+34612345678",    "+34612345678"),
])
def test_normalize_phone_to_e164_valid(phone, expected_e164):
    assert utils.normalize_phone_to_e164(phone) == expected_e164


@pytest.mark.parametrize("phone", [
    "",
    "abc",
    "123",
    "+",
    "+0",
    "++++",
])
def test_normalize_phone_to_e164_invalid(phone):
    assert utils.normalize_phone_to_e164(phone) == ""


@pytest.mark.parametrize("phone,is_mobile", [
    ("+5491144445555",      True),
    ("+5491144445555",  True),
    ("+5491144440000",      True),
    ("+541144444555",       False),
    ("+541147777777",       False),
    ("+59899123456",        True),
    ("+5511987654321",      True),
    ("+525512345678",       True),
    ("+34612345678",        True),
])
def test_is_mobile_number(phone, is_mobile):
    assert utils.is_mobile_number(phone) is is_mobile


@pytest.mark.parametrize("phone,is_wa", [
    ("+5491144445555",  True),
    ("+541144444555",   False),
    ("+54911invalid",   False),
    ("+59899123456",    True),
    ("+5511987654321",  True),
    ("+34612345678",    True),
    ("",                False),
    (None,              False),
])
def test_is_whatsapp_capable(phone, is_wa):
    assert utils.is_whatsapp_capable(phone) is is_wa


def test_normalize_phone_for_whatsapp_strips_plus():
    digits = utils.normalize_phone_for_whatsapp("+54 9 11 4444-5555")
    assert digits == "5491144445555"
    assert not digits.startswith("+")
    assert " " not in digits and "-" not in digits


def test_normalize_phone_for_whatsapp_invalid_returns_empty():
    assert utils.normalize_phone_for_whatsapp("abc") == ""
    assert utils.normalize_phone_for_whatsapp("") == ""
    assert utils.normalize_phone_for_whatsapp(None) == ""


def test_build_whatsapp_message_full():
    msg = utils.build_whatsapp_message(
        pro_name="Carlos",
        operation="Comprar Propiedad",
        zone="Palermo",
    )
    assert "Carlos" in msg
    assert "Comprar Propiedad" in msg
    assert "Palermo" in msg
    assert "ArchEstate" in msg
    assert msg.endswith("hablar?")


def test_build_whatsapp_message_fallback_partial():
    msg = utils.build_whatsapp_message(pro_name="Ana")
    assert "Ana" in msg
    assert "ArchEstate" in msg
    assert len(msg) > 20
    assert len(msg) < 500


def test_build_whatsapp_message_truncates_very_long_input():
    msg = utils.build_whatsapp_message(
        pro_name="X" * 200,
        operation="Y" * 200,
        zone="Z" * 200,
    )
    assert len(msg) <= 500


def test_build_whatsapp_url_valid():
    url = utils.build_whatsapp_url(
        "+5491144445555",
        pro_name="Pro",
        operation="Comprar",
        zone="Recoleta",
    )
    assert url.startswith("https://wa.me/5491144445555?text=")
    assert "Pro" in url
    assert "Comprar" in url


def test_build_whatsapp_url_invalid_returns_empty():
    assert utils.build_whatsapp_url("+541144444555") == ""
    assert utils.build_whatsapp_url("abc") == ""
    assert utils.build_whatsapp_url("") == ""


def test_build_sms_url_valid():
    url = utils.build_sms_url("+5491144445555", pro_name="Pro")
    assert url.startswith("sms:+5491144445555?body=")


def test_hash_phone_digits_consistent_and_short():
    h1 = utils.hash_phone_digits("5491144445555")
    h2 = utils.hash_phone_digits("5491144445555")
    h3 = utils.hash_phone_digits("541144445555")
    assert h1 == h2
    assert h1 != h3
    assert len(h1) == 16
    assert utils.hash_phone_digits("") == ""


@pytest.mark.parametrize("phone,expected_type", [
    ("+5491144445555", "mobile"),
    ("+541144444555", "fixed"),
    ("+59899123456", "mobile"),
    ("+12125551234", "other"),  # US, type may be fixed_or_mobile or other
    ("", ""),
    (None, ""),
    ("abc", ""),
])
def test_classify_phone_type(phone, expected_type):
    result = utils.classify_phone_type(phone)
    # Solo verificamos que para mobile y fixed sea exacto; para 'other'
    # aceptamos cualquier clasificación que phonenumbers devuelva.
    if expected_type in ("mobile", "fixed", ""):
        assert result == expected_type
    else:
        assert result in ("mobile", "fixed", "fixed_or_mobile", "other")
