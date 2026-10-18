"""Aislamiento de buckets de rate limit por endpoint.

Antes la clave del bucket era solo la IP: requests de una ruta (p. ej. /login,
limit=100) llenaban el bucket compartido y disparaban 429 falsos en otra con
límite bajo (send-code, limit=5), aunque esa ruta nunca se hubiera llamado.
"""


class TestRateLimitBucketIsolation:
    def test_login_traffic_does_not_trip_send_code_limit(self, auth_client):
        for _ in range(6):
            assert auth_client.get('/login').status_code != 429

        # 6 requests a /login (limit=100) no deben consumir el cupo de
        # send-code (limit=5): cada endpoint tiene su propio bucket.
        resp = auth_client.post('/api/phone/send-code', content_type='application/json')
        assert resp.status_code == 200

    def test_each_endpoint_limits_independently(self, auth_client):
        # send-code se sigue limitando solo a los 5/min de su propia ruta.
        for _ in range(5):
            resp = auth_client.post('/api/phone/send-code', content_type='application/json')
            assert resp.status_code == 200
        resp = auth_client.post('/api/phone/send-code', content_type='application/json')
        assert resp.status_code == 429
