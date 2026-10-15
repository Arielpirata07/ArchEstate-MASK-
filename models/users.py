import logging

import utils

from .base import get_db_connection

logger = logging.getLogger(__name__)


def get_user_by_id(user_id):
    conn = get_db_connection()
    try:
        user = conn.execute('SELECT id, username, email, phone, hash, role, doc_path, is_active, phone_verified FROM users WHERE id = ?', (user_id,)).fetchone()
        return dict(user) if user else None
    finally:
        conn.close()



def get_user_by_username(username):
    conn = get_db_connection()
    try:
        user = conn.execute('SELECT id, username, email, hash, role, doc_path, is_active FROM users WHERE username = ?', (username,)).fetchone()
        return dict(user) if user else None
    finally:
        conn.close()



def get_user_profile(user_id):
    conn = get_db_connection()
    try:
        row = conn.execute(
            'SELECT u.id, u.username, u.email, u.phone, u.role, u.is_active, u.phone_verified, '
            'u.verification_channel, '
            'up.first_name, up.last_name, up.bio, up.title, up.avatar_path, '
            'up.created_at, up.updated_at '
            'FROM users u LEFT JOIN user_profiles up ON u.id = up.user_id WHERE u.id = ?',
            (user_id,)
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()



ALLOWED_PROFILE_FIELDS = {'first_name', 'last_name', 'bio', 'title', 'avatar_path'}

def update_user_profile(user_id, data):
    conn = get_db_connection()
    try:
        filtered = {k: v for k, v in data.items() if k in ALLOWED_PROFILE_FIELDS}
        if not filtered:
            return False

        existing = conn.execute('SELECT id FROM user_profiles WHERE user_id = ?', (user_id,)).fetchone()
        if existing:
            set_clause = ', '.join(f'{k} = ?' for k in filtered.keys())
            values = list(filtered.values()) + [user_id]
            conn.execute(f'UPDATE user_profiles SET {set_clause}, updated_at = CURRENT_TIMESTAMP WHERE user_id = ?', values)
        else:
            filtered['user_id'] = user_id
            columns = ', '.join(filtered.keys())
            placeholders = ', '.join('?' for _ in filtered)
            values = list(filtered.values())
            conn.execute(f'INSERT INTO user_profiles ({columns}) VALUES ({placeholders})', values)
        conn.commit()
        return True
    except Exception:
        logger.exception('update_user_profile failed for user_id=%s', user_id)
        return False
    finally:
        conn.close()



def update_user_phone_only(user_id, phone):
    """
    Actualiza el teléfono de un usuario con normalización E.164 y
    invalidación condicional de OTP si el número cambió.
    Retorna dict con el resultado de la operación.
    """
    conn = get_db_connection()
    try:
        current = conn.execute(
            'SELECT phone, phone_verified FROM users WHERE id = ?', (user_id,)
        ).fetchone()

        old_phone = current['phone'] if current else ''
        e164 = utils.normalize_phone_to_e164(phone)
        ntype = utils.classify_phone_type(e164) if e164 else ''
        old_e164 = utils.normalize_phone_to_e164(old_phone) if old_phone else ''
        invalidate_otp = bool(e164) and (old_e164 != e164)

        if invalidate_otp:
            conn.execute(
                'UPDATE users SET phone = ?, phone_e164 = ?, phone_number_type = ?, '
                'phone_format_valid = 1, phone_verified = 0, verification_code = \'\', '
                'verification_expires = NULL WHERE id = ?',
                (phone, e164, ntype, user_id)
            )
        else:
            conn.execute(
                'UPDATE users SET phone = ?, phone_e164 = ?, phone_number_type = ? WHERE id = ?',
                (phone, e164, ntype, user_id)
            )
        conn.commit()

        return {
            'success': True,
            'phone': phone,
            'phone_e164': e164,
            'invalidate_otp': invalidate_otp,
            'phone_verified': 0 if invalidate_otp else (current['phone_verified'] if current else 0),
        }
    except Exception:
        logger.exception('update_user_phone_only failed for user_id=%s', user_id)
        return {'success': False}
    finally:
        conn.close()



def update_user_credentials(user_id, email, phone):
    if phone:
        phone_result = update_user_phone_only(user_id, phone)
        if not phone_result['success']:
            return False

    conn = get_db_connection()
    try:
        conn.execute('UPDATE users SET email = ? WHERE id = ?', (email, user_id))
        conn.commit()
        return True
    except Exception:
        return False
    finally:
        conn.close()



def update_user_account(user_id, email, phone, profile_data):
    '''Actualiza credenciales (email/teléfono) + perfil en UNA sola transacción.

    Replica la lógica de update_user_phone_only + update_user_credentials +
    update_user_profile sin conexiones intermedias: o todo se persiste o nada.
    '''
    filtered = {k: v for k, v in (profile_data or {}).items() if k in ALLOWED_PROFILE_FIELDS}
    conn = get_db_connection()
    try:
        if phone:
            current = conn.execute(
                'SELECT phone, phone_verified FROM users WHERE id = ?', (user_id,)
            ).fetchone()
            old_phone = current['phone'] if current else ''
            e164 = utils.normalize_phone_to_e164(phone)
            ntype = utils.classify_phone_type(e164) if e164 else ''
            old_e164 = utils.normalize_phone_to_e164(old_phone) if old_phone else ''
            invalidate_otp = bool(e164) and (old_e164 != e164)
            if invalidate_otp:
                conn.execute(
                    'UPDATE users SET phone = ?, phone_e164 = ?, phone_number_type = ?, '
                    'phone_format_valid = 1, phone_verified = 0, verification_code = \'\', '
                    'verification_expires = NULL WHERE id = ?',
                    (phone, e164, ntype, user_id)
                )
            else:
                conn.execute(
                    'UPDATE users SET phone = ?, phone_e164 = ?, phone_number_type = ? WHERE id = ?',
                    (phone, e164, ntype, user_id)
                )
        conn.execute('UPDATE users SET email = ? WHERE id = ?', (email, user_id))
        if filtered:
            existing = conn.execute('SELECT id FROM user_profiles WHERE user_id = ?', (user_id,)).fetchone()
            if existing:
                set_clause = ', '.join(f'{k} = ?' for k in filtered.keys())
                values = list(filtered.values()) + [user_id]
                conn.execute(f'UPDATE user_profiles SET {set_clause}, updated_at = CURRENT_TIMESTAMP WHERE user_id = ?', values)
            else:
                filtered['user_id'] = user_id
                columns = ', '.join(filtered.keys())
                placeholders = ', '.join('?' for _ in filtered)
                conn.execute(f'INSERT INTO user_profiles ({columns}) VALUES ({placeholders})', list(filtered.values()))
        conn.commit()
        return True
    except Exception:
        logger.exception('update_user_account failed for user_id=%s', user_id)
        conn.rollback()
        return False
    finally:
        conn.close()



def _ensure_user_profile(user_id):
    conn = get_db_connection()
    try:
        existing = conn.execute('SELECT id FROM user_profiles WHERE user_id = ?', (user_id,)).fetchone()
        if not existing:
            conn.execute('INSERT INTO user_profiles (user_id) VALUES (?)', (user_id,))
            conn.commit()
    except Exception:
        logger.exception('_ensure_user_profile failed for user_id=%s', user_id)
    finally:
        conn.close()



def get_user_avatar_path(user_id):
    conn = get_db_connection()
    try:
        row = conn.execute('SELECT avatar_path FROM user_profiles WHERE user_id = ?', (user_id,)).fetchone()
        return row['avatar_path'] if row and row['avatar_path'] else None
    finally:
        conn.close()



def update_user_avatar(user_id, path):
    _ensure_user_profile(user_id)
    conn = get_db_connection()
    try:
        conn.execute('UPDATE user_profiles SET avatar_path = ? WHERE user_id = ?', (path, user_id))
        conn.commit()
        return True
    except Exception:
        return False
    finally:
        conn.close()



def get_professional_photo_path(user_id):
    conn = get_db_connection()
    try:
        row = conn.execute('SELECT photo_path FROM professional_profiles WHERE user_id = ?', (user_id,)).fetchone()
        return row['photo_path'] if row and row['photo_path'] else None
    finally:
        conn.close()



def delete_user_avatar(user_id):
    conn = get_db_connection()
    try:
        conn.execute("UPDATE user_profiles SET avatar_path = '' WHERE user_id = ?", (user_id,))
        conn.commit()
        return True
    except Exception:
        return False
    finally:
        conn.close()



def get_user_login_history(user_id, limit=20):
    conn = get_db_connection()
    try:
        rows = conn.execute(
            'SELECT * FROM user_login_history WHERE user_id = ? ORDER BY last_active DESC LIMIT ?',
            (user_id, limit)
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()



def delete_login_history_entry(entry_id, user_id):
    conn = get_db_connection()
    try:
        cursor = conn.execute(
            'DELETE FROM user_login_history WHERE id = ? AND user_id = ?',
            (entry_id, user_id)
        )
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()



def get_user_activity(user_id, limit=50):
    conn = get_db_connection()
    try:
        rows = conn.execute(
            'SELECT * FROM audit_log WHERE user_id = ? ORDER BY timestamp DESC LIMIT ?',
            (user_id, limit)
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()



def get_user_by_email(email):
    conn = get_db_connection()
    try:
        user = conn.execute('SELECT id, username, email, hash, role, is_active FROM users WHERE email = ?', (email,)).fetchone()
        return dict(user) if user else None
    finally:
        conn.close()



def create_password_reset_token(user_id, token, expires_at):
    conn = get_db_connection()
    try:
        conn.execute(
            'INSERT INTO password_reset_tokens (user_id, token, expires_at) VALUES (?, ?, ?)',
            (user_id, token, expires_at)
        )
        conn.commit()
        return True
    except Exception:
        logger.exception('Error al crear token de recuperación')
        return False
    finally:
        conn.close()



def validate_password_reset_token(token):
    conn = get_db_connection()
    try:
        row = conn.execute(
            'SELECT id, user_id, expires_at, used FROM password_reset_tokens WHERE token = ?',
            (token,)
        ).fetchone()
        if not row:
            return None
        if row['used']:
            return None
        from datetime import datetime, timezone
        expires = datetime.fromisoformat(row['expires_at'])
        if datetime.now(timezone.utc).replace(tzinfo=None) > expires:
            return None
        return row['user_id']
    finally:
        conn.close()



def mark_password_reset_token_used(token):
    conn = get_db_connection()
    try:
        conn.execute('UPDATE password_reset_tokens SET used = 1 WHERE token = ?', (token,))
        conn.commit()
    finally:
        conn.close()



def update_user_password(user_id, new_hash):
    conn = get_db_connection()
    try:
        conn.execute('UPDATE users SET hash = ? WHERE id = ?', (new_hash, user_id))
        conn.commit()
    finally:
        conn.close()



