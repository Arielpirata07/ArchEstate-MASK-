import pytest


@pytest.fixture
def admin_client(client):
    from models import get_db_connection
    conn = get_db_connection()
    conn.execute("UPDATE users SET role = 'admin', is_active = 1 WHERE username = 'admin'")
    conn.commit()
    conn.close()
    with client.session_transaction() as sess:
        sess['user_id'] = 1
        sess['username'] = 'admin'
        sess['role'] = 'admin'
    return client


class TestAdminAccessibility:
    def test_admin_page_has_viewport_meta(self, admin_client):
        res = admin_client.get('/admin')
        html = res.data.decode()
        assert 'name="viewport"' in html

    def test_admin_page_has_lang_attribute(self, admin_client):
        res = admin_client.get('/admin')
        html = res.data.decode()
        assert 'lang=' in html

    def test_form_options_tab_has_aria_live_region(self, admin_client):
        res = admin_client.get('/admin')
        html = res.data.decode()
        assert 'aria-live="polite"' in html
        assert 'fo-results-count' in html

    def test_form_options_search_has_label(self, admin_client):
        res = admin_client.get('/admin')
        html = res.data.decode()
        assert 'for="fo-search"' in html

    def test_category_filters_have_role_tab(self, admin_client):
        res = admin_client.get('/admin')
        html = res.data.decode()
        assert 'id="category-filters"' in html
        assert 'role="tablist"' in html

    def test_admin_tabs_present(self, admin_client):
        res = admin_client.get('/admin')
        html = res.data.decode()
        assert 'id="tab-dashboard"' in html
        assert 'id="tab-management"' in html
        assert 'id="tab-reports"' in html
        assert 'id="tab-form-options"' in html


class TestAdminResponsive:
    def test_tabs_container_has_flex(self, admin_client):
        res = admin_client.get('/admin')
        html = res.data.decode()
        assert 'flex gap-2' in html

    def test_table_has_overflow_wrapper(self, admin_client):
        res = admin_client.get('/admin')
        html = res.data.decode()
        assert 'overflow-x-auto' in html

    def test_modal_responsive_padding_in_js(self, admin_client):
        res = admin_client.get('/static/js/admin.js', follow_redirects=True)
        js = res.data.decode()
        assert 'px-4 sm:px-6' in js

    def test_modal_has_max_width_md(self, admin_client):
        res = admin_client.get('/static/js/admin.js', follow_redirects=True)
        js = res.data.decode()
        assert 'max-w-md' in js
