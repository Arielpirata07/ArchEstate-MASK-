import logging
import re

import utils

from .base import get_db_connection

logger = logging.getLogger(__name__)


PIPELINE_STAGES = ['new', 'contacted', 'visit', 'negotiation', 'proposal', 'closed_won', 'closed_lost', 'archived']


PIPELINE_DEFAULT_STAGE = 'new'

# Etapas que implican contacto: al mover un lead a una de ellas se marca
# lead_tracking.contacted = 1 (ver roadmap Fase 1).

PIPELINE_CONTACTED_FROM = 'contacted'

PIPELINE_STAGE_META = {
    'new': {'label_es': 'Nuevo', 'label_en': 'New', 'color': '#735A3A'},
    'contacted': {'label_es': 'Contactado', 'label_en': 'Contacted', 'color': '#059669'},
    'visit': {'label_es': 'Visita Programada', 'label_en': 'Visit Scheduled', 'color': '#2563EB'},
    'negotiation': {'label_es': 'Negociación', 'label_en': 'Negotiation', 'color': '#7C3AED'},
    'proposal': {'label_es': 'Propuesta', 'label_en': 'Proposal', 'color': '#D97706'},
    'closed_won': {'label_es': 'Cerrado Ganado', 'label_en': 'Closed Won', 'color': '#059669'},
    'closed_lost': {'label_es': 'Cerrado Perdido', 'label_en': 'Closed Lost', 'color': '#DC2626'},
    'archived': {'label_es': 'Archivado', 'label_en': 'Archived', 'color': '#6B7280'},
}


def get_pipeline_stage_settings(conn=None, lang='es'):
    '''Etapas con sus etiquetas/colores/orden. Cae a los defaults si no hay filas.'''
    own_conn = conn is None
    if own_conn:
        conn = get_db_connection()
    try:
        try:
            rows = conn.execute(
                'SELECT stage, label_es, label_en, color, sort_order '
                'FROM pipeline_stage_settings ORDER BY sort_order, stage'
            ).fetchall()
        except Exception:
            rows = []

        settings = {}
        for row in rows:
            stage = row['stage']
            if stage in PIPELINE_STAGES:
                color = row['color'] or ''
                if not re.fullmatch(r'#[0-9A-Fa-f]{6}', color):
                    color = PIPELINE_STAGE_META[stage]['color']
                settings[stage] = {
                    'stage': stage,
                    'label_es': row['label_es'] or PIPELINE_STAGE_META[stage]['label_es'],
                    'label_en': row['label_en'] or PIPELINE_STAGE_META[stage]['label_en'],
                    'color': color,
                    'sort_order': row['sort_order'],
                }

        for index, stage in enumerate(PIPELINE_STAGES, start=1):
            if stage not in settings:
                settings[stage] = {
                    'stage': stage,
                    **PIPELINE_STAGE_META[stage],
                    'sort_order': index,
                }

        ordered = sorted(settings.values(), key=lambda s: (s['sort_order'], s['stage']))
        for item in ordered:
            item['label'] = item['label_en'] if lang == 'en' else item['label_es']
        return ordered
    finally:
        if own_conn:
            conn.close()


def update_pipeline_stage_settings(items):
    '''Actualiza etiquetas/colores/orden. Devuelve False si algún item es inválido.'''
    if not isinstance(items, list) or not items:
        return False

    conn = get_db_connection()
    try:
        for item in items:
            if not isinstance(item, dict):
                return False
            stage = (item.get('stage') or '').strip()
            if stage not in PIPELINE_STAGES:
                return False

            defaults = PIPELINE_STAGE_META[stage]
            label_es = utils.safe_text(item.get('label_es') or '').strip() or defaults['label_es']
            label_en = utils.safe_text(item.get('label_en') or '').strip() or defaults['label_en']
            color = (item.get('color') or defaults['color']).strip()
            if not re.fullmatch(r'#[0-9A-Fa-f]{6}', color):
                color = defaults['color']
            try:
                sort_order = int(item.get('sort_order', PIPELINE_STAGES.index(stage) + 1))
            except (TypeError, ValueError):
                sort_order = PIPELINE_STAGES.index(stage) + 1

            conn.execute(
                'INSERT INTO pipeline_stage_settings (stage, label_es, label_en, color, sort_order) '
                'VALUES (?, ?, ?, ?, ?) ON CONFLICT(stage) DO UPDATE SET '
                'label_es = excluded.label_es, label_en = excluded.label_en, '
                'color = excluded.color, sort_order = excluded.sort_order',
                (stage, label_es, label_en, color, sort_order)
            )
        conn.commit()
        return True
    except Exception:
        logger.exception('update_pipeline_stage_settings failed')
        conn.rollback()
        return False
    finally:
        conn.close()



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



def _move_lead_stage_conn(conn, professional_id, lead_id, to_stage, now_str):
    '''Núcleo del move sobre una conexión ya abierta (sin commit/close).

    Lo usan `move_lead_stage` (1 item) y `move_lead_stage_batch` (N items
    en una sola transacción). Incluye el guard no-op misma-etapa.
    '''
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
    return (from_stage, to_stage)


def move_lead_stage(professional_id, lead_id, to_stage, now_str=None):
    '''Mueve un lead de etapa: upsert en lead_stages + fila en lead_stage_history.

    Sincroniza lead_tracking.contacted = 1 cuando la etapa destino implica contacto.
    Devuelve (from_stage, to_stage) o None si la etapa es inválida.
    '''
    if to_stage not in PIPELINE_STAGES:
        return None
    if now_str is None:
        # UTC por convención de storage: lead_stages.updated_at,
        # lead_stage_history.changed_at y lead_tracking.contacted_at se
        # comparan en SQL contra datetime('now') y en Python contra utc_now().
        now_str = utils.utc_now_str()
    conn = get_db_connection()
    try:
        result = _move_lead_stage_conn(conn, professional_id, lead_id, to_stage, now_str)
        conn.commit()
    except Exception:
        logger.exception('move_lead_stage failed for pro=%s lead=%s', professional_id, lead_id)
        conn.rollback()
        return None
    finally:
        conn.close()

    # SLA: marcar primer contacto fuera de la transaccion critica (post-commit),
    # con su propia conexion. No sostiene el write-lock del request.
    if result and PIPELINE_STAGES.index(to_stage) >= PIPELINE_STAGES.index(PIPELINE_CONTACTED_FROM):
        try:
            from services.sla import record_first_contact
            record_first_contact(lead_id, professional_id, 'stage')
        except Exception:
            logger.warning('record_first_contact (stage) fallo para lead=%s', lead_id)

    return result


def move_lead_stage_batch(professional_id, lead_ids, to_stage, now_str=None):
    '''Mueve varios leads en UNA transacción (all-or-nothing).

    Los ids inexistentes se filtran antes (no abortan); cualquier error de
    DB revierte todo. Retorna cantidad movida (0 ante error o etapa inválida).
    '''
    if to_stage not in PIPELINE_STAGES or not lead_ids:
        return 0
    if now_str is None:
        now_str = utils.utc_now_str()  # ver nota de convención UTC en move_lead_stage
    conn = get_db_connection()
    try:
        placeholders = ','.join(['?'] * len(lead_ids))
        rows = conn.execute(
            f'SELECT id FROM leads WHERE id IN ({placeholders})', list(lead_ids)
        ).fetchall()
        existing = {r['id'] for r in rows}
        moved = 0
        for lid in lead_ids:
            if lid not in existing:
                continue
            if _move_lead_stage_conn(conn, professional_id, lid, to_stage, now_str):
                moved += 1
        conn.commit()
    except Exception:
        logger.exception('move_lead_stage_batch failed for pro=%s', professional_id)
        conn.rollback()
        return 0
    finally:
        conn.close()

    # SLA: marcar primer contacto post-commit, fuera del txn (propia conexion).
    if moved and PIPELINE_STAGES.index(to_stage) >= PIPELINE_STAGES.index(PIPELINE_CONTACTED_FROM):
        try:
            from services.sla import record_first_contact
            for lid in lead_ids:
                if lid in existing:
                    record_first_contact(lid, professional_id, 'stage')
        except Exception:
            logger.warning('record_first_contact (batch) fallo para pro=%s', professional_id)

    return moved



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
        # updated_at se guarda en UTC: restarle hora local del servidor
        # desfasaba los días en host con offset (producción UTC vs dev ART).
        now = utils.utc_now()
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



