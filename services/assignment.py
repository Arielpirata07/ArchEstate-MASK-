import logging

import models
import utils
from services.matching import MIN_MATCH_SCORE, score_lead_for_coverage

logger = logging.getLogger(__name__)


def auto_assign_lead(lead_id: int) -> int | None:
    """
    Asigna un lead al profesional con mejor afinidad, segun su cobertura
    configurada de zonas/especialidades (services.matching.score_lead_for_coverage)
    mas un balanceo por carga de trabajo (-1 por lead en seguimiento).

    Si ningun profesional aprobado tiene una relacion real con las caracteristicas
    del lead (score < MIN_MATCH_SCORE), el lead queda sin asignar a proposito —
    no se fuerza una asignacion arbitraria solo para no dejarlo suelto.

    Devuelve el user_id asignado, o None si quedo sin asignar.
    """
    conn = None
    try:
        conn = models.get_db_connection()
        lead = conn.execute('SELECT * FROM leads WHERE id = ?', (lead_id,)).fetchone()
        if not lead:
            return None

        if lead.get('assigned_to'):
            return lead['assigned_to']

        professionals = conn.execute('''
            SELECT p.user_id, p.name, p.province
            FROM professionals p
            JOIN users u ON p.user_id = u.id
            WHERE p.status = 'approved' AND u.is_active = 1
        ''').fetchall()

        if not professionals:
            return None

        pro_ids = [pro['user_id'] for pro in professionals]
        placeholders = ','.join('?' for _ in pro_ids)
        tracking_rows = conn.execute(
            f'SELECT professional_id, COUNT(*) as cnt FROM lead_tracking WHERE professional_id IN ({placeholders}) GROUP BY professional_id',
            pro_ids
        ).fetchall()
        tracking_counts = {r['professional_id']: r['cnt'] for r in tracking_rows}

        lead_dict = dict(lead)
        best_score = -1
        best_pro = None

        for pro in professionals:
            coverage = models.get_professional_coverage(pro['user_id'])
            score = score_lead_for_coverage(lead_dict, coverage, pro['province'])
            if score < MIN_MATCH_SCORE:
                continue

            tracked = tracking_counts.get(pro['user_id'], 0)
            adjusted_score = score - tracked

            if best_pro is None or adjusted_score > best_score:
                best_score = adjusted_score
                best_pro = pro

        if best_pro:
            conn.execute(
                'UPDATE leads SET assigned_to = ? WHERE id = ?',
                (best_pro['user_id'], lead_id)
            )
            conn.commit()
            utils.log_action(
                'Asignacion automatica lead',
                f'Lead #{lead_id} -> {best_pro["name"]} (score: {best_score})',
                None
            )
            return best_pro['user_id']

        utils.log_action(
            'Asignacion automatica lead',
            f'Lead #{lead_id} sin asignar: ningun profesional matchea sus caracteristicas',
            None
        )
        return None
    except Exception:
        logger.exception('Error en auto_assign_lead')
        return None
    finally:
        if conn:
            conn.close()
