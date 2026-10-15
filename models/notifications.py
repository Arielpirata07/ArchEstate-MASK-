import logging

from .base import get_db_connection

logger = logging.getLogger(__name__)


def get_user_notifications(user_id: int, limit: int = 20, unread_only: bool = False) -> list:
    conn = get_db_connection()
    try:
        query = '''
            SELECT n.*, actor.username AS actor_username
            FROM notifications n
            LEFT JOIN users actor ON n.actor_id = actor.id
            WHERE n.user_id = ?
        '''
        params = [user_id]
        if unread_only:
            query += ' AND n.is_read = 0'
        query += ' ORDER BY n.created_at DESC LIMIT ?'
        params.append(limit)
        rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()



def get_unread_notification_count(user_id: int) -> int:
    conn = get_db_connection()
    try:
        row = conn.execute(
            'SELECT COUNT(*) as cnt FROM notifications WHERE user_id = ? AND is_read = 0',
            (user_id,)
        ).fetchone()
        return row['cnt'] if row else 0
    finally:
        conn.close()



def mark_notification_read(notification_id: int, user_id: int) -> bool:
    conn = get_db_connection()
    try:
        cursor = conn.execute(
            'UPDATE notifications SET is_read = 1 WHERE id = ? AND user_id = ?',
            (notification_id, user_id)
        )
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()



def mark_all_notifications_read(user_id: int) -> bool:
    conn = get_db_connection()
    try:
        conn.execute(
            'UPDATE notifications SET is_read = 1 WHERE user_id = ? AND is_read = 0',
            (user_id,)
        )
        conn.commit()
        return True
    finally:
        conn.close()



def delete_notification(notification_id: int, user_id: int) -> bool:
    conn = get_db_connection()
    try:
        cursor = conn.execute(
            'DELETE FROM notifications WHERE id = ? AND user_id = ?',
            (notification_id, user_id)
        )
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()



def delete_read_notifications(user_id: int) -> int:
    conn = get_db_connection()
    try:
        cursor = conn.execute(
            'DELETE FROM notifications WHERE user_id = ? AND is_read = 1',
            (user_id,)
        )
        conn.commit()
        return cursor.rowcount
    finally:
        conn.close()



def get_all_user_notifications(user_id: int, page: int = 1, per_page: int = 20) -> dict:
    conn = get_db_connection()
    try:
        count_row = conn.execute(
            'SELECT COUNT(*) as cnt FROM notifications WHERE user_id = ?',
            (user_id,)
        ).fetchone()
        total = count_row['cnt'] if count_row else 0
        pages = max(1, -(-total // per_page))
        offset = (page - 1) * per_page
        rows = conn.execute('''
            SELECT n.*, actor.username AS actor_username
            FROM notifications n
            LEFT JOIN users actor ON n.actor_id = actor.id
            WHERE n.user_id = ?
            ORDER BY n.created_at DESC
            LIMIT ? OFFSET ?
        ''', (user_id, per_page, offset)).fetchall()
        return {'items': [dict(r) for r in rows], 'total': total, 'page': page, 'pages': pages}
    finally:
        conn.close()



def get_notifications_sent_by(actor_id: int, page: int = 1, per_page: int = 20, search: str = '') -> dict:
    conn = get_db_connection()
    try:
        params = [actor_id]
        search_clause = ''
        if search:
            search_clause = ' AND u.username LIKE ?'
            params.append(f'%{search}%')
        count_row = conn.execute(
            'SELECT COUNT(*) as cnt FROM notifications n JOIN users u ON n.user_id = u.id WHERE n.actor_id = ?' + search_clause,
            params
        ).fetchone()
        total = count_row['cnt'] if count_row else 0
        pages = max(1, -(-total // per_page))
        offset = (page - 1) * per_page
        query_params = params + [per_page, offset]
        rows = conn.execute('''
            SELECT n.*, u.username AS recipient_username
            FROM notifications n
            JOIN users u ON n.user_id = u.id
            WHERE n.actor_id = ?''' + search_clause + '''
            ORDER BY n.created_at DESC
            LIMIT ? OFFSET ?
        ''', query_params).fetchall()
        return {'items': [dict(r) for r in rows], 'total': total, 'page': page, 'pages': pages}
    finally:
        conn.close()



