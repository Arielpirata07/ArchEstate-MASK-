import pytest


class TestProfilePhoneUpdate:
    """Test phone update via profile API and stored format."""

    def _update_phone(self, auth_client, phone):
        return auth_client.put('/api/profile/user', json={
            'email': 'test@example.com',
            'phone': phone,
            'first_name': '',
            'last_name': '',
            'bio': '',
        })

    def _get_profile(self, auth_client):
        return auth_client.get('/api/profile/user')

    def test_phone_argentina_landline_prefix_and_space(self, auth_client):
        """+54 221 456-7890 (La Plata landline) stored as-is."""
        resp = self._update_phone(auth_client, '+54 221 456-7890')
        assert resp.status_code == 200

        resp = self._get_profile(auth_client)
        phone = resp.json['user']['phone']
        # El phone se guarda tal cual lo envía el frontend
        assert phone == '+54 221 456-7890'

    def test_phone_argentina_landline_prefix_no_dashes(self, auth_client):
        """+54 221 4567890 (La Plata landline, sin guiones)."""
        resp = self._update_phone(auth_client, '+54 221 4567890')
        assert resp.status_code == 200

        resp = self._get_profile(auth_client)
        assert resp.json['user']['phone'] == '+54 221 4567890'

    def test_phone_argentina_mobile_with_9(self, auth_client):
        """+54 9 11 1234-5678 (CABA mobile con 9)."""
        resp = self._update_phone(auth_client, '+54 9 11 1234-5678')
        assert resp.status_code == 200

        resp = self._get_profile(auth_client)
        assert resp.json['user']['phone'] == '+54 9 11 1234-5678'

    def test_phone_argentina_mobile_9_with_province(self, auth_client):
        """+54 9 221 456-7890 (La Plata mobile con 9 y area)."""
        resp = self._update_phone(auth_client, '+54 9 221 456-7890')
        assert resp.status_code == 200

        resp = self._get_profile(auth_client)
        assert resp.json['user']['phone'] == '+54 9 221 456-7890'

    def test_phone_argentina_caba_landline(self, auth_client):
        """+54 11 4567-8901 (CABA landline)."""
        resp = self._update_phone(auth_client, '+54 11 4567-8901')
        assert resp.status_code == 200

        resp = self._get_profile(auth_client)
        assert resp.json['user']['phone'] == '+54 11 4567-8901'

    def test_phone_uruguay_mobile(self, auth_client):
        """+598 99 123-456 (Uruguay mobile)."""
        resp = self._update_phone(auth_client, '+598 99 123-456')
        assert resp.status_code == 200

        resp = self._get_profile(auth_client)
        assert resp.json['user']['phone'] == '+598 99 123-456'

    def test_phone_us_new_york(self, auth_client):
        """+1 212 456-7890 (US New York)."""
        resp = self._update_phone(auth_client, '+1 212 456-7890')
        assert resp.status_code == 200

        resp = self._get_profile(auth_client)
        assert resp.json['user']['phone'] == '+1 212 456-7890'

    def test_phone_argentina_rosario_landline(self, auth_client):
        """+54 341 456-7890 (Rosario landline)."""
        resp = self._update_phone(auth_client, '+54 341 456-7890')
        assert resp.status_code == 200

        resp = self._get_profile(auth_client)
        assert resp.json['user']['phone'] == '+54 341 456-7890'

    def test_phone_empty_allowed(self, auth_client):
        """Phone vacio debe ser aceptado."""
        resp = self._update_phone(auth_client, '')
        assert resp.status_code == 200

    def test_phone_invalid_rejected(self, auth_client):
        """Phone invalido debe ser rechazado con 400."""
        resp = self._update_phone(auth_client, 'abc')
        assert resp.status_code == 400
        assert 'error' in resp.json
