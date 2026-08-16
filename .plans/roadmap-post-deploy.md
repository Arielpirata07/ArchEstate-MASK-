# Roadmap Post-Deploy — ArchEstate

> **Estado:** Plan de referencia — ejecutar después de deploy a Render + fixes de `fixes-pendientes.md`.
> **Versión actual:** v0.32.0 (128 tags, 543 tests)
> **Convención de commits:** `feat(scope):`, `fix(scope):`, `test(scope):`, `docs:`
> **Convención de tags:** Semver `v0.XX.Y` — cada fase = minor bump (`v0.33.0`, `v0.34.0`, `v0.35.0`, `v0.36.0`)

---

## Estado actual del proyecto

| Componente | Estado | Notas |
|---|---|---|
| Flask app | ✅ | Application Factory, 11 blueprints, `factory.py:create_app()` |
| DB | ✅ | SQLite default, PostgreSQL vía `DATABASE_URL` |
| i18n | ✅ | 1,102 keys Python + 412 keys JS (ES/EN) |
| Tests | ✅ | 543 pytest, `conftest.py` con temp DB |
| Professional dashboard | ✅ | 2 tabs: Leads (grid/filtros/tabla) + Stats (charts/KPIs) |
| Lead tracking | ✅ | `lead_tracking` con `seen`/`contacted` booleanos |
| Phone verification | ✅ | OTP simulated + Twilio, WhatsApp webhook |
| Notifications | ✅ | In-app + email, `notifications` table |
| Dark mode | ✅ | CSS variables, toggle en navbar |
| Animations | ✅ | Scroll reveal, tab transitions, hover micro-interactions |

---

## Prerequisito — Deploy + Fixes (sin tag nuevo)

Ejecutar primero. No cambia funcionalidad, solo corrige bugs conocidos.

### Fixes de `fixes-pendientes.md`

| # | Fix | Archivo | Commit |
|---|-----|---------|--------|
| 1 | Dark mode CTA — clase `.btn-cta-gold` | `static/css/base.css`, `templates/register.html:184`, `templates/login.html:86`, `templates/lead_detail.html:13` | `fix(ui): dark mode CTA buttons — add .btn-cta-gold class` |
| 2 | Avatar upload cache-busting | `static/js/profile.js:156,1238` | `fix(ui): avatar upload cache-busting — append ?v=Date.now()` |
| 3 | KPI totals globales | `routes/professional_bp.py:238-245`, `static/js/professional.js:825-857` | `fix(api): KPI totals in /api/leads — add unseen_total, contacted_total` |
| 4 | CTA 'Crear solicitud' oculto para profesionales | `templates/profile.html:568-570` | `fix(ui): hide create-lead CTA for professionals in profile` |
| 5 | Teléfono Argentina duplicación área | `static/js/profile.js:228-243`, `static/js/main.js:406-411` | `fix(phone): Argentina area code duplication — reorder normalization` |

### Deploy a Render

| Paso | Comando/Acción |
|------|---------------|
| Build | `pip install -r requirements.txt` |
| Start | `gunicorn wsgi:app --workers 4 --timeout 120 --access-logfile -` |
| Env vars | `SECRET_KEY`, `DATABASE_URL`, `SITE_URL`, `TWILIO_*`, `SMTP_*`, `PREFER_SECURE_COOKIES=true` |
| Verificación | `GET /health` → 200, `python -m pytest tests/ -q`, `python verify_coherence.py` |

---

## FASE 1 — Pipeline Kanban (Jira-style)

**Tag:** `v0.33.0`
**Archivos modificados:** `app_setup.py`, `routes/professional_bp.py`, `templates/professional.html`, `static/js/professional.js`, `static/css/professional.css`, `i18n/translations.py`, `static/js/i18n.js`
**Dependencia externa:** SortableJS (CDN o `static/js/sortable.min.js`)

### 1.1 Schema — `app_setup.py`

```sql
-- Nuevas tablas (CREATE TABLE IF NOT EXISTS)

CREATE TABLE IF NOT EXISTS lead_stages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    professional_id INTEGER NOT NULL,
    lead_id INTEGER NOT NULL,
    stage TEXT NOT NULL DEFAULT 'new',
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(professional_id, lead_id),
    FOREIGN KEY (professional_id) REFERENCES users(id),
    FOREIGN KEY (lead_id) REFERENCES leads(id)
);

CREATE TABLE IF NOT EXISTS lead_stage_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    professional_id INTEGER NOT NULL,
    lead_id INTEGER NOT NULL,
    from_stage TEXT,
    to_stage TEXT NOT NULL,
    changed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (professional_id) REFERENCES users(id),
    FOREIGN KEY (lead_id) REFERENCES leads(id)
);
```

**Índices:**
```sql
CREATE INDEX IF NOT EXISTS idx_lead_stages_pro ON lead_stages(professional_id);
CREATE INDEX IF NOT EXISTS idx_lead_stages_lead ON lead_stages(lead_id);
CREATE INDEX IF NOT EXISTS idx_lead_stages_stage ON lead_stages(professional_id, stage);
CREATE INDEX IF NOT EXISTS idx_stage_history_pro ON lead_stage_history(professional_id);
```

**Seed de estados por defecto** (en `init_db`):
```python
DEFAULT_STAGES = [
    ('new', 'Nuevo', '#735A3A', 1),
    ('contacted', 'Contactado', '#059669', 2),
    ('visit', 'Visita Programada', '#2563EB', 3),
    ('negotiation', 'Negociación', '#7C3AED', 4),
    ('proposal', 'Propuesta', '#D97706', 5),
    ('closed_won', 'Cerrado Ganado', '#059669', 6),
    ('closed_lost', 'Cerrado Perdido', '#DC2626', 7),
    ('archived', 'Archivado', '#6B7280', 8),
]
```

### 1.2 Endpoints — `routes/professional_bp.py`

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/api/pipeline/stages` | Lista etapas con conteo de leads por etapa |
| GET | `/api/pipeline/leads?stage=X` | Leads en una etapa específica (con filtros existentes) |
| POST | `/api/pipeline/lead/<id>/move` | Mover lead a nueva etapa: `{stage: "contacted"}` |
| GET | `/api/pipeline/stats` | Conteo por etapa + tiempo promedio en cada una |
| POST | `/api/pipeline/lead/<id>/bulk-move` | Mover múltiples leads (drag selecting) |

**Lógica de `move`:**
1. Validar que `stage` existe en `DEFAULT_STAGES`
2. Insertar en `lead_stage_history` (from_stage → to_stage)
3. Upsert en `lead_stages` (UNIQUE constraint)
4. Si `to_stage >= 'contacted'`, actualizar `lead_tracking.contacted = 1`
5. Return JSON con nuevo estado

### 1.3 UI — Kanban Board

**Toggle en Leads tab** (agregar al header, línea ~29 de `professional.html`):
```
Lista | Pipeline
```
Mismo patrón que `tab-btn` existente. `Lista` muestra la tabla actual, `Pipeline` muestra el Kanban.

**Columnas (8):**
```
┌──────────┬──────────┬──────────┬──────────┬──────────┬──────────┬──────────┬──────────┐
│  Nuevo   │Contactado│  Visita  │Negociación│ Propuesta│Cerrado ✓ │Cerrado ✗ │Archivado │
│  (gold)  │(emerald) │  (blue)  │ (violet) │ (amber)  │(emerald) │  (rose)  │  (gray)  │
├──────────┼──────────┼──────────┼──────────┼──────────┼──────────┼──────────┼──────────┤
│ ┌──────┐ │ ┌──────┐ │          │          │          │          │          │          │
│ │ Lead │ │ │ Lead │ │          │          │          │          │          │          │
│ │ Card │ │ │ Card │ │          │          │          │          │          │          │
│ └──────┘ │ └──────┘ │          │          │          │          │          │          │
│ ┌──────┐ │          │          │          │          │          │          │          │
│ │ Lead │ │          │          │          │          │          │          │          │
│ └──────┘ │          │          │          │          │          │          │          │
└──────────┴──────────┴──────────┴──────────┴──────────┴──────────┴──────────┴──────────┘
```

**Diseño de cada columna:**
- Header: `bg-paper-dark rounded-t-lg px-4 py-3 border-b border-midnight/5`
- Título: `text-[10px] font-bold uppercase tracking-widest text-gold` + badge conteo
- WIP limit badge: `text-[8px] text-rose-500` (advertencia visual, no bloqueo)
- Lead cards: `bg-white rounded-lg shadow-sm border border-midnight/5 p-3 mb-2`
- Dots de días en columna: `flex gap-1` con `w-1.5 h-1.5 rounded-full bg-gold/30` (1-7 puntos)
- Drag handle: `cursor-grab active:cursor-grabbing`

**Swimlanes** (toggle en toolbar):
- Por tipo de propiedad: Departamento, Casa, Dúplex, Penthouse, Local Comercial
- Por zona geográfica
- Toggle: chips iguales a los filtros existentes (`prop-chip` pattern)

**Drag & Drop (SortableJS):**
```javascript
// Inicialización
new Sortable(columnEl, {
    group: 'pipeline',
    animation: 200,
    ghostClass: 'pipeline-card-ghost',
    dragClass: 'pipeline-card-drag',
    handle: '.drag-handle',
    onEnd: function(evt) {
        const leadId = evt.item.dataset.leadId;
        const newStage = evt.to.dataset.stage;
        moveLeadToStage(leadId, newStage);
    }
});
```

**Quick filters** (arriba del Kanban):
- "Mis leads" / "Todos" (reutilizar `setMyLeads`)
- "Sin contactar" / "Últimos 7 días" / "Presupuesto > $500k"

### 1.4 CSS — `static/css/professional.css`

```css
/* Pipeline Kanban */
.pipeline-board { display: flex; gap: 1rem; overflow-x: auto; padding-bottom: 1rem; }
.pipeline-column { min-width: 280px; max-width: 320px; flex-shrink: 0; }
.pipeline-card { cursor: grab; transition: box-shadow 0.2s, transform 0.2s; }
.pipeline-card:active { cursor: grabbing; }
.pipeline-card-ghost { opacity: 0.4; background: var(--bg-secondary); }
.pipeline-card-drag { box-shadow: 0 12px 40px rgba(0,0,0,0.15); transform: rotate(2deg); }
.pipeline-column-header { position: sticky; top: 0; z-index: 10; }
.pipeline-dot { width: 6px; height: 6px; border-radius: 50%; }
.pipeline-wip-exceeded { border-color: #DC2626 !important; animation: wipPulse 1s ease infinite; }

@keyframes wipPulse { 0%,100% { box-shadow: 0 0 0 0 rgba(220,38,38,0.2); } 50% { box-shadow: 0 0 0 4px rgba(220,38,38,0); } }
@keyframes cardSlideIn { from { opacity:0; transform: translateY(-8px); } to { opacity:1; transform: translateY(0); } }
@keyframes columnHighlight { 0% { background: rgba(115,90,58,0.08); } 100% { background: transparent; } }
```

### 1.5 Tests

| # | Test | Tipo | Archivo |
|---|------|------|---------|
| 1.1 | Crear lead_stage al mover lead | pytest | `tests/test_pipeline.py` |
| 1.2 | Mover lead entre etapas (historial) | pytest | `tests/test_pipeline.py` |
| 1.3 | Mover lead a etapa inválida → 400 | pytest | `tests/test_pipeline.py` |
| 1.4 | GET /api/pipeline/stages retorna conteos | pytest | `tests/test_pipeline.py` |
| 1.5 | Mover lead actualiza lead_tracking.contacted | pytest | `tests/test_pipeline.py` |
| 1.6 | Lead duplicado en misma etapa → upsert | pytest | `tests/test_pipeline.py` |
| 1.7 | Pipeline stats retorna métricas | pytest | `tests/test_pipeline.py` |
| 1.8 | Kanban renderiza en browser | manual | Chrome DevTools |
| 1.9 | Drag-drop mueve lead entre columnas | manual | Chrome DevTools |
| 1.10 | Dots de días actualizan al mover | manual | Chrome DevTools |
| 1.11 | Swimlanes filtran correctamente | manual | Chrome DevTools |
| 1.12 | Dark mode en pipeline | manual | Chrome DevTools |

### 1.6 i18n — Nuevas keys (~30)

**Python (`i18n/translations.py`):**
```python
'pipeline.title': 'Pipeline',
'pipeline.toggle_list': 'Lista',
'pipeline.toggle_pipeline': 'Pipeline',
'pipeline.new': 'Nuevo',
'pipeline.contacted': 'Contactado',
'pipeline.visit': 'Visita Programada',
'pipeline.negotiation': 'Negociación',
'pipeline.proposal': 'Propuesta',
'pipeline.closed_won': 'Cerrado Ganado',
'pipeline.closed_lost': 'Cerrado Perdido',
'pipeline.archived': 'Archivado',
'pipeline.days_in_column': '{days} días en columna',
'pipeline.no_leads': 'Sin leads en esta etapa',
'pipeline.drag_hint': 'Arrastrar lead a otra columna',
'pipeline.swimlane_property': 'Por tipo de propiedad',
'pipeline.swimlane_zone': 'Por zona',
'pipeline.wip_warning': 'Límite WIP excedido',
'pipeline.filter_not_contacted': 'Sin contactar',
'pipeline.filter_last_7d': 'Últimos 7 días',
'pipeline.filter_high_budget': 'Presupuesto > $500k',
'pipeline.move_success': 'Lead movido a {stage}',
'pipeline.move_error': 'Error al mover lead',
```

**JS (`static/js/i18n.js`):**
```javascript
'pipeline.title': 'Pipeline',
'pipeline.toggle_list': 'Lista',
'pipeline.toggle_pipeline': 'Pipeline',
'pipeline.drag_hint': 'Arrastrar lead a otra columna',
'pipeline.no_leads': 'Sin leads',
'pipeline.days_in_column': '{days}d',
```

### 1.7 Commits

```
feat(pipeline): lead stages schema + seed — lead_stages, lead_stage_history tables
feat(pipeline): pipeline API — GET /api/pipeline/stages, POST move, stats
feat(pipeline): kanban board UI — 8 columns, drag-drop (SortableJS), swimlanes, WIP limits
feat(pipeline): pipeline toggle in Leads tab — Lista | Pipeline switch
test(pipeline): pytest + manual — 12 tests
docs(pipeline): add v0.33.0 to tags table
```

**Tag:** `v0.33.0`

---

## FASE 2 — Dashboard Ejecutivo

**Tag:** `v0.34.0`
**Archivos modificados:** `routes/professional_bp.py`, `templates/professional.html`, `static/js/professional.js`, `static/css/professional.css`, `i18n/translations.py`, `static/js/i18n.js`

### 2.1 Schema — `app_setup.py`

```sql
CREATE TABLE IF NOT EXISTS dashboard_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    professional_id INTEGER NOT NULL,
    snapshot_date DATE NOT NULL,
    total_leads INTEGER DEFAULT 0,
    new_leads INTEGER DEFAULT 0,
    contacted_leads INTEGER DEFAULT 0,
    pipeline_leads INTEGER DEFAULT 0,
    conversion_rate REAL DEFAULT 0,
    avg_budget REAL DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(professional_id, snapshot_date)
);
```

**Índices:**
```sql
CREATE INDEX IF NOT EXISTS idx_dash_snap_pro ON dashboard_snapshots(professional_id);
CREATE INDEX IF NOT EXISTS idx_dash_snap_date ON dashboard_snapshots(professional_id, snapshot_date);
```

**Nota:** `dashboard_snapshots` es opcional — cache de snapshots diarios para acelerar queries. Si no se usa, el dashboard calcula en tiempo real.

### 2.2 Endpoints — `routes/professional_bp.py`

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/api/dashboard/summary` | KPIs: total leads, nuevos hoy, tasa contacto, leads en pipeline, avg budget |
| GET | `/api/dashboard/trends?days=30` | Tendencia diaria de leads (para chart de línea) |
| GET | `/api/dashboard/pipeline` | Funnel: conteo por etapa de pipeline |
| GET | `/api/dashboard/activity?limit=20` | Actividad reciente: leads asignados, status changes, etapa changes |
| GET | `/api/dashboard/top-metrics` | Top zonas, top tipos propiedad, top operaciones (para bar charts) |

**Respuesta de `/api/dashboard/summary`:**
```json
{
    "total_leads": 145,
    "new_today": 3,
    "new_this_week": 12,
    "contact_rate": 0.72,
    "pipeline_active": 28,
    "avg_budget": 450000,
    "vs_last_week": { "leads": +8, "contact_rate": +0.05 },
    "top_zone": "Palermo",
    "top_property_type": "departamento"
}
```

### 2.3 UI — Executive Dashboard

**Nueva pestaña** (3ra tab): `Leads | Dashboard | Stats`

**Layout:**
```
┌──────────────────────────────────────────────────────────────┐
│ 📊 Dashboard Ejecutivo                                       │
├────────┬────────┬────────┬────────┬────────┬────────────────┤
│ Total  │ Nuevos │ Tasa   │Pipeline│  Avg   │ vs Semana      │
│ Leads  │ Semana │Contact │ Activo │ Budget │ Pasada         │
│  145   │  12    │  72%   │  28    │ $450k  │ +8 leads       │
├────────┴────────┴────────┴────────┴────────┴────────────────┤
│                                                              │
│  ┌─────────────────────────┐  ┌─────────────────────────┐   │
│  │ Tendencia Leads (30d)   │  │ Funnel Pipeline         │   │
│  │ 📈 Chart.js line        │  │ 📊 Barras horizontales  │   │
│  └─────────────────────────┘  └─────────────────────────┘   │
│                                                              │
│  ┌─────────────────────────┐  ┌─────────────────────────┐   │
│  │ Top Zonas               │  │ Top Tipos Propiedad     │   │
│  │ 📊 Barras verticales    │  │ 📊 Dona                 │   │
│  └─────────────────────────┘  └─────────────────────────┘   │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ Actividad Reciente                                   │   │
│  │ • Lead #45 asignado — Palermo — hace 2h              │   │
│  │ • Lead #42 movido a "Contactado" — hace 3h           │   │
│  │ • Lead #38 marcado como contactado — hace 5h         │   │
│  └──────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────┘
```

**KPI Cards** (reutilizar clase `kpi-card` existente):
- Total Leads: `border-l-4 border-gold`
- Nuevos esta semana: `border-l-4 border-emerald-600`
- Tasa de contacto: `border-l-4 border-blue-600`
- Leads en pipeline: `border-l-4 border-violet-600`
- Avg Budget: `border-l-4 border-amber-500`
- vs Semana pasada: trend arrow `↑ +8` / `↓ -3` con color

**Charts** (reutilizar `chart.umd.min.js` ya incluido):
- Tendencia: `line` chart, eje X = fechas, eje Y = cantidad leads
- Funnel pipeline: barras horizontales, cada etapa = barra con color
- Top zonas: barras verticales (reutilizar estilo de admin dashboard)
- Top tipos propiedad: doughnut chart

**Actividad reciente:**
- Lista tipo feed con iconos por tipo de evento
- Timestamp relativo ("hace 2h", "ayer")
- Click en lead → abre Lead Preview Drawer existente

### 2.4 CSS — `static/css/professional.css`

```css
/* Dashboard */
.dash-kpi-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 1rem; }
.dash-chart-card { background: var(--bg-secondary); border: 1px solid var(--border); border-radius: 1rem; padding: 1.25rem; }
.dash-activity-item { display: flex; align-items: flex-start; gap: 0.75rem; padding: 0.75rem 0; border-bottom: 1px solid var(--border); }
.dash-activity-dot { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; margin-top: 4px; }
.dash-trend-up { color: #059669; }
.dash-trend-down { color: #DC2626; }

@keyframes dashCountUp { from { opacity: 0; transform: translateY(8px); } to { opacity: 1; transform: translateY(0); } }
@keyframes dashFunnelGrow { from { width: 0; } to { width: var(--target-width); } }
@keyframes dashActivitySlide { from { opacity: 0; transform: translateX(-12px); } to { opacity: 1; transform: translateX(0); } }
@keyframes dashChartFade { from { opacity: 0; } to { opacity: 1; } }
```

### 2.5 Tests

| # | Test | Tipo | Archivo |
|---|------|------|---------|
| 2.1 | GET /api/dashboard/summary retorna KPIs | pytest | `tests/test_dashboard.py` |
| 2.2 | GET /api/dashboard/trends con days=7 | pytest | `tests/test_dashboard.py` |
| 2.3 | GET /api/dashboard/pipeline retorna conteos | pytest | `tests/test_dashboard.py` |
| 2.4 | GET /api/dashboard/activity con limit | pytest | `tests/test_dashboard.py` |
| 2.5 | Dashboard sin leads retorna zeros | pytest | `tests/test_dashboard.py` |
| 2.6 | Dashboard respeta filtro my_leads | pytest | `tests/test_dashboard.py` |
| 2.7 | Dashboard renderiza en browser | manual | Chrome DevTools |
| 2.8 | Charts muestran datos correctos | manual | Chrome DevTools |
| 2.9 | KPI cards animan al cargar | manual | Chrome DevTools |
| 2.10 | Dark mode en dashboard | manual | Chrome DevTools |

### 2.6 i18n — Nuevas keys (~25)

**Python:**
```python
'dash.title': 'Dashboard Ejecutivo',
'dash.total_leads': 'Total Leads',
'dash.new_this_week': 'Nuevos esta semana',
'dash.contact_rate': 'Tasa de contacto',
'dash.pipeline_active': 'En pipeline',
'dash.avg_budget': 'Presupuesto promedio',
'dash.vs_last_week': 'vs semana pasada',
'dash.trend_title': 'Tendencia de Leads',
'dash.pipeline_funnel': 'Funnel Pipeline',
'dash.top_zones': 'Top Zonas',
'dash.top_property_types': 'Tipos de Propiedad',
'dash.activity_recent': 'Actividad Reciente',
'dash.no_activity': 'Sin actividad reciente',
'dash.lead_assigned': 'Lead #{id} asignado',
'dash.lead_moved': 'Lead #{id} movido a {stage}',
'dash.lead_contacted': 'Lead #{id} contactado',
'dash.leads_today': '{count} leads hoy',
'dash.leads_week': '{count} leads esta semana',
```

**JS:**
```javascript
'dash.title': 'Dashboard Ejecutivo',
'dash.no_activity': 'Sin actividad',
'dash.lead_assigned': 'Lead #{id} asignado',
```

### 2.7 Commits

```
feat(dashboard): dashboard schema — dashboard_snapshots table
feat(dashboard): dashboard API — /api/dashboard/summary, trends, pipeline, activity
feat(dashboard): executive dashboard UI — KPI cards, trend chart, pipeline funnel, activity feed
feat(dashboard): dashboard tab — 3rd tab alongside Leads and Stats
test(dashboard): pytest + manual — 10 tests
docs(dashboard): add v0.34.0 to tags table
```

**Tag:** `v0.34.0`

---

## FASE 3 — Calendario (Google Calendar-style)

**Tag:** `v0.35.0`
**Archivos modificados:** `app_setup.py`, `routes/professional_bp.py`, `templates/professional.html`, `static/js/professional.js`, `static/css/professional.css`, `i18n/translations.py`, `static/js/i18n.js`

### 3.1 Schema — `app_setup.py`

```sql
CREATE TABLE IF NOT EXISTS calendar_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    professional_id INTEGER NOT NULL,
    lead_id INTEGER,
    title TEXT NOT NULL,
    description TEXT DEFAULT '',
    event_date DATE NOT NULL,
    start_time TEXT,
    end_time TEXT,
    event_type TEXT NOT NULL DEFAULT 'visit',
    location TEXT DEFAULT '',
    color TEXT DEFAULT 'gold',
    all_day INTEGER DEFAULT 0,
    completed INTEGER DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (professional_id) REFERENCES users(id),
    FOREIGN KEY (lead_id) REFERENCES leads(id)
);
```

**Índices:**
```sql
CREATE INDEX IF NOT EXISTS idx_cal_events_pro ON calendar_events(professional_id);
CREATE INDEX IF NOT EXISTS idx_cal_events_date ON calendar_events(professional_id, event_date);
CREATE INDEX IF NOT EXISTS idx_cal_events_type ON calendar_events(professional_id, event_type);
```

**Tipos de evento y colores:**
| Tipo | Color Tailwind | Hex | Uso |
|------|---------------|-----|-----|
| `visit` | `bg-gold` | `#735A3A` | Visita a propiedad |
| `call` | `bg-emerald-600` | `#059669` | Llamada telefónica |
| `followup` | `bg-blue-600` | `#2563EB` | Seguimiento |
| `meeting` | `bg-violet-600` | `#7C3AED` | Reunión |
| `other` | `bg-midnight` | `#000410` | Otro |

### 3.2 Endpoints — `routes/professional_bp.py`

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/api/calendar/events?month=YYYY-MM&week=YYYY-Www` | Listar eventos (mes o semana) |
| POST | `/api/calendar/events` | Crear evento: `{title, date, start_time, end_time, type, lead_id?, location?}` |
| PUT | `/api/calendar/events/<id>` | Actualizar evento |
| DELETE | `/api/calendar/events/<id>` | Eliminar evento |
| POST | `/api/calendar/events/<id>/move` | Re-programar: `{date, start_time?, end_time?}` |
| POST | `/api/calendar/events/<id>/complete` | Marcar como completado |
| GET | `/api/calendar/events/upcoming?days=7` | Próximos eventos (para mini sidebar) |

**Respuesta de `GET /api/calendar/events?month=2026-08`:**
```json
{
    "events": [
        {
            "id": 1,
            "title": "Visita depto Palermo",
            "date": "2026-08-15",
            "start_time": "10:00",
            "end_time": "11:00",
            "type": "visit",
            "color": "gold",
            "lead_id": 42,
            "location": "Av. Scalabrini Ortiz 1234",
            "all_day": false,
            "completed": false
        }
    ],
    "month": "2026-08"
}
```

### 3.3 UI — Google Calendar-style

**Nueva pestaña** (4ta tab): `Leads | Pipeline | Calendar | Stats`
(Dashboard se integra como 5to tab o como sección del pipeline — decidir en implementación)

**Layout principal:**
```
┌──────────────────────────────────────────────────────────────────┐
│ [<]  Agosto 2026  [>]        Hoy    Mes | Semana | Día          │
├────────────┬─────────────────────────────────────────────────────┤
│            │  Lun 10   Mar 11   Mié 12   Jue 13   Vie 14  ... │
│ Mini Cal   │ ┌────────┬────────┬────────┬────────┬────────┐     │
│ ┌────────┐ │ │        │        │ 🟡 10h │        │        │     │
│ │ A 2026 │ │ │        │        │ Visita │        │        │     │
│ │LuMaMiJv│ │ ├────────┼────────┼────────┼────────┼────────┤     │
│ │SaDo    │ │ │ 🟢 14h │        │        │ 🟣 09h │        │     │
│ │        │ │ │ Llamada│        │        │ Reunión│        │     │
│ └────────┘ │ ├────────┼────────┼────────┼────────┼────────┤     │
│            │ │        │ 🔵 11h │        │        │        │     │
│ Próximos   │ │        │Seguim. │        │        │        │     │
│ ────────   │ ├────────┼────────┼────────┼────────┼────────┤     │
│ • 15/8 10h │ │        │        │        │        │ 🟡 16h │     │
│   Visita   │ │        │        │        │        │ Visita │     │
│ • 18/8 14h │ └────────┴────────┴────────┴────────┴────────┘     │
│   Llamada  │                                                     │
└────────────┴─────────────────────────────────────────────────────┘
```

**Diseño del grid de mes (Google Calendar-style):**
- Cada día: `border border-midnight/5` con `min-height: 100px`
- Número de día: `text-[11px] font-bold text-midnight/70` en esquina superior izquierda
- Hoy: círculo `bg-gold text-white rounded-full w-6 h-6 flex items-center justify-center`
- Días de otros meses: `text-midnight/20` (ghosted)
- Eventos: pills pequeños con color del tipo, `text-[9px] text-white truncate rounded px-1.5 py-0.5`
- Hover en evento: tooltip con título completo + hora
- Click en evento: abre modal de detalle/edición

**Mini calendario sidebar (izquierda):**
- Grid 7x6 igual al principal pero en miniatura
- `text-[10px]`, días clickables para navegar
- Highlight de mes actual con `bg-gold/10`
- Hover: `bg-paper-dark rounded`
- Debajo: lista de "Próximos eventos" (5 más cercanos)

**Vista Semana:**
- 7 columnas (lun-dom), 24 filas (horas)
- Bloques de evento posicionados absolutamente (como Google Calendar)
- All-day events en header especial
- Click en slot vacío → modal de creación con fecha/hora prellenadas

**Vista Día:**
- 1 columna, 24 filas horarias
- Misma lógica de bloques que semana
- Más detalle por evento (ubicación, lead asociado)

**Toolbar de vista:**
```
Mes | Semana | Día
```
Mismo patrón `tab-btn` que existe. La vista se guarda en `localStorage`.

### 3.4 Modal de Creación/Edición de Evento

**Mismo patrón que Report Modal** (fixed inset-0, backdrop-blur, panel centrado):

```
┌──────────────────────────────────────────────┐
│ ✕                                            │
│  📅 Nuevo Evento                             │
│                                              │
│  Título *                                    │
│  ┌──────────────────────────────────────┐    │
│  │ Visita depto Palermo                 │    │
│  └──────────────────────────────────────┘    │
│                                              │
│  Fecha *          Hora inicio    Hora fin    │
│  ┌──────────┐    ┌────────┐    ┌────────┐   │
│  │ 15/08/26 │    │ 10:00  │    │ 11:00  │   │
│  └──────────┘    └────────┘    └────────┘   │
│                                              │
│  Tipo de evento                              │
│  [🟡 Visita] [🟢 Llamada] [🔵 Seguimiento]  │
│  [🟣 Reunión] [⚫ Otro]                     │
│                                              │
│  Lead asociado (opcional)                    │
│  ┌──────────────────────────────────────┐    │
│  │ 🔍 Buscar lead...                   │    │
│  └──────────────────────────────────────┘    │
│                                              │
│  Ubicación (opcional)                        │
│  ┌──────────────────────────────────────┐    │
│  │ Av. Scalabrini Ortiz 1234            │    │
│  └──────────────────────────────────────┘    │
│                                              │
│  Notas (opcional)                            │
│  ┌──────────────────────────────────────┐    │
│  │                                     │    │
│  └──────────────────────────────────────┘    │
│                                              │
│  [☐ Todo el día]                             │
│                                              │
│         [Cancelar]          [Crear Evento]   │
└──────────────────────────────────────────────┘
```

**Lead association:** Autocomplete que busca leads del profesional por ID/zona/email. Al seleccionar, se linkea `lead_id` y se muestra badge.

### 3.5 CSS — `static/css/professional.css`

```css
/* Calendar */
.cal-grid { display: grid; grid-template-columns: repeat(7, 1fr); border: 1px solid var(--border); }
.cal-day { min-height: 100px; padding: 0.25rem; border-right: 1px solid var(--border); border-bottom: 1px solid var(--border); position: relative; }
.cal-day:hover { background: var(--bg-secondary); }
.cal-day-number { font-size: 11px; font-weight: 700; color: rgba(0,4,16,0.7); width: 24px; height: 24px; display: flex; align-items: center; justify-content: center; border-radius: 50%; }
.cal-day-today .cal-day-number { background: #735A3A; color: white; }
.cal-day-other { opacity: 0.25; }
.cal-event { font-size: 9px; color: white; padding: 2px 6px; border-radius: 4px; margin-bottom: 2px; cursor: pointer; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; transition: transform 0.15s, box-shadow 0.15s; }
.cal-event:hover { transform: scale(1.02); box-shadow: 0 2px 8px rgba(0,0,0,0.15); }

/* Mini Calendar */
.cal-mini-grid { display: grid; grid-template-columns: repeat(7, 1fr); gap: 1px; }
.cal-mini-day { font-size: 10px; padding: 4px; text-align: center; border-radius: 4px; cursor: pointer; transition: background 0.15s; }
.cal-mini-day:hover { background: var(--bg-secondary); }
.cal-mini-day-selected { background: #735A3A; color: white; }
.cal-mini-day-today { font-weight: 700; color: #735A3A; }

/* Week/Day View */
.cal-time-grid { display: grid; grid-template-columns: 60px 1fr; }
.cal-time-label { font-size: 10px; color: rgba(0,4,16,0.4); padding: 0 0.5rem; text-align: right; border-right: 1px solid var(--border); }
.cal-time-slot { border-bottom: 1px solid var(--border); min-height: 48px; position: relative; }
.cal-time-slot:hover { background: rgba(115,90,58,0.03); }
.cal-event-block { position: absolute; left: 2px; right: 2px; border-radius: 6px; padding: 4px 8px; font-size: 10px; color: white; overflow: hidden; z-index: 5; cursor: pointer; transition: box-shadow 0.2s; }
.cal-event-block:hover { box-shadow: 0 4px 12px rgba(0,0,0,0.2); z-index: 10; }

/* Calendar Animations */
@keyframes calMonthSlide { from { opacity: 0; transform: translateX(20px); } to { opacity: 1; transform: translateX(0); } }
@keyframes calEventPop { from { opacity: 0; transform: scale(0.8); } to { opacity: 1; transform: scale(1); } }
@keyframes calTodayPulse { 0%,100% { box-shadow: 0 0 0 0 rgba(115,90,58,0.3); } 50% { box-shadow: 0 0 0 6px rgba(115,90,58,0); } }
@keyframes calMiniFade { from { opacity: 0; } to { opacity: 1; } }
@keyframes calModalIn { from { opacity: 0; transform: scale(0.95) translateY(8px); } to { opacity: 1; transform: scale(1) translateY(0); } }
@keyframes calSlotHighlight { from { background: rgba(115,90,58,0.1); } to { background: transparent; } }
@keyframes calWeekSlide { from { opacity: 0; transform: translateY(12px); } to { opacity: 1; transform: translateY(0); } }
@keyframes calEventDrag { from { opacity: 0.6; transform: scale(1.05); } to { opacity: 1; transform: scale(1); } }
```

### 3.6 Tests

| # | Test | Tipo | Archivo |
|---|------|------|---------|
| 3.1 | Crear evento válido | pytest | `tests/test_calendar.py` |
| 3.2 | Crear evento sin título → 400 | pytest | `tests/test_calendar.py` |
| 3.3 | Listar eventos por mes | pytest | `tests/test_calendar.py` |
| 3.4 | Actualizar evento | pytest | `tests/test_calendar.py` |
| 3.5 | Eliminar evento | pytest | `tests/test_calendar.py` |
| 3.6 | Re-programar evento (move) | pytest | `tests/test_calendar.py` |
| 3.7 | Evento con lead_id válido se linkea | pytest | `tests/test_calendar.py` |
| 3.8 | Próximos eventos (upcoming) | pytest | `tests/test_calendar.py` |
| 3.9 | Calendario renderiza en browser | manual | Chrome DevTools |
| 3.10 | Navegación mes anterior/siguiente | manual | Chrome DevTools |
| 3.11 | Click en día abre modal de creación | manual | Chrome DevTools |
| 3.12 | Eventos se muestran con color correcto | manual | Chrome DevTools |

### 3.7 i18n — Nuevas keys (~35)

**Python:**
```python
'cal.title': 'Calendario',
'cal.new_event': 'Nuevo Evento',
'cal.edit_event': 'Editar Evento',
'cal.event_title': 'Título',
'cal.event_date': 'Fecha',
'cal.event_start': 'Hora inicio',
'cal.event_end': 'Hora fin',
'cal.event_type': 'Tipo de evento',
'cal.event_type_visit': 'Visita',
'cal.event_type_call': 'Llamada',
'cal.event_type_followup': 'Seguimiento',
'cal.event_type_meeting': 'Reunión',
'cal.event_type_other': 'Otro',
'cal.event_lead': 'Lead asociado',
'cal.event_location': 'Ubicación',
'cal.event_notes': 'Notas',
'cal.event_all_day': 'Todo el día',
'cal.view_month': 'Mes',
'cal.view_week': 'Semana',
'cal.view_day': 'Día',
'cal.today': 'Hoy',
'cal.no_events': 'Sin eventos este día',
'cal.upcoming': 'Próximos eventos',
'cal.create': 'Crear Evento',
'cal.save': 'Guardar',
'cal.delete': 'Eliminar',
'cal.completed': 'Completado',
'cal.mark_complete': 'Marcar completo',
'cal.search_lead': 'Buscar lead...',
'cal.month_names': 'Enero,Febrero,Marzo,Abril,Mayo,Junio,Julio,Agosto,Septiembre,Octubre,Noviembre,Diciembre',
'cal.day_names': 'Lu,Ma,Mi,Ju,Vi,Sá,Do',
'cal.event_created': 'Evento creado',
'cal.event_updated': 'Evento actualizado',
'cal.event_deleted': 'Evento eliminado',
```

**JS:**
```javascript
'cal.title': 'Calendario',
'cal.new_event': 'Nuevo Evento',
'cal.today': 'Hoy',
'cal.no_events': 'Sin eventos',
'cal.create': 'Crear',
'cal.delete': 'Eliminar',
'cal.month_names': ['Enero','Febrero','Marzo','Abril','Mayo','Junio','Julio','Agosto','Septiembre','Octubre','Noviembre','Diciembre'],
'cal.day_names': ['Lu','Ma','Mi','Ju','Vi','Sá','Do'],
```

### 3.8 Commits

```
feat(calendar): calendar events schema — calendar_events table
feat(calendar): calendar API — CRUD, move, month/week/day views
feat(calendar): calendar UI — Google Calendar-style month grid, mini sidebar, event modal
feat(calendar): calendar tab — 4th tab, event color-coding by type
feat(calendar): integration — calendar events linked to leads (click → lead preview)
test(calendar): pytest + manual — 12 tests
docs(calendar): add v0.35.0 to tags table
```

**Tag:** `v0.35.0`

---

## FASE 4 — Multi-Tenant (Organizaciones)

**Tag:** `v0.36.0`
**Archivos modificados:** `app_setup.py`, `routes/admin_bp.py`, `routes/professional_bp.py`, `templates/admin.html`, `static/js/admin.js`, `static/css/admin.css`, `i18n/translations.py`, `static/js/i18n.js`

### 4.1 Schema — `app_setup.py`

```sql
CREATE TABLE IF NOT EXISTS organizations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    slug TEXT UNIQUE NOT NULL,
    description TEXT DEFAULT '',
    logo_url TEXT DEFAULT '',
    owner_id INTEGER NOT NULL,
    is_active INTEGER DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (owner_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS org_members (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    org_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    role TEXT NOT NULL DEFAULT 'member',
    joined_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(org_id, user_id),
    FOREIGN KEY (org_id) REFERENCES organizations(id),
    FOREIGN KEY (user_id) REFERENCES users(id)
);
```

**Índices:**
```sql
CREATE INDEX IF NOT EXISTS idx_org_members_org ON org_members(org_id);
CREATE INDEX IF NOT EXISTS idx_org_members_user ON org_members(user_id);
CREATE INDEX IF NOT EXISTS idx_orgs_owner ON organizations(owner_id);
```

**Roles de org:** `owner`, `admin`, `member`

### 4.2 Endpoints — `routes/admin_bp.py` + `routes/professional_bp.py`

| Método | Ruta | Blueprint | Descripción |
|--------|------|-----------|-------------|
| GET | `/api/admin/organizations` | admin | Listar todas las orgs |
| POST | `/api/admin/organizations` | admin | Crear org: `{name, slug, description}` |
| PUT | `/api/admin/organizations/<id>` | admin | Actualizar org |
| DELETE | `/api/admin/organizations/<id>` | admin | Eliminar org (soft delete) |
| POST | `/api/admin/organizations/<id>/members` | admin | Agregar miembro: `{user_id, role}` |
| DELETE | `/api/admin/organizations/<id>/members/<user_id>` | admin | Remover miembro |
| PUT | `/api/admin/organizations/<id>/members/<user_id>` | admin | Cambiar rol |
| GET | `/api/professional/my-org` | professional | Obtener org del profesional actual |
| GET | `/api/professional/org-leads` | professional | Leads de la org (compartidos) |

### 4.3 UI — Admin Panel

**Nueva pestaña en Admin:** `Dashboard | Professionals | Reports | Options | Organizations | ...`

**Vista de Organizaciones:**
```
┌──────────────────────────────────────────────────────────┐
│ 🏢 Organizaciones                          [+ Crear]     │
├──────────────────────────────────────────────────────────┤
│ Nombre         │ Slug        │ Miembros │ Owner │ Acción │
├────────────────┼─────────────┼──────────┼───────┼────────┤
│ ArchEstate BA  │ ae-ba       │    5     │ Admin │ ✏️ 🗑️  │
│ Studio Moderno │ studio-mod  │    3     │ Admin │ ✏️ 🗑️  │
└────────────────┴─────────────┴──────────┴───────┴────────┘
```

**Modal de creación:** Mismo patrón que existentes (form con nombre, slug auto-generado, descripción).

**Detalle de org:** Click en org → vista con lista de miembros, botón agregar/remover, selector de rol.

### 4.4 Integración con Leads

- `lead_stages` se mantiene por profesional (no por org)
- Nueva columna `org_id` en `leads` (opcional, FK a organizations)
- Filtro "org leads" muestra leads donde `leads.org_id = professional's org`
- Los leads de la org son visibles para todos los miembros de la org
- El admin puede asignar leads a orgs desde la gestión de usuarios

**Migración:**
```sql
ALTER TABLE leads ADD COLUMN org_id INTEGER REFERENCES organizations(id);
CREATE INDEX IF NOT EXISTS idx_leads_org ON leads(org_id);
```

### 4.5 Tests

| # | Test | Tipo | Archivo |
|---|------|------|---------|
| 4.1 | Crear organización | pytest | `tests/test_multitenant.py` |
| 4.2 | Slug duplicado → 409 | pytest | `tests/test_multitenant.py` |
| 4.3 | Agregar miembro a org | pytest | `tests/test_multitenant.py` |
| 4.4 | Remover miembro de org | pytest | `tests/test_multitenant.py` |
| 4.5 | Cambiar rol de miembro | pytest | `tests/test_multitenant.py` |
| 4.6 | Eliminar org (soft delete) | pytest | `tests/test_multitenant.py` |
| 4.7 | Org leads visibles para miembros | pytest | `tests/test_multitenant.py` |
| 4.8 | Lead sin org visible para todos | pytest | `tests/test_multitenant.py` |
| 4.9 | Admin CRUD orgs en browser | manual | Chrome DevTools |
| 4.10 | Agregar/remover miembros funciona | manual | Chrome DevTools |
| 4.11 | Org leads filtran correctamente | manual | Chrome DevTools |
| 4.12 | Solo owner puede eliminar org | manual | Chrome DevTools |
| 4.13 | Dark mode en panel de orgs | manual | Chrome DevTools |
| 4.14 | Mobile responsive en orgs | manual | Chrome DevTools |
| 4.15 | Existing leads sin org siguen visibles | manual | Chrome DevTools |

### 4.6 i18n — Nuevas keys (~25)

**Python:**
```python
'org.title': 'Organizaciones',
'org.create': 'Crear Organización',
'org.edit': 'Editar Organización',
'org.name': 'Nombre',
'org.slug': 'Slug',
'org.description': 'Descripción',
'org.members': 'Miembros',
'org.owner': 'Propietario',
'org.add_member': 'Agregar Miembro',
'org.remove_member': 'Remover Miembro',
'org.change_role': 'Cambiar Rol',
'org.role_owner': 'Propietario',
'org.role_admin': 'Admin',
'org.role_member': 'Miembro',
'org.my_org': 'Mi Organización',
'org.org_leads': 'Leads de la Organización',
'org.no_org': 'Sin organización',
'org.created': 'Organización creada',
'org.updated': 'Organización actualizada',
'org.deleted': 'Organización eliminada',
'org.member_added': 'Miembro agregado',
'org.member_removed': 'Miembro removido',
'org.slug_auto': 'Se generará automáticamente',
```

### 4.7 Commits

```
feat(multitenant): organizations schema — organizations, org_members tables
feat(multitenant): org management API — admin CRUD, role assignment
feat(multitenant): org admin UI — org list, member management, settings
feat(multitenant): org-scoped lead visibility — org_id in leads, org leads endpoint
feat(multitenant): migration — add org_id to leads table
test(multitenant): pytest + manual — 15 tests
docs(multitenant): add v0.36.0 to tags table
```

**Tag:** `v0.36.0`

---

## Verificación Final (sin tag)

```bash
python -m pytest tests/ -q                  # 590+ tests verdes
python verify_coherence.py                  # Schema/routes/templates coherentes
node --check static/js/*.js                 # Syntax check
node --test tests/*.test.js                 # JS tests
git log --oneline -20                       # Revisar commits
git tag -l --sort=-v:refname | head -10     # Ver tags nuevos
```

---

## Resumen de Tags

| Tag | Fase | Descripción | Tests |
|-----|------|-------------|-------|
| `v0.32.0` | Actual | Última versión antes del roadmap | 543 |
| (sin tag) | Prerequisito | Deploy + fixes de bugs conocidos | 543 |
| `v0.33.0` | Fase 1 | Pipeline Kanban (Jira-style) | +12 |
| `v0.34.0` | Fase 2 | Dashboard Ejecutivo | +10 |
| `v0.35.0` | Fase 3 | Calendario (Google Calendar-style) | +12 |
| `v0.36.0` | Fase 4 | Multi-Tenant (Organizaciones) | +15 |

**Total estimado:** 592 tests, 4 tags nuevos, ~25 commits.

---

## Archivos Totales Modificados por Fase

| Fase | Archivos nuevos | Archivos modificados | Líneas estimadas |
|------|----------------|---------------------|-----------------|
| Prerequisito | 0 | 5 | ~50 |
| Pipeline | `tests/test_pipeline.py` | 7 | ~800 |
| Dashboard | `tests/test_dashboard.py` | 6 | ~600 |
| Calendar | `tests/test_calendar.py` | 7 | ~900 |
| Multi-Tenant | `tests/test_multitenant.py` | 7 | ~700 |
| **Total** | **4** | **~12** | **~3050** |

---

## Dependencias Externas

| Dependencia | Fase | Uso | Incluida actualmente |
|-------------|------|-----|---------------------|
| Chart.js | 2 | Dashboard charts | ✅ `static/js/chart.umd.min.js` |
| SortableJS | 1 | Kanban drag-drop | ❌ — agregar `static/js/sortable.min.js` o CDN |
| Lucide Icons | Todas | Iconos UI | ✅ Cargado en `base.html` |

---

## Riesgos y Mitigaciones

| Riesgo | Impacto | Mitigación |
|--------|---------|------------|
| SortableJS no compatible con CSP | Alto | Usar versión CDN con hash, o bundle local |
| Calendar events DB crece rápido | Medio | Índices en `event_date`, Cleanup job opcional |
| Pipeline stages hardcodeados | Bajo | Seed en `init_db`, admin puede customizar en futuro |
| Multi-tenant rompe lead visibility actual | Alto | `org_id` nullable, leads sin org siguen visibles para todos |
| Performance con muchos leads en Kanban | Medio | Paginación por columna, lazy load al scrollear |
| Dark mode en calendar/grid | Medio | Usar CSS variables existentes, test manual obligatorio |
