import logging

from .base import get_db_connection

logger = logging.getLogger(__name__)


PIPELINE_STAGES = ['new', 'contacted', 'visit', 'negotiation', 'proposal', 'closed_won', 'closed_lost', 'archived']


PIPELINE_DEFAULT_STAGE = 'new'

# Etapas que implican contacto: al mover un lead a una de ellas se marca
# lead_tracking.contacted = 1 (ver roadmap Fase 1).

PIPELINE_CONTACTED_FROM = 'contacted'



def get_lead_stage(professional_id, lead_id):
    '''Etapa actual de un lead para un profesional. Sin fila → etapa por defecto.'''
    conn = get_db_connection()
    try:
        row = conn.execute(
            'SELECT stage FROM lead_stages WHERE professional_id = ? AND lead_id = ?',
            (professional_id, lead_id)
        ).fetchone()
        return row['stage'] if row else PIPELINE_DEFAULT_STAGE
    finally:
        conn.close()



def get_pipeline_counts(professional_id, extra_where='', extra_params=()):
    '''Conteo de leads por etapa para un profesional. Sin fila cuenta como 'new'.

    extra_where/extra_params restringen a un subconjunto de leads (p. ej. filtro
    geografico de my_leads); las condiciones aplican sobre la tabla leads.
    '''
    conn = get_db_connection()
    try:
        counts = {stage: 0 for stage in PIPELINE_STAGES}
        filt = f' AND {extra_where}' if extra_where else ''
        rows = conn.execute(
            'SELECT s.stage, COUNT(*) AS n FROM lead_stages s '
            'JOIN leads ON leads.id = s.lead_id '
            f'WHERE s.professional_id = ?{filt} GROUP BY s.stage',
            (professional_id,) + tuple(extra_params)
        ).fetchall()
        for row in rows:
            if row['stage'] in counts:
                counts[row['stage']] = row['n']
        implicit_new = conn.execute(
            'SELECT COUNT(*) AS n FROM leads WHERE 1=1' + filt + ' AND id NOT IN ('
            'SELECT lead_id FROM lead_stages WHERE professional_id = ?)',
            tuple(extra_params) + (professional_id,)
        ).fetchone()['n']
        counts['new'] += implicit_new
        return counts
    finally:
        conn.close()



def move_lead_stage(professional_id, lead_id, to_stage, now_str=None):
    '''Mueve un lead de etapa: upsert en lead_stages + fila en lead_stage_history.

    Sincroniza lead_tracking.contacted = 1 cuando la etapa destino implica contacto.
    Devuelve (from_stage, to_stage) o None si la etapa es inválida.
    '''
    if to_stage not in PIPELINE_STAGES:
        return None
    if now_str is None:
        from datetime import datetime as _dt
        now_str = _dt.now().strftime('%Y-%m-%d %H:%M:%S')
    conn = get_db_connection()
    try:
        current = conn.execute(
            'SELECT stage FROM lead_stages WHERE professional_id = ? AND lead_id = ?',
            (professional_id, lead_id)
        ).fetchone()
        from_stage = current['stage'] if current else PIPELINE_DEFAULT_STAGE
        if from_stage == to_stage:
            # No-op idempotente: reintento o doble-click no genera
            # historial basura ni toca lead_tracking.
            return (from_stage, to_stage)
        if current:
            conn.execute(
                'UPDATE lead_stages SET stage = ?, updated_at = ? WHERE professional_id = ? AND lead_id = ?',
                (to_stage, now_str, professional_id, lead_id)
            )
        else:
            conn.execute(
                'INSERT INTO lead_stages (professional_id, lead_id, stage, updated_at) VALUES (?, ?, ?, ?)',
                (professional_id, lead_id, to_stage, now_str)
            )
        conn.execute(
            'INSERT INTO lead_stage_history (professional_id, lead_id, from_stage, to_stage, changed_at) VALUES (?, ?, ?, ?, ?)',
            (professional_id, lead_id, from_stage, to_stage, now_str)
        )
        if PIPELINE_STAGES.index(to_stage) >= PIPELINE_STAGES.index(PIPELINE_CONTACTED_FROM):
            existing = conn.execute(
                'SELECT contacted FROM lead_tracking WHERE professional_id = ? AND lead_id = ?',
                (professional_id, lead_id)
            ).fetchone()
            if existing:
                conn.execute(
                    'UPDATE lead_tracking SET contacted = 1, contacted_at = ? WHERE professional_id = ? AND lead_id = ?',
                    (now_str, professional_id, lead_id)
                )
            else:
                conn.execute(
                    'INSERT INTO lead_tracking (professional_id, lead_id, seen, contacted, seen_at, contacted_at) VALUES (?, ?, 0, 1, NULL, ?)',
                    (professional_id, lead_id, now_str)
                )
        conn.commit()
        return (from_stage, to_stage)
    except Exception:
        logger.exception('move_lead_stage failed for pro=%s lead=%s', professional_id, lead_id)
        conn.rollback()
        return None
    finally:
        conn.close()



def get_pipeline_stats(professional_id):
    '''Métricas del pipeline: conteo por etapa + días promedio en etapa actual + movimientos.'''
    from datetime import datetime as _dt
    conn = get_db_connection()
    try:
        counts = get_pipeline_counts(professional_id)
        rows = conn.execute(
            'SELECT stage, updated_at FROM lead_stages WHERE professional_id = ?',
            (professional_id,)
        ).fetchall()
        days_sum = {stage: 0.0 for stage in PIPELINE_STAGES}
        days_n = {stage: 0 for stage in PIPELINE_STAGES}
        now = _dt.now()
        for row in rows:
            if row['stage'] not in days_sum:
                continue
            try:
                updated = _dt.strptime((row['updated_at'] or '')[:19], '%Y-%m-%d %H:%M:%S')
                days_sum[row['stage']] += max(0.0, (now - updated).total_seconds() / 86400.0)
                days_n[row['stage']] += 1
            except ValueError:
                continue
        avg_days = {
            stage: (round(days_sum[stage] / days_n[stage], 1) if days_n[stage] else 0.0)
            for stage in PIPELINE_STAGES
        }
        moves_row = conn.execute(
            'SELECT COUNT(*) AS n FROM lead_stage_history WHERE professional_id = ?',
            (professional_id,)
        ).fetchone()
        return {'counts': counts, 'avg_days_in_stage': avg_days, 'total_moves': moves_row['n'] if moves_row else 0}
    finally:
        conn.close()



