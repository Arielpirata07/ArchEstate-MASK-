import logging

import models
import utils

logger = logging.getLogger(__name__)


def auto_assign_lead(lead_id: int) -> int | None:
    """
    Assigns a lead to the best-matching professional based on:
    - Specialty match (property_type == specialty) → weight 100
    - Zone match → weight 30
    - Province match → weight 20
    - Workload balance → -1 per tracked lead

    Returns the assigned user_id or None.
    """
    conn = None
    try:
        conn = models.get_db_connection()
        lead = conn.execute('SELECT * FROM leads WHERE id = ?', (lead_id,)).fetchone()
        if not lead:
            return None

        if lead.get('assigned_to'):
            return lead['assigned_to']

        lead_property_type = (lead['property_type'] or '').strip().lower()
        lead_zone = (lead['zone'] or '').strip().lower()
        lead_province = (lead['province'] or '').strip().lower()

        professionals = conn.execute('''
            SELECT p.user_id, p.name, p.specialty, p.province, p.zone
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

        best_score = -999
        best_pro = None

        for pro in professionals:
            score = 0
            pro_specialty = (pro['specialty'] or '').strip().lower()
            pro_zone = (pro['zone'] or '').strip().lower()
            pro_province = (pro['province'] or '').strip().lower()

            if pro_specialty and lead_property_type:
                if pro_specialty == lead_property_type:
                    score += 100
                elif pro_specialty in lead_property_type or lead_property_type in pro_specialty:
                    score += 50

            if pro_zone and lead_zone:
                if pro_zone == lead_zone or pro_zone in lead_zone or lead_zone in pro_zone:
                    score += 30

            if pro_province and lead_province and pro_province == lead_province:
                score += 20

            tracked = tracking_counts.get(pro['user_id'], 0)
            score -= tracked

            if score > best_score:
                best_score = score
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

        return None
    except Exception:
        logger.exception('Error en auto_assign_lead')
        return None
    finally:
        if conn:
            conn.close()
