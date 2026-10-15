import flask
import pytest

CODES = [400, 403, 404, 409, 410, 413, 429, 500, 502, 503, 504]


@pytest.fixture
def boom_client(app):
    for code in CODES:
        app.add_url_rule(
            f'/boom{code}', f'boom{code}',
            lambda code=code: flask.abort(code),
        )
    return app.test_client()


class TestErrorHandlersHtml:
    @pytest.mark.parametrize('code', CODES)
    def test_html_response(self, boom_client, code):
        resp = boom_client.get(f'/boom{code}')
        assert resp.status_code == code
        assert b'<!DOCTYPE html>' in resp.data or b'<html' in resp.data


class TestErrorHandlersJson:
    @pytest.mark.parametrize('code', CODES)
    def test_json_response(self, boom_client, code):
        resp = boom_client.get(f'/boom{code}', headers={'Accept': 'application/json'})
        assert resp.status_code == code
        data = resp.get_json()
        assert data is not None
        assert data['code']
        assert data['error']


class TestNotFoundRoute:
    def test_unknown_route_404_html(self, client):
        resp = client.get('/ruta-que-no-existe-xyz')
        assert resp.status_code == 404

    def test_unknown_route_404_json(self, client):
        resp = client.get('/ruta-que-no-existe-xyz', headers={'Accept': 'application/json'})
        assert resp.status_code == 404
        assert resp.get_json()['code'] == 'NOT_FOUND'
