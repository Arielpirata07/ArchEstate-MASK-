# noodle --queries-> database (sql,leads)
# noodle --computes-> metrics (sla,business_hours)
"""
SLA de primer contacto.

Un lead se considera "contactado" en la primera señal explícita de un
profesional aprobado: moverlo a etapa 'contacted'+, revelar el teléfono, o
generar/usar el link de WhatsApp. La marca se guarda en `lead_first_contact`
(PK = lead_id → idempotente, gana la primera señal) con las horas hábiles
transcurridas desde la creación del lead.

Diseño sin fricción: solo instrumentación. Fuera de la transacción crítica
(patrón del plan marketplace) — `record_first_contact` usa su propia conexión
y hace commit propio; nunca sostiene el write-lock del request principal.
"""
import logging
from datetime import datetime, timedelta, time

logger = logging.getLogger(__name__)

# Horario hábil del SLA (lun–vie). Feriados y tz por usuario: fuera de alcance
# (ver plan Fase 3). Se usa la tz naive del servidor, consistente con
# lead_tracking.contacted_at y events.ts.
BUSINESS_START = time(9, 0)
BUSINESS_END = time(18, 0)

# Fuentes de primer contacto, en orden de prioridad de reporting (no temporal).
SLA_SOURCES = ('stage', 'reveal', 'wa_link', 'call', 'sms')

# Etapas de pipeline que implican contacto (>= 'contacted').
# Se importa en caliente para evitar circular imports con models.pipeline.


def business_hours_between(start, end):
    '''Horas hábiles transcurridas entre dos datetimes (lun–vie 09:00–18:00).

    Función pura y testeable. Devuelve float (horas). Si end <= start → 0.0.
    Recorre día a día; en la práctica son pocos días (SLA de horas), así que
    un loop diario es correcto y barato.
    '''
    if not start or not end or end <= start:
        return 0.0

    total = timedelta(0)
    day = start.date()
    last = end.date()

    while day <= last:
        if day.weekday() < 5:  # 0=lun .. 4=viernes
            day_start = datetime.combine(day, BUSINESS_START)
            day_end = datetime.combine(day, BUSINESS_END)
            lo = max(start, day_start)
            hi = min(end, day_end)
            if hi > lo:
                total += hi - lo
        day += timedelta(days=1)

    return total.total_seconds() / 3600.0


def _parse_ts(value):
    '''Parsea un timestamp de DB (str o datetime) a datetime. Devuelve None si es inválido.'''
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    text = str(value).strip()
    if not text:
        return None
    try:
        return datetime.strptime(text[:19], '%Y-%m-%d %H:%M:%S')
    except ValueError:
        try:
            return datetime.strptime(text[:10], '%Y-%m-%d')
        except ValueError:
            return None


def record_first_contact(lead_id, professional_id, source, when=None, conn=None):
    '''Marca el primer contacto de un lead (idempotente, gana la primera señal).

    - `source` debe estar en SLA_SOURCES.
    - `when`: datetime de la señal (default: ahora). Se ignora si el lead ya
      tiene fila en lead_first_contact (INSERT OR IGNORE por PK).
    - Si se pasa `conn`, NO hace commit (para when dentro de un txn ajeno).
      Si no, abre su propia conexión y commitea (patrón fuera de txn crítico).
    - Devuelve True si esta llamada insertó la fila (fue la primera señal).
    '''
    if source not in SLA_SOURCES:
        logger.warning('record_first_contact: source desconocida %r', source)
        return False

    own_conn = conn is None
    try:
        if own_conn:
            from models import get_db_connection
            conn = get_db_connection()

        lead = conn.execute(
            'SELECT timestamp FROM leads WHERE id = ?', (lead_id,)
        ).fetchone()
        if not lead:
            return False

        created = _parse_ts(lead['timestamp']) or _parse_ts(when) or datetime.now()
        contact_at = when or datetime.now()
        elapsed = business_hours_between(created, contact_at)

        cur = conn.execute(
            'INSERT OR IGNORE INTO lead_first_contact '
            '(lead_id, professional_id, contact_at, source, business_hours_elapsed) '
            'VALUES (?, ?, ?, ?, ?)',
            (lead_id, professional_id, contact_at.strftime('%Y-%m-%d %H:%M:%S'),
             source, round(elapsed, 4))
        )
        if own_conn:
            conn.commit()
        return cur.rowcount > 0
    except Exception:
        logger.exception('record_first_contact falló para lead=%s', lead_id)
        if own_conn and conn:
            try:
                conn.rollback()
            except Exception:
                pass
        return False
    finally:
        if own_conn and conn:
            conn.close()


def _percentile(values, pct):
    '''Percentil lineal simple sobre una lista de floats.'''
    if not values:
        return 0.0
    if len(values) == 1:
        return float(values[0])
    k = (len(values) - 1) * (pct / 100.0)
    f = int(k)
    c = min(f + 1, len(values) - 1)
    if f == c:
        return float(values[f])
    return float(values[f] + (values[c] - values[f]) * (k - f))


def compute_sla_kpis(conn, days=30, threshold_hours=24.0):
    '''KPIs de cumplimiento del SLA de primer contacto.

    - Ventana: `days` días hacia atrás desde ahora (creación del lead).
    - Cumplido: primer contacto con `business_hours_elapsed <= threshold_hours`.
    - Desglose por profesional (quien hizo el primer contacto) y por zona.
    - Leads sin señal ('unassigned') no entran al % de cumplimiento.
    '''
    since = f"-{int(days)} days"

    base = conn.execute(
        f"SELECT COUNT(*) FROM leads WHERE timestamp >= datetime('now', '{since}')"
    ).fetchone()[0]

    contacted = conn.execute(
        'SELECT COUNT(*) FROM lead_first_contact lfc '
        'JOIN leads l ON l.id = lfc.lead_id '
        f"WHERE l.timestamp >= datetime('now', '{since}')"
    ).fetchone()[0]

    met = conn.execute(
        'SELECT COUNT(*) FROM lead_first_contact lfc '
        'JOIN leads l ON l.id = lfc.lead_id '
        f"WHERE l.timestamp >= datetime('now', '{since}') "
        'AND lfc.business_hours_elapsed <= ?',
        (threshold_hours,)
    ).fetchone()[0]

    breached = contacted - met

    elapsed_rows = conn.execute(
        'SELECT lfc.business_hours_elapsed FROM lead_first_contact lfc '
        'JOIN leads l ON l.id = lfc.lead_id '
        f"WHERE l.timestamp >= datetime('now', '{since}') "
        'ORDER BY lfc.business_hours_elapsed ASC'
    ).fetchall()
    elapsed = [float(r['business_hours_elapsed']) for r in elapsed_rows]

    compliance = (met / contacted * 100.0) if contacted else 0.0

    by_pro = conn.execute(
        'SELECT lfc.professional_id, u.username, '
        'COUNT(*) AS contacted, '
        'SUM(CASE WHEN lfc.business_hours_elapsed <= ? THEN 1 ELSE 0 END) AS met '
        'FROM lead_first_contact lfc '
        'JOIN leads l ON l.id = lfc.lead_id '
        'LEFT JOIN users u ON u.id = lfc.professional_id '
        f"WHERE l.timestamp >= datetime('now', '{since}') "
        'GROUP BY lfc.professional_id, u.username '
        'ORDER BY met DESC',
        (threshold_hours,)
    ).fetchall()

    by_zone = conn.execute(
        'SELECT l.zone, COUNT(*) AS contacted, '
        'SUM(CASE WHEN lfc.business_hours_elapsed <= ? THEN 1 ELSE 0 END) AS met '
        'FROM lead_first_contact lfc '
        'JOIN leads l ON l.id = lfc.lead_id '
        f"WHERE l.timestamp >= datetime('now', '{since}') "
        'GROUP BY l.zone ORDER BY contacted DESC',
        (threshold_hours,)
    ).fetchall()

    unassigned = base - contacted

    return {
        'days': int(days),
        'threshold_hours': threshold_hours,
        'total_leads': base,
        'contacted': contacted,
        'unassigned': unassigned,
        'met': met,
        'breached': breached,
        'compliance_pct': round(compliance, 1),
        'median_hours': round(_percentile(elapsed, 50), 2),
        'p90_hours': round(_percentile(elapsed, 90), 2),
        'by_professional': [
            {
                'professional_id': r['professional_id'],
                'username': r['username'] or '',
                'contacted': r['contacted'],
                'met': r['met'],
                'compliance_pct': round((r['met'] / r['contacted'] * 100.0) if r['contacted'] else 0.0, 1),
            }
            for r in by_pro
        ],
        'by_zone': [
            {
                'zone': r['zone'],
                'contacted': r['contacted'],
                'met': r['met'],
                'compliance_pct': round((r['met'] / r['contacted'] * 100.0) if r['contacted'] else 0.0, 1),
            }
            for r in by_zone
        ],
    }
