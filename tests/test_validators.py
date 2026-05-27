import pytest
import validators


class TestValidateEmail:
    def test_valid_emails(self):
        assert validators.validate_email('user@example.com') == (True, None)
        assert validators.validate_email('test.user@domain.co.uk') == (True, None)
        assert validators.validate_email('user+tag@example.com') == (True, None)
        assert validators.validate_email('a@b.co') == (True, None)

    def test_invalid_emails(self):
        assert validators.validate_email('')[0] is False
        assert validators.validate_email('invalid')[0] is False
        assert validators.validate_email('@example.com')[0] is False
        assert validators.validate_email('user@')[0] is False
        assert validators.validate_email(None)[0] is False
        assert validators.validate_email('a@b')[0] is False
        assert validators.validate_email(123)[0] is False

    def test_double_dot(self):
        assert validators.validate_email('user..name@example.com')[0] is False

    def test_long_email(self):
        local = 'a' * 65
        assert validators.validate_email(f'{local}@example.com')[0] is False

    def test_long_domain(self):
        domain = 'a' * 256
        assert validators.validate_email(f'user@{domain}')[0] is False


class TestValidatePhone:
    def test_valid_argentina_mobile(self):
        assert validators.validate_phone('+5491112345678') == (True, None)
        assert validators.validate_phone('+54 9 11 1234 5678') == (True, None)

    def test_valid_argentina_landline(self):
        assert validators.validate_phone('+541112345678') == (True, None)

    def test_valid_uruguay(self):
        assert validators.validate_phone('+59899123456') == (True, None)

    def test_valid_us(self):
        assert validators.validate_phone('+12125551234') == (True, None)

    def test_valid_spain(self):
        assert validators.validate_phone('+34612345678') == (True, None)

    def test_invalid_phone_too_short(self):
        is_valid, error = validators.validate_phone('+54')
        assert is_valid is False
        assert error is not None

    def test_invalid_phone_no_country_code(self):
        is_valid, error = validators.validate_phone('12345')
        assert is_valid is False

    def test_empty_phone(self):
        assert validators.validate_phone('')[0] is False
        assert validators.validate_phone(None)[0] is False

    def test_phone_impossible_number(self):
        is_valid, error = validators.validate_phone('+54911111111111111111')
        assert is_valid is False

    def test_phone_invalid_for_region(self):
        is_valid, error = validators.validate_phone('+54911111')
        assert is_valid is False

    def test_phone_fallback_no_country_code(self):
        is_valid, error = validators.validate_phone('12345678')
        assert is_valid is True


class TestValidateBudget:
    def test_valid_budget_single(self):
        assert validators.validate_budget(100000) == (True, None)

    def test_valid_budget_range(self):
        assert validators.validate_budget('100000 - 200000') == (True, None)

    def test_zero_budget(self):
        assert validators.validate_budget(0)[0] is False

    def test_negative_budget(self):
        assert validators.validate_budget(-100)[0] is False

    def test_huge_budget(self):
        assert validators.validate_budget(10**15)[0] is False

    def test_none_budget(self):
        assert validators.validate_budget(None)[0] is False


class TestValidateZone:
    def test_valid_zone(self):
        assert validators.validate_zone('Palermo') == (True, None)

    def test_empty_zone(self):
        assert validators.validate_zone('')[0] is False
        assert validators.validate_zone(None)[0] is False

    def test_zone_too_short(self):
        assert validators.validate_zone('a')[0] is False

    def test_zone_too_long(self):
        assert validators.validate_zone('a' * 101)[0] is False


class TestValidateUsername:
    def test_valid_username(self):
        assert validators.validate_username('john_doe') == (True, None)

    def test_username_too_short(self):
        assert validators.validate_username('ab')[0] is False

    def test_username_too_long(self):
        assert validators.validate_username('a' * 31)[0] is False

    def test_username_with_special_chars(self):
        assert validators.validate_username('user name!')[0] is False

    def test_empty_username(self):
        assert validators.validate_username('')[0] is False


class TestValidatePassword:
    def test_valid_password(self):
        assert validators.validate_password('abc123') == (True, None)

    def test_too_short(self):
        assert validators.validate_password('ab1')[0] is False

    def test_no_letters(self):
        assert validators.validate_password('123456')[0] is False

    def test_no_numbers(self):
        assert validators.validate_password('abcdef')[0] is False

    def test_empty_password(self):
        assert validators.validate_password('')[0] is False
        assert validators.validate_password(None)[0] is False


class TestValidatePropertyType:
    def test_valid_types(self):
        for ptype in validators.VALID_PROPERTY_TYPES:
            assert validators.validate_property_type(ptype) == (True, None)

    def test_invalid_type(self):
        assert validators.validate_property_type('castle')[0] is False

    def test_empty_type(self):
        assert validators.validate_property_type('')[0] is False


class TestValidateOperationType:
    def test_valid_types(self):
        for otype in validators.VALID_OPERATION_TYPES:
            assert validators.validate_operation_type(otype) == (True, None)

    def test_invalid_type(self):
        assert validators.validate_operation_type('rent')[0] is False

    def test_empty_type(self):
        assert validators.validate_operation_type('')[0] is False
