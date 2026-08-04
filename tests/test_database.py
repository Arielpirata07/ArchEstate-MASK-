import pytest

import services.database as dbmod


class TestCompatRow:
    def test_getitem_by_key(self):
        row = dbmod.CompatRow(('id', 'name'), (1, 'Ana'))
        assert row['id'] == 1
        assert row['name'] == 'Ana'

    def test_getitem_by_index(self):
        row = dbmod.CompatRow(('id', 'name'), (1, 'Ana'))
        assert row[0] == 1
        assert row[1] == 'Ana'

    def test_getattr(self):
        row = dbmod.CompatRow(('id', 'name'), (1, 'Ana'))
        assert row.name == 'Ana'

    def test_getattr_missing_raises(self):
        row = dbmod.CompatRow(('id',), (1,))
        with pytest.raises(AttributeError):
            row.missing

    def test_get_with_default(self):
        row = dbmod.CompatRow(('id',), (1,))
        assert row.get('missing', 'dflt') == 'dflt'
        assert row.get('id') == 1

    def test_iter_and_keys(self):
        row = dbmod.CompatRow(('id', 'name'), (1, 'Ana'))
        assert set(row.keys()) == {'id', 'name'}
        assert dict(row) == {'id': 1, 'name': 'Ana'}

    def test_slice(self):
        row = dbmod.CompatRow(('a', 'b', 'c'), (1, 2, 3))
        assert row[1:] == (2, 3)


class TestDBConnection:
    def test_execute_fetchone_returns_compat_row(self, db):
        row = db.execute('SELECT id FROM users LIMIT 1')
        assert row.fetchone() is not None

    def test_lastrowid_on_insert(self, db):
        cursor = db.execute(
            'INSERT INTO users (username, email, hash, role) VALUES (?, ?, ?, ?)',
            ('db_test_user', 'db_test@test.com', 'x', 'client')
        )
        db.commit()
        assert isinstance(cursor.lastrowid, int)
        assert cursor.lastrowid > 0

    def test_commit_and_close(self, db):
        db.commit()
        assert db.total_changes >= 0


class TestHelpers:
    def test_table_columns(self):
        cols = dbmod.table_columns('users')
        assert 'id' in cols
        assert 'username' in cols
        assert 'email' in cols

    def test_date_format_sql_sqlite(self):
        sql = dbmod.date_format_sql('timestamp', '%Y-%m')
        assert sql == "strftime('%Y-%m', timestamp)"

    def test_now_sql_sqlite(self):
        assert dbmod.now_sql() == "strftime('%Y-%m', 'now')"

    def test_is_integrity_error_sqlite(self):
        import sqlite3
        assert dbmod.is_integrity_error(sqlite3.IntegrityError('dup'))

    def test_is_integrity_error_false_for_other(self):
        assert not dbmod.is_integrity_error(ValueError('nope'))

    def test_get_db_connection_roundtrip(self):
        conn = dbmod.get_db_connection()
        try:
            row = conn.execute('SELECT 1 AS n').fetchone()
            assert row['n'] == 1
        finally:
            conn.close()
