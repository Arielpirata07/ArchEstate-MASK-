class TestPublicRoutes:
    def test_index_renders(self, client):
        resp = client.get('/')
        assert resp.status_code == 200
        assert b'ArchEstate' in resp.data

    def test_robots_txt(self, client):
        resp = client.get('/robots.txt')
        assert resp.status_code == 200
        assert resp.mimetype == 'text/plain'
        assert 'User-agent: *' in resp.get_data(as_text=True)
        assert 'Disallow: /admin/' in resp.get_data(as_text=True)
        assert 'Sitemap:' in resp.get_data(as_text=True)

    def test_sitemap_xml(self, client):
        resp = client.get('/sitemap.xml')
        assert resp.status_code == 200
        assert 'xml' in resp.mimetype
        body = resp.get_data(as_text=True)
        assert '<urlset' in body
        assert '<loc>' in body

    def test_landing_stats(self, client):
        resp = client.get('/api/landing/stats')
        assert resp.status_code == 200
        data = resp.get_json()
        assert set(data) == {'total_leads', 'total_professionals', 'total_zones', 'leads_this_month'}

    def test_estadisticas(self, client):
        resp = client.get('/estadisticas')
        assert resp.status_code == 200
        assert isinstance(resp.get_json(), dict)

    def test_estadisticas_popup(self, client):
        resp = client.get('/estadisticas-popup')
        assert resp.status_code == 200
        data = resp.get_json()
        assert 'currency_options' in data
        assert 'ARG' in data['currency_options']
