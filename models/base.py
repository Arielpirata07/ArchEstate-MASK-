# noodle --queries-> database (sql,all_entities)
# noodle --provides-> routes (orm,queries)
import logging
import threading
import time

import utils  # noqa: F401 (re-exportado para compatibilidad)

logger = logging.getLogger(__name__)


class SimpleTTLCache:
    """Thread-safe in-memory cache with per-key TTL."""

    def __init__(self, ttl_seconds=60):
        self._cache = {}
        self._timestamps = {}
        self._ttl = ttl_seconds
        self._lock = threading.Lock()

    def get(self, key):
        with self._lock:
            if key in self._cache:
                if time.time() - self._timestamps[key] < self._ttl:
                    return self._cache[key]
                del self._cache[key]
                del self._timestamps[key]
        return None

    def set(self, key, value):
        with self._lock:
            self._cache[key] = value
            self._timestamps[key] = time.time()

    def invalidate(self, key):
        with self._lock:
            self._cache.pop(key, None)
            self._timestamps.pop(key, None)

    def invalidate_prefix(self, prefix):
        with self._lock:
            keys_to_del = [k for k in self._cache if k.startswith(prefix)]
            for k in keys_to_del:
                del self._cache[k]
                del self._timestamps[k]


_prefs_cache = SimpleTTLCache(ttl_seconds=60)
_form_options_cache = SimpleTTLCache(ttl_seconds=60)


class DatabaseError(Exception):
    pass


def get_db_connection():
    from services.database import get_db_connection as _get_db
    try:
        from flask import g, has_app_context
        if has_app_context():
            real = getattr(g, '_shared_db_conn', None)
            if real is None:
                real = _get_db()
                g._shared_db_conn = real
            return _GuardedConnection(real)
    except Exception:
        logger.exception('Error al cachear conexión del request')
    try:
        return _get_db()
    except Exception:
        logger.exception('Error al conectar a la base de datos')
        raise DatabaseError('No se pudo conectar a la base de datos')


class _GuardedConnection:
    '''Proxy a la conexión compartida del request: close() es no-op.

    La conexión real se cierra en teardown_appcontext (close_db_connection).
    Así N llamadas en un request reusan 1 conexión sin cambiar callers.
    '''
    def __init__(self, real):
        self._real = real

    def execute(self, sql, params=None):
        return self._real.execute(sql, params)

    def cursor(self):
        return self._real.cursor()

    def commit(self):
        return self._real.commit()

    def rollback(self):
        return self._real.rollback()

    def close(self):
        return None

    @property
    def total_changes(self):
        return self._real.total_changes


