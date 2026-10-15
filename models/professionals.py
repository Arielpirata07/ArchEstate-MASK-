import logging

from .base import get_db_connection

logger = logging.getLogger(__name__)


def get_professional_by_user_id(user_id):
    conn = get_db_connection()
    try:
        pro = conn.execute('SELECT * FROM professionals WHERE user_id = ?', (user_id,)).fetchone()
        return dict(pro) if pro else None
    finally:
        conn.close()



def get_professional_by_name(name):
    conn = get_db_connection()
    try:
        pro = conn.execute('SELECT * FROM professionals WHERE name = ?', (name,)).fetchone()
        return dict(pro) if pro else None
    finally:
        conn.close()



ALLOWED_PROFESSIONAL_FIELDS = {'specialty', 'title', 'province', 'zone', 'country'}

ALLOWED_PROFESSIONAL_PROFILE_FIELDS = {
    'bio_pro', 'experience_years', 'services_offered',
    'portfolio', 'availability', 'social_links',
    'fee_range_min', 'fee_range_max', 'professional_address',
    'photo_path',
}

def update_professional_profile(user_id, data):
    filtered = {k: v for k, v in data.items() if k in ALLOWED_PROFESSIONAL_FIELDS}
    if not filtered:
        return False
    conn = get_db_connection()
    try:
        set_clause = ', '.join(f'{k} = ?' for k in filtered.keys())
        values = list(filtered.values()) + [user_id]
        conn.execute(f'UPDATE professionals SET {set_clause} WHERE user_id = ?', values)
        conn.commit()
        return True
    except Exception:
        logger.exception('update_professional_profile failed for user_id=%s', user_id)
        return False
    finally:
        conn.close()



MAX_COVERAGE_VALUES = 20



def get_professional_coverage(user_id):
    """Devuelve la cobertura de zonas/especialidades configurada por el profesional.

    Si todavia no configuro nada en professional_coverage, cae de vuelta a los
    valores unicos legacy de la tabla professionals (compatibilidad hacia atras).
    'configured' indica si la cobertura viene de la config nueva (True) o del
    fallback legacy (False), para que la UI pueda distinguir "sin configurar".
    """
    conn = get_db_connection()
    try:
        rows = conn.execute(
            'SELECT coverage_type, value FROM professional_coverage WHERE user_id = ? ORDER BY value',
            (user_id,)
        ).fetchall()
        zones = [r['value'] for r in rows if r['coverage_type'] == 'zone']
        specialties = [r['value'] for r in rows if r['coverage_type'] == 'specialty']
        if zones or specialties:
            return {'zones': zones, 'specialties': specialties, 'configured': True}

        pro = conn.execute(
            'SELECT zone, specialty, province FROM professionals WHERE user_id = ?', (user_id,)
        ).fetchone()
        legacy_zones = [pro['zone']] if pro and pro['zone'] else []
        legacy_specialties = [pro['specialty']] if pro and pro['specialty'] else []
        return {'zones': legacy_zones, 'specialties': legacy_specialties, 'configured': False}
    finally:
        conn.close()



def get_professional_coverage_batch(user_ids):
    '''Cobertura de varios profesionales en 2 queries (evita N+1 en auto_assign).

    Replica la lógica de get_professional_coverage (coverage + fallback legacy).
    '''
    user_ids = list(dict.fromkeys(user_ids))
    if not user_ids:
        return {}
    conn = get_db_connection()
    try:
        placeholders = ','.join('?' for _ in user_ids)
        rows = conn.execute(
            f'SELECT user_id, coverage_type, value FROM professional_coverage WHERE user_id IN ({placeholders}) ORDER BY value',
            user_ids
        ).fetchall()
        by_user = {}
        for r in rows:
            entry = by_user.setdefault(r['user_id'], {'zones': [], 'specialties': []})
            if r['coverage_type'] == 'zone':
                entry['zones'].append(r['value'])
            elif r['coverage_type'] == 'specialty':
                entry['specialties'].append(r['value'])
        missing = [uid for uid in user_ids if not by_user.get(uid, {}).get('zones') and not by_user.get(uid, {}).get('specialties')]
        legacy = {}
        if missing:
            placeholders = ','.join('?' for _ in missing)
            for pro in conn.execute(
                f'SELECT user_id, zone, specialty, province FROM professionals WHERE user_id IN ({placeholders})',
                missing
            ).fetchall():
                legacy[pro['user_id']] = pro
        result = {}
        for uid in user_ids:
            entry = by_user.get(uid, {'zones': [], 'specialties': []})
            if entry['zones'] or entry['specialties']:
                result[uid] = {'zones': entry['zones'], 'specialties': entry['specialties'], 'configured': True}
            else:
                pro = legacy.get(uid)
                result[uid] = {
                    'zones': [pro['zone']] if pro and pro['zone'] else [],
                    'specialties': [pro['specialty']] if pro and pro['specialty'] else [],
                    'configured': False,
                }
        return result
    finally:
        conn.close()



def set_professional_coverage(user_id, zones, specialties):
    """Reemplaza por completo la cobertura de zonas/especialidades del profesional."""
    clean_zones = list(dict.fromkeys(z.strip() for z in zones if z and z.strip()))[:MAX_COVERAGE_VALUES]
    clean_specialties = list(dict.fromkeys(s.strip() for s in specialties if s and s.strip()))[:MAX_COVERAGE_VALUES]

    conn = get_db_connection()
    try:
        conn.execute('DELETE FROM professional_coverage WHERE user_id = ?', (user_id,))
        for z in clean_zones:
            conn.execute(
                "INSERT INTO professional_coverage (user_id, coverage_type, value) VALUES (?, 'zone', ?)",
                (user_id, z)
            )
        for s in clean_specialties:
            conn.execute(
                "INSERT INTO professional_coverage (user_id, coverage_type, value) VALUES (?, 'specialty', ?)",
                (user_id, s)
            )
        conn.commit()
        return {'zones': clean_zones, 'specialties': clean_specialties, 'configured': True}
    except Exception:
        logger.exception('set_professional_coverage failed for user_id=%s', user_id)
        conn.rollback()
        return None
    finally:
        conn.close()



def get_professional_full_profile(user_id):
    conn = get_db_connection()
    try:
        row = conn.execute(
            'SELECT p.id as prof_id, p.name, p.license, p.specialty, p.status, p.license_verified, '
            'p.province, p.zone, p.country, '
            'pp.id as pro_profile_id, pp.photo_path, pp.bio_pro, pp.experience_years, '
            'pp.services_offered, pp.portfolio, pp.availability, pp.social_links, '
            'pp.fee_range_min, pp.fee_range_max, pp.professional_address, '
            'pp.created_at, pp.updated_at '
            'FROM professionals p '
            'LEFT JOIN professional_profiles pp ON p.user_id = pp.user_id '
            'WHERE p.user_id = ?',
            (user_id,)
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()



def create_or_update_professional_profile(user_id, data):
    filtered = {k: v for k, v in data.items() if k in ALLOWED_PROFESSIONAL_PROFILE_FIELDS}
    if not filtered:
        return False
    conn = get_db_connection()
    try:
        existing = conn.execute(
            'SELECT id FROM professional_profiles WHERE user_id = ?', (user_id,)
        ).fetchone()
        if existing:
            set_clause = ', '.join(f'{k} = ?' for k in filtered.keys())
            values = list(filtered.values()) + [user_id]
            conn.execute(f'UPDATE professional_profiles SET {set_clause}, updated_at = CURRENT_TIMESTAMP WHERE user_id = ?', values)
        else:
            filtered['user_id'] = user_id
            columns = ', '.join(filtered.keys())
            placeholders = ', '.join('?' for _ in filtered)
            conn.execute(f'INSERT INTO professional_profiles ({columns}) VALUES ({placeholders})', list(filtered.values()))
        conn.commit()
        return True
    except Exception:
        logger.exception('create_or_update_professional_profile failed for user_id=%s', user_id)
        return False
    finally:
        conn.close()



def get_professional_by_license(license_number):
    conn = get_db_connection()
    try:
        pro = conn.execute(
            'SELECT * FROM professionals WHERE license = ?', (license_number,)
        ).fetchone()
        return dict(pro) if pro else None
    finally:
        conn.close()



