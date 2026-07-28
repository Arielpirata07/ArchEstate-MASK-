"""
Test de regresión del flujo de login.

Motivación: el usuario reportó que "el login no me permite ingresar como
administrador, me dice que el usuario ya existe". El problema real era
que estaba en /register (no en /login) y el username 'admin' ya existía.

Este test asegura que:
1. /login (no /register) es el endpoint correcto para autenticarse.
2. Las credenciales admin/admin123 permiten el acceso.
3. /register rechaza 'admin' con un mensaje que NO lo confunda con un
   error de login.
4. /admin está protegido sin sesión.
"""
import re

import pytest

import models


class TestLoginFlow:
    """El flujo de login de admin debe funcionar end-to-end."""

    def test_login_page_renders_username_and_password_fields(self, client):
        """/login debe tener los campos correctos (sin phone)."""
        resp = client.get('/login')
        assert resp.status_code == 200
        assert b'name="username"' in resp.data
        assert b'name="password"' in resp.data
        assert b'name="phone"' not in resp.data, \
            "/login no debe tener campo phone"

    def test_login_with_correct_credentials_redirects_to_admin(self, client):
        """admin/admin123 debe redirigir a /admin."""
        resp = client.post('/login', data={
            'username': 'admin',
            'password': 'admin123',
        }, follow_redirects=False)
        assert resp.status_code == 302, \
            f"Login correcto debería redirigir, no devolver {resp.status_code}"
        assert '/admin' in resp.headers.get('Location', ''), \
            f"Debería ir a /admin, fue a {resp.headers.get('Location')}"

    def test_login_with_wrong_password_shows_generic_error(self, client):
        """Contraseña incorrecta → mensaje genérico (NO 'ya está en uso')."""
        resp = client.post('/login', data={
            'username': 'admin',
            'password': 'wrong_password',
        }, follow_redirects=True)
        assert resp.status_code == 200
        body = resp.data.decode('utf-8', errors='ignore').lower()
        # El mensaje NO debe confundir con un error de registro
        assert 'ya está en uso' not in body, \
            "Mensaje 'ya está en uso' NO debe aparecer en /login (es de /register)"
        assert 'ya esta en uso' not in body
        # El mensaje debe mencionar credenciales inválidas
        assert 'credencial' in body or 'inválid' in body or 'invalid' in body

    def test_login_with_nonexistent_user_shows_generic_error(self, client):
        """Usuario inexistente → mismo mensaje genérico (no enumeración)."""
        resp = client.post('/login', data={
            'username': 'no_existe_este_user',
            'password': 'cualquiera',
        }, follow_redirects=True)
        assert resp.status_code == 200
        body = resp.data.decode('utf-8', errors='ignore').lower()
        assert 'credencial' in body or 'inválid' in body

    def test_admin_endpoint_requires_session(self, client):
        """/admin sin sesión debe redirigir a /login."""
        resp = client.get('/admin', follow_redirects=False)
        assert resp.status_code == 302
        assert '/login' in resp.headers.get('Location', '')

    def test_admin_endpoint_accessible_after_login(self, client):
        """Después de login, /admin debe devolver 200."""
        client.post('/login', data={'username': 'admin', 'password': 'admin123'})
        resp = client.get('/admin')
        assert resp.status_code == 200, \
            f"Esperaba 200 después de login, obtuve {resp.status_code}"

    def test_logout_clears_session(self, client):
        """Logout debe invalidar la sesión."""
        client.post('/login', data={'username': 'admin', 'password': 'admin123'})
        # Confirmar que está logueado
        resp = client.get('/admin')
        assert resp.status_code == 200
        # Logout
        client.get('/logout')
        # Ahora /admin debe redirigir
        resp = client.get('/admin', follow_redirects=False)
        assert resp.status_code == 302


class TestRegisterDoesNotConfuseWithLogin:
    """El form de /register debe dejar claro que es para nuevos usuarios."""

    def test_register_with_existing_username_says_ya_esta_en_uso(self, client):
        """/register debe rechazar 'admin' con un mensaje claro."""
        resp = client.post('/register', data={
            'username': 'admin',  # ya existe
            'email': 'otro@example.com',
            'phone': '+5491112345678',
            'password': 'Abc123',
            'role': 'client',
        }, follow_redirects=True)
        assert resp.status_code == 200
        body = resp.data.decode('utf-8', errors='ignore').lower()
        assert 'ya está en uso' in body or 'ya esta en uso' in body, \
            "El mensaje de register debe decir 'ya está en uso'"

    def test_register_page_has_link_to_login(self, client):
        """/register debe ofrecer el camino a /login."""
        resp = client.get('/register')
        assert resp.status_code == 200
        # Verificar que haya un link a login
        body = resp.data.decode('utf-8', errors='ignore')
        assert '/login' in body or 'Ingresar' in body or 'login' in body.lower(), \
            "/register debe tener link a /login para usuarios que ya tienen cuenta"

    def test_register_does_not_accept_admin_role_directly(self, client):
        """El form de /register no debe permitir crear role=admin (escalation)."""
        resp = client.post('/register', data={
            'username': 'newadminuser',
            'email': 'newadmin@example.com',
            'phone': '+5491112345678',
            'password': 'Abc123',
            'role': 'admin',  # intento de privilege escalation
        }, follow_redirects=True)
        # Verificar en la DB que el user no se creó con role=admin
        conn = models.get_db_connection()
        row = conn.execute(
            "SELECT role FROM users WHERE username = ?", ('newadminuser',)
        ).fetchone()
        conn.close()
        if row:
            assert row[0] != 'admin', \
                f"Register NO debe crear users con role=admin. Encontré role={row[0]}"


class TestLoginPageDoesNotLeakInfo:
    """El form de /login no debe filtrar info sobre usuarios existentes."""

    def test_login_error_message_is_same_for_wrong_user_and_wrong_password(self, client):
        """
        Por seguridad, /login debe mostrar el mismo mensaje para:
        - Usuario inexistente
        - Contraseña incorrecta
        Esto previene enumeración de usuarios.
        """
        r1 = client.post('/login', data={'username': 'noexiste123', 'password': 'x'}, follow_redirects=True)
        r2 = client.post('/login', data={'username': 'admin', 'password': 'wrong'}, follow_redirects=True)
        # Extraer solo el mensaje flash (no toda la página)
        flash1 = re.search(rb'role="alert"[^>]*>([^<]+)<', r1.data)
        flash2 = re.search(rb'role="alert"[^>]*>([^<]+)<', r2.data)
        # Ambos deben tener un mensaje
        assert flash1 is not None
        assert flash2 is not None
        # Y deben ser idénticos (mismo mensaje genérico)
        assert flash1.group(1).strip() == flash2.group(1).strip(), \
            f"Mensajes diferentes: {flash1.group(1)!r} vs {flash2.group(1)!r}"
