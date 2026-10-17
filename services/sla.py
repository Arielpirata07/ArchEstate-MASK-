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
