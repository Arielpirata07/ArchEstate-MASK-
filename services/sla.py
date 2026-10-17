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
      `days=None` → todo el histórico (línea base con los datos backfilleados).
    - `contacted`: leads con fila en `lead_first_contact`.
      - `met`: contactados dentro de `threshold_hours` (cumplidos).
      - `contacted_late`: contactados fuera de plazo.
    - `pending`: asignados, sin contacto y todavía dentro de plazo.
    - `breached`: incumplidos = contactados tarde + asignados sin contacto ya vencidos.
    - `unassigned`: sin profesional asignado (o asignado inactivo) → fuera del KPI.
    - `% cumplimiento` = met / (met + breached).
    - Desglose por profesional (quien hizo el primer contacto) y por zona.
    '''
    from datetime import datetime

    now = datetime.now()
    if days is None:
        lead_where = ''
        contact_where = ''
    else:
        window = f"datetime('now', '-{int(days)} days')"
        lead_where = f'WHERE timestamp >= {window}'
        contact_where = f'WHERE l.timestamp >= {window} '

    lead_rows = conn.execute(
        f'SELECT id, timestamp, assigned_to FROM leads {lead_where}'
    ).fetchall()

    # Solo contactos de leads dentro de la ventana (la mediana/P90 deben ser
    # consistentes con `met`/`breached`, que ya están en ventana).
    contact_rows = conn.execute(
        'SELECT lfc.lead_id, lfc.business_hours_elapsed FROM lead_first_contact lfc '
        'JOIN leads l ON l.id = lfc.lead_id ' + contact_where
    ).fetchall()
    contact_by_lead = {}
    for r in contact_rows:
        contact_by_lead[r['lead_id']] = float(r['business_hours_elapsed'])

    inactive_rows = conn.execute('SELECT id FROM users WHERE is_active = 0').fetchall()
    inactive = {r['id'] for r in inactive_rows}

    total = len(lead_rows)
    contacted = met = contacted_late = pending = pending_late = unassigned = 0

    for lead in lead_rows:
        lid = lead['id']
        if lid in contact_by_lead:
            contacted += 1
            if contact_by_lead[lid] <= threshold_hours:
                met += 1
            else:
                contacted_late += 1
            continue
        assigned = lead['assigned_to']
        if not assigned or assigned in inactive:
            unassigned += 1
            continue
        created = _parse_ts(lead['timestamp'])
        elapsed = business_hours_between(created, now) if created else 0.0
        if elapsed <= threshold_hours:
            pending += 1
        else:
            pending_late += 1

    breached = contacted_late + pending_late
    compliance = (met / (met + breached) * 100.0) if (met + breached) else 0.0

    elapsed = sorted(contact_by_lead.values())

    by_pro = conn.execute(
        'SELECT lfc.professional_id, u.username, '
        'COUNT(*) AS contacted, '
        'SUM(CASE WHEN lfc.business_hours_elapsed <= ? THEN 1 ELSE 0 END) AS met '
        'FROM lead_first_contact lfc '
        'JOIN leads l ON l.id = lfc.lead_id '
        'LEFT JOIN users u ON u.id = lfc.professional_id ' + contact_where +
        'GROUP BY lfc.professional_id, u.username '
        'ORDER BY met DESC',
        (threshold_hours,)
    ).fetchall()

    by_zone = conn.execute(
        'SELECT l.zone, COUNT(*) AS contacted, '
        'SUM(CASE WHEN lfc.business_hours_elapsed <= ? THEN 1 ELSE 0 END) AS met '
        'FROM lead_first_contact lfc '
        'JOIN leads l ON l.id = lfc.lead_id ' + contact_where +
        'GROUP BY l.zone ORDER BY contacted DESC',
        (threshold_hours,)
    ).fetchall()

    return {
        'days': int(days) if days is not None else None,
        'threshold_hours': threshold_hours,
        'total_leads': total,
        'contacted': contacted,
        'unassigned': unassigned,
        'pending': pending,
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


def get_response_commitment(conn, days=90, min_sample=5, max_display=48):
    '''Compromiso de respuesta que se le comunica al cliente (Fase 3).

    Devuelve la mediana de horas habiles hasta el primer contacto de los
    ultimos `days` dias, redondeada, pero SOLO si hay muestra suficiente
    (`min_sample`) y el valor es razonable (`<= max_display`). Si no, la UI
    debe mostrar un mensaje generico ("a la brevedad") en vez de un numero
    que pueda sonar mal.

    `available=False` → usar el texto generico.
    '''
    since = f"-{int(days)} days"
    rows = conn.execute(
        'SELECT lfc.business_hours_elapsed FROM lead_first_contact lfc '
        'JOIN leads l ON l.id = lfc.lead_id '
        f"WHERE l.timestamp >= datetime('now', '{since}')"
    ).fetchall()
    hours = [float(r['business_hours_elapsed']) for r in rows]
    return _commitment_from(hours, min_sample, max_display)


def _commitment_from(hours, min_sample=5, max_display=48):
    '''Decide el compromiso a mostrar a partir de una lista de horas (pura).'''
    sample = len(hours)
    median = _percentile(sorted(hours), 50) if hours else 0.0
    available = sample >= min_sample and 0 < median <= max_display
    return {
        'available': bool(available),
        'hours': int(round(median)) if available else 0,
        'sample': sample,
    }
