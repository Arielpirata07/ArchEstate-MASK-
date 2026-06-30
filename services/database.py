import logging

import config

logger = logging.getLogger(__name__)


class CompatRow:
    def __init__(self, keys, values):
        self._keys = keys
        self._values = values
        self._dict = dict(zip(keys, values))

    def __getitem__(self, key):
        if isinstance(key, (int, slice)):
            return self._values[key]
        return self._dict[key]

    def __getattr__(self, name):
        try:
            return self._dict[name]
        except KeyError:
            raise AttributeError(name)

    def __iter__(self):
        return iter(self._dict.items())

    def keys(self):
        return self._dict.keys()

    def values(self):
        return self._dict.values()

    def get(self, key, default=None):
        if isinstance(key, int):
            try:
                return self._values[key]
            except IndexError:
                return default
        return self._dict.get(key, default)


class _DBCursor:
    def __init__(self, raw_cursor, driver):
        self._raw = raw_cursor
        self._driver = driver
        self.lastrowid = None
        self.rowcount = 0
        self._description = None

    def _columns(self):
        if self._description is None:
            self._description = self._raw.description
        if self._description is None:
            return []
        return [d[0] for d in self._description]

    def _wrap(self, row):
        if row is None:
            return None
        return CompatRow(self._columns(), row)

    def execute(self, sql, params=None):
        if params is None:
            params = ()
        if self._driver == 'postgresql':
            sql = sql.replace('?', '%s')
        self._raw.execute(sql, params)
        self.rowcount = self._raw.rowcount
        self._description = self._raw.description
        if self._driver == 'postgresql' and sql.strip().upper().startswith('INSERT'):
            try:
                self._raw.execute('SELECT LASTVAL()')
                self.lastrowid = self._raw.fetchone()[0]
            except Exception:
                self.lastrowid = None
        elif self._driver == 'sqlite':
            self.lastrowid = self._raw.lastrowid
        return self

    def fetchone(self):
        return self._wrap(self._raw.fetchone())

    def fetchall(self):
        rows = self._raw.fetchall()
        return [self._wrap(r) for r in rows]

    def __iter__(self):
        for row in self._raw:
            yield self._wrap(row)


class DBConnection:
    def __init__(self, raw_conn, driver):
        self._conn = raw_conn
        self._driver = driver

    def execute(self, sql, params=None):
        cursor = self.cursor()
        return cursor.execute(sql, params)

    def commit(self):
        self._conn.commit()

    def rollback(self):
        self._conn.rollback()

    def close(self):
        self._conn.close()

    @property
    def total_changes(self):
        if self._driver == 'sqlite':
            return self._conn.total_changes
        return 0

    def cursor(self):
        raw = self._conn.cursor()
        return _DBCursor(raw, self._driver)


def is_integrity_error(exc):
    cls = type(exc)
    if cls.__module__ == 'sqlite3' and cls.__name__ == 'IntegrityError':
        return True
    if cls.__module__ == 'psycopg2.errors' and cls.__name__ == 'UniqueViolation':
        return True
    return False


def _driver():
    url = config.DATABASE_URL
    if url and url.startswith('postgresql://'):
        return 'postgresql'
    return 'sqlite'


def date_format_sql(column, fmt):
    if _driver() == 'postgresql':
        pg_fmt = fmt.replace('%Y', 'YYYY').replace('%m', 'MM').replace('%d', 'DD')
        return f"to_char({column}, '{pg_fmt}')"
    return f"strftime('{fmt}', {column})"


def now_sql():
    if _driver() == 'postgresql':
        return 'NOW()'
    return "strftime('%Y-%m', 'now')"


def table_columns(table):
    """Return list of column names for a table, works with both SQLite and PostgreSQL."""
    url = config.DATABASE_URL
    if url and url.startswith('postgresql://'):
        import psycopg2
        conn = psycopg2.connect(url)
        try:
            cur = conn.cursor()
            cur.execute(
                "SELECT column_name FROM information_schema.columns WHERE table_name = %s",
                (table,)
            )
            return [r[0] for r in cur.fetchall()]
        finally:
            conn.close()
    else:
        import sqlite3
        conn = sqlite3.connect(config.DATABASE)
        try:
            cur = conn.execute(f"PRAGMA table_info({table})")
            return [r[1] for r in cur.fetchall()]
        finally:
            conn.close()


def get_db_connection():
    url = config.DATABASE_URL

    if url and url.startswith('postgresql://'):
        return _connect_postgresql(url)
    return _connect_sqlite()


def _connect_sqlite():
    import sqlite3
    conn = sqlite3.connect(config.DATABASE)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA journal_mode=WAL')
    conn.execute('PRAGMA busy_timeout=5000')
    return DBConnection(conn, 'sqlite')


def _connect_postgresql(url):
    import psycopg2
    conn = psycopg2.connect(url)
    conn.autocommit = False
    return DBConnection(conn, 'postgresql')
