import os
import sys
import tempfile
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


@pytest.fixture(scope='session')
def test_db_path():
    fd, path = tempfile.mkstemp(suffix='.db')
    os.close(fd)
    os.environ['SECRET_KEY'] = 'test-secret-key-not-for-production'
    import config
    config.DATABASE = path
    yield path
    if os.path.exists(path):
        os.unlink(path)


@pytest.fixture
def app(test_db_path):
    from factory import create_app
    flask_app = create_app()
    flask_app.config.update({
        'TESTING': True,
        'WTF_CSRF_ENABLED': False,
        'SERVER_NAME': 'localhost',
    })
    with flask_app.app_context():
        from app_setup import init_db
        init_db(flask_app)
    yield flask_app


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def db(app):
    from models import get_db_connection
    conn = get_db_connection()
    yield conn
    conn.close()


@pytest.fixture(autouse=True)
def _clear_rate_limits():
    import rate_limit
    with rate_limit._rate_lock:
        rate_limit._save_store({})

    # Limpiar también el store de rate limits de lead_bp (usa archivo propio)
    import routes.lead_bp as lead_bp
    with lead_bp._rate_lock:
        lead_bp._save_rate_store({})


@pytest.fixture
def auth_client(client, request):
    import uuid
    from werkzeug.security import generate_password_hash
    from models import get_db_connection
    unique = uuid.uuid4().hex[:8]
    username = f'testuser_{unique}'
    conn = get_db_connection()
    cursor = conn.execute(
        'INSERT INTO users (username, email, hash, role, phone, phone_format_valid) VALUES (?, ?, ?, ?, ?, 1)',
        (username, f'{unique}@example.com', generate_password_hash('abc123'), 'client', '+5491112345678')
    )
    user_id = cursor.lastrowid
    conn.commit()
    conn.close()

    with client.session_transaction() as sess:
        sess['user_id'] = user_id
        sess['username'] = username
        sess['role'] = 'client'

    setattr(request.cls, '_test_username', username)
    return client
