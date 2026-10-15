import logging

from .base import get_db_connection

logger = logging.getLogger(__name__)


def get_audit_logs(limit=100):
    conn = get_db_connection()
    try:
        logs = conn.execute('SELECT * FROM audit_log ORDER BY timestamp DESC LIMIT ?', (limit,)).fetchall()
        return [dict(log) for log in logs]
    finally:
        conn.close()



