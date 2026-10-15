# noodle --initializes-> database (schema,migrations,seeds)
# noodle --creates-> database (tables,indexes)
import logging
import os

import config
import models

import db_migrations
import db_schema
import db_seeds

logger = logging.getLogger(__name__)


class FilterOptionsCache(models.SimpleTTLCache):
    """Caché para opciones de filtros de leads. `invalidate()` limpia todo."""

    def invalidate(self):
        with self._lock:
            self._cache.clear()
            self._timestamps.clear()


filter_cache = FilterOptionsCache(ttl_seconds=300)


def get_budget_stats_from_db():
    conn = None
    try:
        conn = models.get_db_connection()
        total_leads = conn.execute('SELECT COUNT(*) FROM leads').fetchone()[0]
        leads_by_budget = conn.execute(
            'SELECT budget, COUNT(*) as count FROM leads GROUP BY budget ORDER BY count DESC'
        ).fetchall()
        leads_by_currency = conn.execute(
            'SELECT currency, COUNT(*) as count FROM leads GROUP BY currency'
        ).fetchall()
        return {
            'total_leads': total_leads,
            'by_budget': [{'label': r['budget'], 'value': r['count']} for r in leads_by_budget],
            'by_currency': [{'label': r['currency'], 'value': r['count']} for r in leads_by_currency],
        }
    finally:
        if conn:
            conn.close()


def init_db(app):
    with app.app_context():
        conn = models.get_db_connection()
        cursor = conn.cursor()

        os.makedirs(config.AVATAR_FOLDER, exist_ok=True)
        os.makedirs(os.path.join('static', 'uploads', 'portfolio'), exist_ok=True)
        os.makedirs(config.UPLOAD_FOLDER, exist_ok=True)

        db_schema.create_tables(cursor)
        db_migrations.apply_migrations(cursor)
        db_seeds.seed_all(cursor)
        conn.commit()
        conn.close()
