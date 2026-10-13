# Plan de Mejoras — Auditoría Completa (2026-08-24)

**Fecha:** 2026-08-24
**Tests previos:** ~525 pytest + 3 node
**Contexto:** Auditoría integral del codebase (estructura, seguridad, DB, frontend, i18n) cruzada con documentos existentes (`fixes-pendientes.md`, `mejora-total.md`, `responsive-i18n-plan.md`, `roadmap-post-deploy.md`, `deploy-checklist.md`).

---

## Referencias cruzadas

| Documento existente | Relación con este plan |
|---------------------|----------------------|
| `fixes-pendientes.md` | 5 bugs → FASE 0 de este plan |
| `mejora-total.md` Fase 6 | Tests pendientes → FASE 6 de este plan |
| `responsive-i18n-plan.md` | i18n template strings → FASE 4 de este plan |
| `roadmap-post-deploy.md` | Features futuras → Post-plan |
| `deploy-checklist.md` | Deploy infra → FASE 7 de este plan |

---

## FASE 0 — Bug Fixes Pendientes (de `fixes-pendientes.md`)

> Ya documentados con root cause y líneas exactas. Bloquean deploy a Render.

| # | Bug | Archivos | Estado |
|---|-----|----------|--------|
| 0.1 | Phone formatting duplica código de área Argentina | `profile.js`, `main.js` | ⬜ |
| 0.2 | Dark mode CTA button invisible (`!important` overrides) | `base.css` | ⬜ |
| 0.3 | Avatar upload sin cache-busting | `profile.js` | ⬜ |
| 0.4 | KPI cards muestran por-página en vez de globales | `professional_bp.py`, `professional.js` | ⬜ |
| 0.5 | "Create request" CTA visible para profesionales | `profile.html` | ⬜ |

### Verificación FASE 0
```bash
python -m pytest tests/ -q
node --test tests/*.test.js
node --check static/js/profile.js static/js/main.js static/js/professional.js
python verify_coherence.py
```

---

## FASE 1 — Seguridad Crítica (P0)

| # | Problema | Ubicación | Fix | Estado |
|---|----------|-----------|-----|--------|
| 1.1 | **Connection leak** — `restore_session_from_remember_cookie` nunca cierra `conn` | `middleware.py:86-108` | `try/finally: conn.close()` | ⬜ |
| 1.2 | **Lead version + update no atómicos** — version persiste si update falla | `profile_bp.py:111-115` | Una sola conexión + transacción explícita | ⬜ |
| 1.3 | **XSS en admin.js** — categoría inyectada en innerHTML sin escape | `static/js/admin.js:1494` | `escapeHtml(c).replace(/_/g, ' ')` | ⬜ |
| 1.4 | **XSS en admin.js** — country code en onclick sin escape | `static/js/admin.js:2019` | Data attributes + `addEventListener` | ⬜ |
| 1.5 | **`confirm()` nativo** viola convención del proyecto | `static/js/admin.js:2153` | Reemplazar por `showConfirm()` de `main.js` | ⬜ |
| 1.6 | **`PRAGMA foreign_keys` no habilitado** — FK constraints inactive | `services/database.py:192` | `conn.execute('PRAGMA foreign_keys = ON')` | ⬜ |
| 1.7 | **Non-atomic credentials + profile update** | `profile_bp.py:171-176` | Una sola transacción | ⬜ |

> **Nota sobre 1.6**: `mejora-total.md` Fase 1.5 documenta que `PRAGMA foreign_keys = ON` fue revertido por timeouts en tests. Revisar si el issue persiste o usar `PRAGMA foreign_keys = ON` solo en production (no en test DB).

### Verificación FASE 1
```bash
python -m pytest tests/ -q
python verify_coherence.py
# Verificar que tests no fallan por FK constraints
```

---

## FASE 2 — Performance / Database (P1)

| # | Problema | Ubicación | Fix | Estado |
|---|----------|-----------|-----|--------|
| 2.1 | **N+1 connections en `auto_assign_lead()`** — conexión por cada profesional | `services/assignment.py:57` | `get_professional_coverage_batch(user_ids)` nueva en `models.py` | ⬜ |
| 2.2 | **N+1 notification inserts** — conexión por cada `_create_notification()` | `services/notifications.py:307-321` | Batch inserts con conexión pasada como parámetro | ⬜ |
| 2.3 | **Request-scoped connections no usadas** — `g.db_conn` nunca se setea | `models.py` + `middleware.py` | `get_db_connection()` cachea en `g`, teardown en `close_db_connection` | ⬜ |
| 2.4 | **Índices faltantes** en columnas filtradas frecuentemente | `app_setup.py` (migración) | `idx_leads_assigned`, `idx_leads_property_type`, `idx_lead_reports_lead_reported`, `idx_notifications_user_created` | ⬜ |
| 2.5 | **`_get_pro_geo_filter()` abre conexión propia** en vez de reusar | `professional_bp.py:314-358` | Recibir `conn` como parámetro | ⬜ |
| 2.6 | **`table_columns()` bypass DB abstraction** — abre conexión raw | `services/database.py:155-177` | Usar `get_db_connection()` | ⬜ |

### Verificación FASE 2
```bash
python -m pytest tests/ -q
python verify_coherence.py
# Benchmark: tiempo de carga /profesional con >100 leads antes/después
```

---

## FASE 3 — Calidad de Código (P2)

| # | Problema | Ubicación | Fix | Estado |
|---|----------|-----------|-----|--------|
| 3.1 | **`models.py` god file** (1346 líneas) | `models.py` | Dividir: `models/__init__.py`, `models/users.py`, `models/leads.py`, `models/professionals.py`, `models/notifications.py`, `models/misc.py` | ⬜ |
| 3.2 | **Rate limiting duplicado** — `lead_bp.py` reimplementa rate limiter | `routes/lead_bp.py:26-67` | Reutilizar `rate_limit.py` con configuración por zona | ⬜ |
| 3.3 | **`professional_bp.py`** (1255 líneas) | `routes/professional_bp.py` | Extraer: `routes/professional_leads.py`, `routes/professional_stats.py`, `routes/professional_export.py` | ⬜ |
| 3.4 | **`profile_bp.py`** (1199 líneas) | `routes/profile_bp.py` | Extraer API endpoints a `routes/profile_api.py` | ⬜ |
| 3.5 | **`config.py` parser manual de .env** | `config.py` | Usar `dotenv.load_dotenv()` (ya es dependencia en `requirements.txt`) | ⬜ |
| 3.6 | **`init_db()` demasiado largo** (776 líneas) | `app_setup.py:96-872` | Separar: `db_schema.py` (tables), `db_migrations.py` (migrations), `db_seeds.py` (seeds) | ⬜ |
| 3.7 | **100+ `except Exception`** — 21 son `pass` silencioso | Todo el proyecto | Auditar y reemplazar con excepciones específicas + log. Priorizar los 21 `pass` | ⬜ |
| 3.8 | **SQL f-string interpolation** sin parameterizar en KPI queries | `professional_bp.py:198, 374-419` | Queries parametrizadas | ⬜ |
| 3.9 | **`date_format_sql()` no valida column param** | `services/database.py:139` | Whitelist de columnas conocidas (`'timestamp'`, `'ts'`, etc.) | ⬜ |
| 3.10 | **`delete_reported_lead` nombre engañoso** — solo soft-deleta reporte | `admin_bp.py:556-599` | Renombrar a `mark_report_deleted` | ⬜ |

### Verificación FASE 3
```bash
python -m pytest tests/ -q
python verify_coherence.py
node --check static/js/*.js
```

---

## FASE 4 — i18n Pendiente (de `responsive-i18n-plan.md`)

> El plan `responsive-i18n-plan.md` documenta ~150+ strings hardcodeados y ~100 keys nuevas necesarias.

| # | Problema | Ubicación | Fix | Estado |
|---|----------|-----------|-----|--------|
| 4.1 | **~150+ strings hardcoded** en templates (lead_detail, edit_lead, professional, admin, user) | Ver `responsive-i18n-plan.md` Part C | Agregar ~100 keys a `translations.py` + `i18n.js` | ⬜ |
| 4.2 | **~100 strings en email templates** | `templates/email/*.html` | Keys para subjects y body de emails | ⬜ |
| 4.3 | **Meta tags SEO hardcodeados en español** | `templates/base.html:9,17,24,34` | `{{ t('seo.meta_description') }}` etc. | ⬜ |
| 4.4 | **Validation messages en `data-auth-rules`** — hardcodeados español | `login.html`, `register.html` | Inyectar `{{ t() }}` en JSON attributes | ⬜ |
| 4.5 | **aria-labels hardcodeados español** (~30 instancias) | Templates various | Keys en `translations.py` | ⬜ |
| 4.6 | **Structured data JSON-LD en español** | `templates/landing.html:28-58` | Usar `{{ t() }}` para FAQ content | ⬜ |

### Verificación FASE 4
```bash
python -m pytest tests/test_i18n.py -q
# Toggle idioma EN en /mi-perfil → verificar UI completa en inglés
python verify_coherence.py
```

---

## FASE 5 — Frontend / JS Architecture (P2-P3)

| # | Problema | Ubicación | Fix | Estado |
|---|----------|-----------|-----|--------|
| 5.1 | **263+ funciones globales en JS** — riesgo de collisiones | `admin.js`, `profile.js`, `professional.js`, `main.js` | Envolver cada archivo en IIFE | ⬜ |
| 5.2 | **`main.js` monolítico** (1539 líneas) | `static/js/main.js` | Dividir: `toasts.js`, `forms.js`, `scroll.js`, `budget.js`, `modals.js`, `otp.js` | ⬜ |
| 5.3 | **`escapeHtml` duplicado** | `main.js:42`, `auth.js:27` | Centralizar en `main.js`, eliminar fallback de `auth.js` | ⬜ |
| 5.4 | **Chip selection logic duplicada** | `user.js`, `edit_lead.js` | Extraer a `shared/chips.js` | ⬜ |
| 5.5 | **Empty `.catch()` blocks** — 47 fetch calls sin error handling | `main.js`, `profile.js`, `professional.js` | Agregar `console.error()` + toast en catch | ⬜ |
| 5.6 | **Google Fonts preload redundante** | `templates/base.html:98-99` | Eliminar `<link preload>` duplicado | ⬜ |
| 5.7 | **CDN sin SRI** — Lucide icons | `templates/base.html` | Self-host Lucide o agregar SRI hash | ⬜ |
| 5.8 | **`og-image.png` no existe** — social sharing roto | `templates/base.html:29,35` | Crear imagen 1200x630px | ⬜ |
| 5.9 | **162 inline `onclick` handlers** | Templates various | Migrar a `addEventListener` (progresivo, por template) | ⬜ |
| 5.10 | **Hero image externa** (`picsum.photos`) | `templates/landing.html:119` | Asset local optimizado | ⬜ |

### Verificación FASE 5
```bash
node --check static/js/*.js
python -m pytest tests/ -q
# Lighthouse audit:Performance, Accessibility, Best Practices, SEO
```

---

## FASE 6 — Testing (de `mejora-total.md` Fase 6 + gaps de auditoría)

> `mejora-total.md` Fase 6 está marcada como PENDING. Este plan la extiende con los gaps encontrados.

| # | Gap | Fix | Estado |
|---|-----|-----|--------|
| 6.1 | **Admin API endpoints** — sin tests dedicados | `test_admin_bp.py` (professional approval, lead management, reports, notifications) | ⬜ |
| 6.2 | **PDF/XLSX exports** — sin tests | `test_export_helpers.py` | ⬜ |
| 6.3 | **Matching service** — sin tests | `test_matching.py` | ⬜ |
| 6.4 | **Middleware** — sin tests directos | `test_middleware.py` (session refresh, language injection) | ⬜ |
| 6.5 | **Error handlers** — sin tests | `test_errors.py` (400-504 responses) | ⬜ |
| 6.6 | **Security tests** — Fase 1 items | Tests para connection leak, atomic operations, XSS patterns | ⬜ |

### Verificación FASE 6
```bash
python -m pytest tests/ -q
python -m pytest tests/ -x -v  # Stop on first failure
# Objetivo: 580+ tests pasando
```

---

## FASE 7 — Infraestructura / Deploy

> Alineado con `deploy-checklist.md` y `render.yaml`.

| # | Item | Fix | Estado |
|---|------|-----|--------|
| 7.1 | **Rate limiting multi-worker** — lock por-worker multiplica límite | Migrar de file-backed a Redis (`REDIS_URL` ya en `.env-example` y `render.yaml`) | ⬜ |
| 7.2 | **`init_db()` SQLite-specific** — `PRAGMA table_info` rompe con PostgreSQL | Adaptar migraciones para dual-driver (SQLite + PostgreSQL) | ⬜ |
| 7.3 | **Users table sin `created_at`** | Agregar columna + migración en `app_setup.py` | ⬜ |
| 7.4 | **Budget como TEXT** — requiere CAST en queries | Considerar `budget_min`/`budget_max` numéricos | ⬜ |
| 7.5 | **Schema versioning manual** | Evaluar migración a Alembic | ⬜ |

### Verificación FASE 7
```bash
python -m pytest tests/ -q
python verify_coherence.py
# Con DATABASE_URL apuntando a PostgreSQL: verificar que init_db() funciona
```

---

## Orden de Ejecución

```
Fase 0 (Bugs)  ──┐
                  ├──→ Fase 1 (Seguridad) ──→ Fase 2 (Performance)
                  │         │
                  │         └──→ Fase 6.6 (Security tests)
                  │
Fase 7.1 (Redis) ─┘

Fase 3 (Calidad) ──→ Fase 4 (i18n) ──→ Fase 5 (Frontend)
       │                    │
       └──→ Fase 6.1-6.5   └──→ Fase 6 (Tests completos)

Fase 7.2-7.5 (Infra) ──→ Post-plan (Roadmap Kanban)
```

**Justificación:**
- **Fase 0 primero**: los bugs ya están diagnosticados, son rápidos y desbloquean deploy.
- **Fase 1 después**: seguridad es prerrequisito para cualquier deploy a producción.
- **Fase 2 después de seguridad**: performance afecta UX directamente.
- **Fases 3-5 en paralelo**: calidad/i18n/frontend son independientes entre sí.
- **Fase 6 incrementalmente**: tests se escriben junto con cada fase.
- **Fase 7 al final**: infraestructura (Redis, PostgreSQL readiness) es previo al roadmap de features.

---

## Resumen por Esfuerzo

| Esfuerzo | Items | Descripción |
|----------|-------|-------------|
| **S** (<1h) | 20 | Bug fixes, XSS fixes, config improvements, index creation, preload fix, SRI |
| **M** (1-4h) | 12 | N+1 fixes, connection management, export tests, chip dedup, email i18n |
| **L** (4h+) | 8 | File splits (models.js, main.js, professional_bp.py), i18n bulk, admin tests, Alembic |

**Total estimado:** ~40 items, ~80-100h de trabajo.

---

## Checklists de Ejecución

### Post-FASE 0
- [ ] 5 bugs corregidos
- [ ] `python verify_coherence.py` pass
- [ ] Tests pasando

### Post-FASE 1
- [ ] 7 items de seguridad corregidos
- [ ] No hay connection leaks (verificar con `PRAGMA compile_options` o logging)
- [ ] XSS explorado con `escapeHtml`
- [ ] `confirm()` nativo eliminado

### Post-FASE 2
- [ ] N+1 queries eliminados (logging de queries para verificar)
- [ ] Request-scoped connections funcionando
- [ ] Índices creados

### Post-FASE 3
- [ ] `models.py` dividido en módulos
- [ ] Rate limiting unificado
- [ ] Route files reducidos a <500 líneas cada uno
- [ ] `config.py` usando `dotenv`

### Post-FASE 4
- [ ] ~100 keys nuevas en `translations.py` + `i18n.js`
- [ ] Toggle EN funciona en toda la UI
- [ ] Email templates internacionalizados

### Post-FASE 5
- [ ] JS files envueltos en IIFE
- [ ] `main.js` dividido en módulos
- [ ] Lighthouse score >90 en todas las categorías

### Post-FASE 6
- [ ] 580+ tests pasando
- [ ] Cobertura de admin API, exports, matching, middleware, error handlers

### Post-FASE 7
- [ ] Rate limiting con Redis
- [ ] `init_db()` compatible con PostgreSQL
- [ ] `users.created_at` agregado

---

## Riesgos / Notas

- **Fase 1.6**: `PRAGMA foreign_keys = ON` fue revertido en `mejora-total.md` por timeouts en tests. Investigar causa raíz antes de re-intentar.
- **Fase 3.1**: Dividir `models.py` puede romper imports en ~30+ archivos. Hacer incrementalmente con re-exports en `models/__init__.py`.
- **Fase 3.3-3.4**: Dividir route files puede romper `url_for()` si los blueprint names cambian. Mantener names existentes.
- **Fase 5.2**: Dividir `main.js` puede romper dependencias implícitas entre funciones. Hacer con cuidado y tests.
- **Fase 7.1**: Redis requiere `REDIS_URL` en Render. Verificar que el servicio Redis está configurado en `render.yaml`.
- **Fase 7.4**: Cambiar schema de `budget` afecta todas las queries existentes. Evaluar si el beneficio justifica el riesgo.
- **Roadmap**: Este plan es prerrequisito para `roadmap-post-deploy.md` (Kanban, Dashboard, Calendar, Multi-Tenant).
