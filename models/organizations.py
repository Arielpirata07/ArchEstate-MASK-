import logging

from .base import get_db_connection

logger = logging.getLogger(__name__)


def slugify(text):
    import re as _re
    import unicodedata as _ud
    normalized = _ud.normalize('NFKD', (text or '').lower().strip())
    ascii_text = normalized.encode('ascii', 'ignore').decode('ascii')
    slug = _re.sub(r'[^\w\s-]', '', ascii_text)
    slug = _re.sub(r'[-\s]+', '-', slug)
    slug = slug.strip('-')
    if not slug:
        slug = 'org'
    return slug



def _unique_slug(base_slug, exclude_id=None):
    conn = get_db_connection()
    try:
        slug = base_slug
        counter = 2
        while True:
            existing = conn.execute(
                'SELECT id FROM organizations WHERE slug = ?' + (' AND id != ?' if exclude_id else ''),
                (slug, exclude_id) if exclude_id else (slug,)
            ).fetchone()
            if not existing:
                return slug
            slug = f'{base_slug}-{counter}'
            counter += 1
    finally:
        conn.close()



def get_organizations():
    conn = get_db_connection()
    try:
        rows = conn.execute('''
            SELECT o.*,
                   (SELECT COUNT(*) FROM org_members m WHERE m.org_id = o.id) AS member_count,
                   (SELECT COUNT(*) FROM leads l WHERE l.org_id = o.id) AS lead_count
            FROM organizations o
            ORDER BY o.name
        ''').fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()



def get_organization_by_id(org_id):
    conn = get_db_connection()
    try:
        row = conn.execute('SELECT * FROM organizations WHERE id = ?', (org_id,)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()



def get_organization_by_slug(slug):
    conn = get_db_connection()
    try:
        row = conn.execute('SELECT * FROM organizations WHERE slug = ?', (slug,)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()



def create_organization(name, description='', slug=None):
    base_slug = slugify(slug) if slug else slugify(name)
    if slug:
        existing = get_organization_by_slug(base_slug)
        if existing:
            raise ValueError('duplicate slug')
    slug = _unique_slug(base_slug)
    conn = get_db_connection()
    try:
        cursor = conn.execute(
            'INSERT INTO organizations (name, slug, description) VALUES (?, ?, ?)',
            (name, slug, description)
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()



def update_organization(org_id, data):
    allowed = {'name', 'description', 'is_active'}
    filtered = {k: v for k, v in data.items() if k in allowed}
    if not filtered:
        return False
    conn = get_db_connection()
    try:
        if 'name' in filtered:
            base_slug = slugify(filtered['name'])
            filtered['slug'] = _unique_slug(base_slug, exclude_id=org_id)
        set_clause = ', '.join(f'{k} = ?' for k in filtered.keys())
        values = list(filtered.values()) + [org_id]
        conn.execute(f'UPDATE organizations SET {set_clause} WHERE id = ?', values)
        conn.commit()
        return True
    except Exception:
        logger.exception('update_organization failed for org_id=%s', org_id)
        return False
    finally:
        conn.close()



def deactivate_organization(org_id):
    conn = get_db_connection()
    try:
        conn.execute('UPDATE organizations SET is_active = 0 WHERE id = ?', (org_id,))
        conn.execute('DELETE FROM org_members WHERE org_id = ?', (org_id,))
        conn.execute('UPDATE professionals SET org_id = NULL WHERE org_id = ?', (org_id,))
        conn.execute('UPDATE leads SET org_id = NULL WHERE org_id = ?', (org_id,))
        conn.commit()
        return True
    except Exception:
        logger.exception('deactivate_organization failed for org_id=%s', org_id)
        conn.rollback()
        return False
    finally:
        conn.close()



def delete_organization(org_id):
    conn = get_db_connection()
    try:
        conn.execute('DELETE FROM org_members WHERE org_id = ?', (org_id,))
        conn.execute('UPDATE professionals SET org_id = NULL WHERE org_id = ?', (org_id,))
        conn.execute('UPDATE leads SET org_id = NULL WHERE org_id = ?', (org_id,))
        conn.execute('DELETE FROM organizations WHERE id = ?', (org_id,))
        conn.commit()
        return True
    except Exception:
        logger.exception('delete_organization failed for org_id=%s', org_id)
        conn.rollback()
        return False
    finally:
        conn.close()



def set_professional_organization(professional_user_id, org_id):
    conn = get_db_connection()
    try:
        if org_id is not None:
            org = conn.execute('SELECT id, is_active FROM organizations WHERE id = ?', (org_id,)).fetchone()
            if not org or not org['is_active']:
                return False
        conn.execute('UPDATE professionals SET org_id = ? WHERE user_id = ?', (org_id, professional_user_id))
        if org_id is None:
            conn.execute('DELETE FROM org_members WHERE user_id = ?', (professional_user_id,))
        else:
            conn.execute(
                'INSERT OR IGNORE INTO org_members (org_id, user_id, role) VALUES (?, ?, ?)',
                (org_id, professional_user_id, 'member')
            )
        conn.commit()
        return True
    except Exception:
        logger.exception('set_professional_organization failed for user_id=%s', professional_user_id)
        conn.rollback()
        return False
    finally:
        conn.close()



def set_lead_organization(lead_id, org_id):
    conn = get_db_connection()
    try:
        if org_id is not None:
            org = conn.execute('SELECT id, is_active FROM organizations WHERE id = ?', (org_id,)).fetchone()
            if not org or not org['is_active']:
                return False
        conn.execute('UPDATE leads SET org_id = ? WHERE id = ?', (org_id, lead_id))
        conn.commit()
        return True
    except Exception:
        logger.exception('set_lead_organization failed for lead_id=%s', lead_id)
        conn.rollback()
        return False
    finally:
        conn.close()



ORG_ROLES = ('owner', 'admin', 'member')




def get_org_members(org_id):
    conn = get_db_connection()
    try:
        rows = conn.execute('''
            SELECT m.user_id, m.role, m.joined_at, u.username, u.email
            FROM org_members m JOIN users u ON u.id = m.user_id
            WHERE m.org_id = ? ORDER BY m.joined_at
        ''', (org_id,)).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()



def add_org_member(org_id, user_id, role='member'):
    if role not in ORG_ROLES:
        return False
    conn = get_db_connection()
    try:
        org = conn.execute('SELECT id, is_active FROM organizations WHERE id = ?', (org_id,)).fetchone()
        if not org or not org['is_active']:
            return False
        user = conn.execute('SELECT id FROM users WHERE id = ?', (user_id,)).fetchone()
        if not user:
            return False
        conn.execute(
            'INSERT OR IGNORE INTO org_members (org_id, user_id, role) VALUES (?, ?, ?)',
            (org_id, user_id, role)
        )
        conn.execute('UPDATE professionals SET org_id = ? WHERE user_id = ?', (org_id, user_id))
        conn.commit()
        return True
    except Exception:
        logger.exception('add_org_member failed org=%s user=%s', org_id, user_id)
        conn.rollback()
        return False
    finally:
        conn.close()



def remove_org_member(org_id, user_id):
    conn = get_db_connection()
    try:
        conn.execute('DELETE FROM org_members WHERE org_id = ? AND user_id = ?', (org_id, user_id))
        conn.execute('UPDATE professionals SET org_id = NULL WHERE user_id = ? AND org_id = ?', (user_id, org_id))
        conn.commit()
        return True
    except Exception:
        logger.exception('remove_org_member failed org=%s user=%s', org_id, user_id)
        conn.rollback()
        return False
    finally:
        conn.close()



def set_member_role(org_id, user_id, role):
    if role not in ORG_ROLES:
        return False
    conn = get_db_connection()
    try:
        cur = conn.execute(
            'UPDATE org_members SET role = ? WHERE org_id = ? AND user_id = ?',
            (role, org_id, user_id)
        )
        conn.commit()
        return cur.rowcount > 0
    except Exception:
        logger.exception('set_member_role failed org=%s user=%s', org_id, user_id)
        conn.rollback()
        return False
    finally:
        conn.close()



def get_user_orgs(user_id):
    conn = get_db_connection()
    try:
        rows = conn.execute('''
            SELECT o.*, m.role FROM org_members m
            JOIN organizations o ON o.id = m.org_id
            WHERE m.user_id = ? AND o.is_active = 1 ORDER BY o.name
        ''', (user_id,)).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()



def get_my_org(user_id):
    orgs = get_user_orgs(user_id)
    if orgs:
        return orgs[0]
    conn = get_db_connection()
    try:
        row = conn.execute('''
            SELECT o.* FROM organizations o
            JOIN professionals p ON p.org_id = o.id
            WHERE p.user_id = ? AND o.is_active = 1
        ''', (user_id,)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()
