# Changelog — ArchEstate

Formato basado en [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/), versionado [SemVer](https://semver.org/lang/es/). Las entradas están ordenadas de la más reciente a la más antigua.

> **Fuente profunda:** la tabla de tags completa (commit + descripción) vive en `.contexto-proyecto.md` (sección "Tags / Versionado"). El log de bugfixes por sesión está en `fixes-changelog.md`.

## [Unreleased]

### Agregado
- **Portafolio profesional**: hasta 12 imágenes por profesional
  (`GET/POST/DELETE /api/profile/professional/portfolio`), validación por
  magic-bytes y límite de 16 MB, almacenamiento en `PORTFOLIO_FOLDER`, galería
  editable en `/mi-perfil` y claves i18n ES/EN.
- **Etapas de pipeline configurables**: tabla `pipeline_stage_settings` con seed
  idempotente, `models.get_pipeline_stage_settings` /
  `update_pipeline_stage_settings`, `GET/PUT /api/admin/pipeline-stages` y
  pestaña de administración para editar etiquetas ES/EN, color y orden. El
  tablero Kanban del profesional consume las etiquetas/colores/orden del
  servidor.
- **Verificación de email**: columna `users.email_verified`, tabla
  `email_verification_tokens`, email transaccional, ruta `/verify-email/<token>`
  (token de un solo uso, 24 h), reenvío desde `/mi-perfil`
  (`POST /api/email/send-verification`) y reset automático de la verificación
  al cambiar el email. Cuentas preexistentes se migran como verificadas.

### Corregido
- **Sitemap** (`routes/public_bp.py`): se quitó `/profesional` (ruta privada)
  del `sitemap.xml`.

### Frontend (revisión UI)
- **Panel de etapas del admin** (`templates/admin.html`, `static/js/admin.js`):
  el formulario y el botón Guardar usaban clases `.input-label`/`.input-field`/
  `.btn-primary` que solo existen en `profile.css` (no cargado en `/admin`);
  ahora siguen el patrón admin (labels `text-[10px] uppercase` con `for`,
  inputs con borde/focus gold, botón `bg-midnight hover:bg-gold`) y cada campo
  tiene `id` por etapa.
- **Portafolio** (`static/js/profile.js`): `alt` descriptivo en las imágenes,
  botón de eliminar visible en touch (antes solo en hover), y `loadPortfolio`
  muestra estado de carga/error en `#portfolio-status` (antes `catch`
  silencioso con parpadeo del empty state).
- **i18n**: nuevas keys `profile.portfolio_image_alt` y
  `profile.portfolio_loading` (ES/EN, Python y JS).
- **Responsive**: filas de etapas pasan a `md:grid-cols-2 lg:grid-cols-5`
  (evita 5 columnas apretadas a 768px), `flex-wrap` en la fila de Guardar del
  panel y en `#email-verification-area`, y botón de eliminar portafolio con
  mejor target táctil (`p-3 md:p-1.5`).

### Seguridad (post-revisión)
- **Portafolio con ownership real**: `portfolio` salió del allowlist de
  `PUT /api/profile/professional/full` (solo se edita por la API de portafolio);
  `_portfolio_items` filtra por prefijo `pro_{user_id}_` y el `DELETE` rechaza
  rutas que no pertenezcan al propio usuario.
- **Límite de tamaño a nivel HTTP**: `app.config['MAX_CONTENT_LENGTH']` en
  `factory.py` (antes el chequeo de 16 MB corría después de bufferizar el
  multipart).
- **Tokens de verificación atados al email**: `email_verification_tokens.email`
  + validación contra el email vigente; cambiar el email invalida los tokens
  pendientes (`update_user_credentials` / `update_user_account`). Índice
  `(user_id, used)` y columna agregada vía migración.
- **`X-Content-Type-Options: nosniff` ahora también para `/static/`**
  (defensa contra polyglots en uploads).
- **Color de pipeline validado al leer** y escapado en el render JS del Kanban.

### Revisión completa del sistema
- **Seguridad backend**: OTP de verificadores simulados redactado en logs fuera
  de debug (`services/verifier.py`); el seed del admin ya no loguea la
  contraseña si no puede escribir `.admin_initial_password` (en producción omite
  la creación y pide `ADMIN_INITIAL_PASSWORD`); el token de reset de contraseña
  se consume de forma atómica (`models.consume_password_reset_token`), evitando
  doble uso concurrente; el teléfono del webhook de WhatsApp se loguea hasheado;
  `/health` loguea la excepción; los 429 incluyen `Retry-After` y
  `X-RateLimit-*` con la misma clave `endpoint:IP`.
- **Correctitud de datos**: `utils.parse_budget_avg` promedia rangos
  (`"150000 - 400000"` → 275000) y reemplaza los `AVG` SQL divergentes en
  dashboard/stats; timestamps del pipeline en UTC (se quitó `pytz`/ART);
  `get_user_leads` con `LIMIT/OFFSET` (máx. 500) y parámetros en la API;
  migración v8 con dedup seguro e índices únicos en `lead_versions(lead_id,
  version)` y parciales en `professionals.user_id` / `users.email`; registro
  rechaza emails duplicados con `auth.email_taken`.
- **Frontend**: handlers inline rotos por IIFE reemplazados por `data-action`
  (búsqueda de iconos, selects de organización, rol de miembros y dropzone de
  documentos con drag & drop); headers de tablas admin/profesional traducidos
  (`leads.*`); `aria-labelledby` en los modales de detalle de lead y calendario;
  CTA del email de cambio de estado ya no apunta a `#`.
- **Infra/docs**: `verify_coherence.py` cubre los 12 blueprints; `AGENTS.md`
  actualizado; `.env-example` agregado.

### Tests
- Nuevos: `tests/test_email_verification.py` (11) y
  `TestAdminPipelineStages` en `tests/test_admin_bp.py` (6).
- Nuevos de esta revisión: reset token de un solo uso, registro con email
  duplicado, `parse_budget_avg` con rangos y OTP redactado (visible solo en
  debug).
- `TestEmailTokenBinding`, `TestUploadAndHeaderSecurity`
  (MAX_CONTENT_LENGTH, 413, nosniff), ownership de portafolio y fallback de
  color inválido en lectura.
- → **863 pytest / 96 coherence / 34 node**.

## [v0.48.7] — 2026-10-20 — Aislamiento de Twilio en tests y sincronización de docs

### Corregido
- **Tests de rate limit dependientes del `.env` local**
  (`tests/conftest.py`): `test_rate_limit_isolation.py` fallaba con 502 al
  llamar `/api/phone/send-code` cuando el entorno tenía `TWILIO_SIMULATE=false`
  y credenciales reales: el router singleton de `services/verifier.py`
  instanciaba `TwilioSmsVerifier` y el test pegaba contra Twilio real
  (`400 Content was not found`). Nuevo fixture `autouse`
  `_force_simulated_twilio` que fuerza `config.TWILIO_SIMULATE=True` y resetea
  el router antes/después de cada test, de modo que la suite ya no depende del
  `.env` ni de CI. Los tests que ejercitan Twilio real siguen haciendo
  `patch('config.TWILIO_SIMULATE', False)` + `reset_default_router()`.

### Documentación
- **`README.md` roadmap**: marcados como completados los 3 ítems que ya estaban
  implementados (notificaciones internas, asignación automática y paginación de
  leads).
- **Conteos de tests/coherencia actualizados**: `828 pytest + 34 node` y
  `94 checks` en `README.md`, `AGENTS.md` y `docs/contexto-proyecto.md`.
- **`AGENTS.md` Test notes**: documentado que `conftest.py` fuerza
  `TWILIO_SIMULATE=true` y resetea el router por test.

### Tests
- → **828 pytest / 94 coherence / 34 node** (0 fallos en local con `.env` real).

## [v0.48.6] — 2026-10-19 — Endurecimiento XSS en render de leads y paridad i18n

### Corregido
- **XSS persistente en el render JS de leads** (`static/js/admin.js`,
  `static/js/professional.js`): `renderLeadDetail`, `renderLeads` y
  `openLeadPreview` interpolaban valores provenientes de la API en `innerHTML`
  sin escapar. El servidor no sanitiza centralmente estos campos
  (`client_bp.py` toma `data.get(...)` tal cual; `utils.safe_text` solo
  reemplaza símbolos de moneda), así que un lead con HTML se ejecutaba en el
  panel de admin/profesional. Ahora se escapa todo valor de texto/numérico:
  `budget`, `timestamp`, `bedrooms`/`bathrooms`/`total_area`/`land_area`/
  `built_area`/`usable_m2`, `propLabel`, `specs`, `type`, `zone`, `province`,
  `architectural_style`, `ambientes`, `parking`, `orientation`,
  `property_condition`, `property_age`, `email`, `phone` y los `typeDetails`.
  En admin también se escapan `eventoLabel`/`fecha` del panel de actividad,
  `created_at` del log de notificaciones y `cc` de los filtros por país.
- **XSS atributivo en `<option>`** (`budget.js`, `forms.js`): el `value="..."`
  del código de moneda/operación se armaba con el texto crudo del servidor;
  ahora pasa por `escapeHtml`.
- **Badge de verificación de teléfono** (`profile.js`): `icon` y `label` se
  concatenaban sin escapar (aunque hoy son constantes).
- **Carga del dashboard batch sin defensa ante errores** (`professional.js`):
  `Promise.all` sobre 5 endpoints mapeaba `r.json()` sin verificar `response.ok`,
  de modo que un 4xx/5xx dejaba campos en `undefined` y rompía la promesa
  completa. Ahora usa `Promise.allSettled` + `if (!r.ok) throw` por petición y
  consume cada resultado por separado.
- **i18n: keys usadas pero ausentes de `translations.py`**: la UI mostraba la key
  cruda. Se añadieron `admin.active` y `pro.operation_type` (usadas en
  `templates/admin.html` y `templates/professional.html`) y
  `prof.export_leads_sheet` (usada en `routes/professional/exports.py`), ES/EN.

### Tests
- +1 `TestPythonTemplateI18nParity` en `tests/test_i18n.py`: escanea los `t()`
  de templates, `routes/`, `services/` y raíz y falla si alguna key no existe en
  `translations.py` (la paridad ES/EN del diccionario no cubría este caso).
  Discriminado: al remover `admin.active` el test falla nombrando la key.
  → **828 pytest / 94 coherence / 34 node**.

## [v0.48.5] — 2026-10-17 — Storage UTC canónico para timestamps de tracking/pipeline

### Corregido
- **Zona horaria inconsistente en `lead_tracking` / pipeline**: `tracking.py`
  escribía `seen_at`/`contacted_at` en ART y `models/pipeline.py` en hora local
  del servidor — el mismo campo dependía de quién lo escribiera y del host. En
  producción (UTC) el timeline trataba los valores ART como UTC (3 h corridos)
  y las ventanas SQL (`datetime('now')` = UTC) comparaban contra ART.
  **Storage canónico en UTC** (`utils.utc_now()` / `utc_now_str()`), siguiendo
  la convención de `leads.timestamp` y `events.ts`:
  - Writers: `tracking.py` (toggle) y los `now_str` de `move_lead_stage`(_batch).
  - Display convierte a hora Argentina: feed del dashboard como muro horario
    ART naive (`dashTimeAgo()` en JS parsea el string como hora local del
    navegador; la normalización se aplica antes del dedup changed↔contacted),
    XLSX y PDF de perfil en `dd/mm/yyyy`, timeline ya convertía.
  - `days_in_stage` y `get_pipeline_stats` restan ahora UTC a `updated_at`
    UTC (antes: hora local − UTC, daba 0 días en hosts con offset).
  - Ventanas SQL de 7/14/30 días quedan UTC↔UTC correctas.
- **Backfill v7** (`db_migrations.py`): `contacted_at` se convierte con
  `_to_server_local`. En servidores UTC (producción) la conversión es
  identidad y el histórico no cambia; filas legacy escritas en ART/local en
  hosts con offset quedan como mejor esfuerzo (la zona original no queda
  registrada). Migración v7 aplicada y verificada en la DB de desarrollo.
- `convert_to_argentina_time()` acepta `fmt` para consumidores que necesitan
  el formato crudo (`yyyy-mm-dd HH:MM:SS`).

### Tests
- +7 `tests/test_utc_storage.py` (writers, feed ART, dedup post-conversión,
  `days_in_stage`, backfill, export XLSX) → **827 pytest / 94 coherence /
  34 node**. Discriminados: con el código previo fallan 6/7 (delta exacto de
  3 h, `days_in_stage` 4≠5, backfill 19:00≠16:00, valores crudos en crudo).

## [v0.48.4] — 2026-10-17 — Revisión de bugs: 4 fixes críticos

### Corregido
- **SLA: mezcla UTC / hora local** (`services/sla.py`, `routes/professional/leads.py`,
  `db_migrations.py`): `leads.timestamp` y `events.ts` se guardan en UTC
  (`CURRENT_TIMESTAMP` de SQLite) pero los cálculos usaban `datetime.now()` local,
  con lo que las horas hábiles quedaban desfasadas por el offset del servidor
  (-3 h en Argentina; invisible en un servidor UTC). `_to_server_local()` /
  `_created_local()` normalizan a la tz del servidor en los 5 puntos de cálculo
  (primer contacto, recordatorios, KPI de admin, `sort=match` y backfill v7).
- **Rate limit: bucket aislado por endpoint** (`rate_limit.py`): la clave era solo
  la IP, así que tráfico de una ruta de límite alto llenaba el bucket compartido y
  disparaba 429 falsos en `send-code` (limit 5). Ahora la clave es `(endpoint, IP)`.
- **`escapeHtml` no escapaba comillas** (`static/js/main.js`): escapaba `& < >` pero
  no `"`/`'`, lo que permitía romper atributos HTML (XSS por inyección de atributo)
  con el CSP `unsafe-inline` vigente.
- **Índices únicos creados antes que su dedup** (`db_schema.py`, `db_migrations.py`):
  `create_tables()` corre antes que `apply_migrations()`, y crear
  `idx_lead_reports_pending_once` / `idx_notif_lead_created_once` antes del DELETE
  de dedup hacía reventar el arranque con `IntegrityError` en una DB con duplicados
  históricos — el dedup nunca llegaba a correr. Los índices ahora se crean solo en
  `apply_migrations()`, después de la limpieza (verificado en vivo: 2 filas → 1).

### Tests
- +5 `TestCreatedTimestampUtcNormalization`, +2 `TestRateLimitBucketIsolation`,
  +4 `escape_html.test.js` → **820 pytest / 94 coherence / 34 node**.

## [v0.48.3] — 2026-10-17 — Recordatorios suaves de SLA

### Añadido (Fase 3 — Recordatorios)
- **Recordatorio suave en el panel del profesional** (`templates/professional.html`,
  `static/js/professional.js`): tarjeta discreta debajo de los KPIs — "Tenés N
  solicitudes asignadas sin responder (· M vencidas)" — con un botón
  **Priorizar** que activa "Mejor match" (donde el SLA ya ordena) y un
  descartar por sesión. Se oculta sola cuando no hay nada pendiente.
- **`services/sla.py`**: `get_professional_reminders(conn, professional_id)` —
  cuenta los leads `assigned_to` al profesional, sin primer contacto, en estado
  `at_risk`/`breached`. Se calcula al momento: **sin scheduler, sin emails, sin
  escrituras**, coherente con el resto del SLA. Cuenta como contactado el primer
  contacto global o el `tracking.contacted` del propio profesional.
- `GET /api/leads` expone `sla_reminder` (`total`/`at_risk`/`breached`) sobre el
  conjunto asignado, independiente de la página y de los filtros.
- i18n `pro.sla_reminder_text` / `_breached` / `_action` / `_dismiss` (ES/EN).
- 7 tests (`TestProfessionalReminders`) + 2 de ruta (`TestSlaReminder`).

### Nota
- Se levanta **explícitamente** la restricción de "cero fricción" para esta
  feature; el recordatorio es in-app y silencioso (sin push, email ni ranking).

## [v0.48.2] — 2026-10-17 — SLA en el orden `sort=match`

### Añadido (Fase 3 — Priorización por SLA)
- **`sort=match` consciente del SLA** (`routes/professional/leads.py`): el orden
  pasa a ser `match_score` desc → urgencia SLA → id. Dentro del mismo score, los
  leads sin primer contacto en riesgo (`breached` > `at_risk`) suben, y los ya
  contactados (`lead_first_contact` o `tracking.contacted` propio) se hunden:
  **no se re-empujan**. El `match_score` sigue siendo la clave primaria (nunca
  deja de ser descendente), así que "mejor match" conserva su significado.
- Cada lead en modo match expone `sla_status`
  (`contacted` | `pending` | `at_risk` | `breached`) junto a `match_score`.
- **`services/sla.py`**: `classify_sla_status()` (puro) + constantes
  `DEFAULT_THRESHOLD_HOURS`, `AT_RISK_FRACTION` y `SLA_RANK`. `at_risk` = segunda
  mitad del plazo (12–24 h hábiles).
- Sin notificaciones ni cambios de UI → se mantiene "cero fricción" para el
  profesional (solo cambia el orden del listado cuando elige "Mejor match").
- 6 tests en `TestClassifySlaStatus` + 3 en `TestMatchSort`.

## [v0.48.1] — 2026-10-17 — SLA: línea base con datos backfilleados

### Añadido (Fase 3 — Línea base)
- **Ventana histórica completa** en `compute_sla_kpis()`: `days=None` agrega
  **todo** el histórico (sin filtro de fecha) → la línea base construida a partir
  de los datos backfilleados en `lead_first_contact` (responde "¿cuál es el
  cumplimiento actual?").
- **`GET /api/admin/sla?days=all`** (`routes/admin_bp.py`) → `days=None`; un
  `days` no numérico o fuera de 7/30/90 cae a 30.
- **Botón «Línea base»** en el panel SLA (`templates/admin.html` +
  `static/js/admin.js`): el período pasa a manejarse como string para admitir
  `all` (`data-days="all"` → `loadSla('all')`).
- i18n `sla.period_all` / `sla.period_all_hint` ES/EN (`translations.py`).
- 2 tests en `TestComputeSlaKpis` (ventana all-time + lead antiguo que solo
  aparece en la línea base) + 2 en `TestAdminSla` (`?days=all`, `days=abc`).

## [v0.48.0] — 2026-10-17 — SLA: compromiso de respuesta al cliente

### Añadido (Fase 3 — Compromiso de respuesta comunicado al cliente)
- **`services/sla.py`**: `get_response_commitment()` (mediana de horas hábiles
  hasta el primer contacto en 90 días) con decisión pura `_commitment_from()`:
  solo muestra un número si hay muestra suficiente (`>=5`) y es razonable
  (`<=48 h`); caso contrario devuelve `available=False` para usar el texto
  genérico. Nunca expone un valor que pueda sonar mal.
- **`GET /api/profile/leads`** ahora incluye `sla_commitment` (`available`,
  `hours`, `sample`) sin romper la lista si el cálculo falla.
- **Banner en el panel "Mis Solicitudes"** (`templates/profile.html` +
  `renderSlaCommitment()` en `static/js/profile.js`): "Nuestros profesionales
  suelen contactarte en ~X horas hábiles" o el texto genérico.
- i18n `sla.client_commitment` / `sla.client_commitment_generic` ES/EN en
  `translations.py` e `i18n.js`.
- 7 tests puros en `TestGetResponseCommitment` + 1 en `test_profile.py`.

### Arreglado (Fase 3 — consistencia de la mediana/P90 del KPI)
- `compute_sla_kpis()` calculaba median y P90 sobre **todos** los contactos
  históricos, mientras `met`/`breached` sí estaban acotados a la ventana: los
  tres percentiles podían no corresponder al mismo conjunto. Ahora la query de
  contactos se une a `leads` y filtra por ventana (además baja la carga al no
  traer contactos fuera de rango).

## [v0.47.3] — 2026-10-17 — SLA: KPI de pendientes vs incumplidos

### Arreglado (Fase 2.1 — KPI de SLA: pendientes vs incumplidos)
- **`compute_sla_kpis()`** ahora clasifica cada lead de la ventana en
  `contacted` (con contacto), `pending` (asignado, sin contacto, **en plazo**),
  `breached` (contactados tarde **+** asignados sin contacto ya vencidos) y
  `unassigned` (sin profesional asignado o asignado inactivo). El `%` de
  cumplimiento pasa a `met / (met + breached)`, que es la definición correcta
  (antes `unassigned` absorbía también los pendientes y los vencidos sin
  contacto, inflando la tarjeta "Sin asignar").
- La tarjeta "Contactados" del panel se reemplaza por **"Pendientes"** (la
  información de contactados sigue en las tablas de desglose).
- 6 tests en `TestComputeSlaKpis` (deltas sobre la DB compartida: pending,
  breached por antigüedad, met/breached según `business_hours_elapsed`, y
  profesional inactivo → unassigned).

## [v0.47.2] — 2026-10-17 — SLA: panel de cumplimiento en admin

### Añadido (Fase 2 — Panel SLA en el dashboard admin)
- **Pestaña "SLA de contacto"** en `templates/admin.html` (`#panel-sla`): tarjetas de
  cumplimiento, mediana, P90, pendientes, incumplidos y sin asignar, más tablas
  de desglose por profesional y por zona. Selector de período 7/30/90 días.
- **`static/js/admin.js`**: `loadSla()` / `renderSla()` consumen `GET /api/admin/sla`,
  con estado activo del período y escape HTML en nombres de usuario/zona.
- **i18n**: claves `sla.*` y `admin.sla` en `i18n/translations.py` (ES/EN) y
  `static/js/i18n.js` (ES/EN); paridad verificada por `TestJsI18nParity`.
- 1 test nuevo (render del panel en `/admin`).

## [v0.47.1] — 2026-10-17 — SLA: KPI y endpoint de cumplimiento

### Añadido (Fase 1 — KPI de cumplimiento + endpoint admin)
- **`compute_sla_kpis()`** (`services/sla.py`): cumplimiento (%), mediana y p90
  de horas hábiles hasta el primer contacto, con desglose por profesional y por
  zona. `unassigned` (sin señal) queda fuera del % para no sesgar.
- **Endpoint `GET /api/admin/sla?days=30&threshold=24`** (`routes/admin_bp.py`,
  `@admin_required`): ventana 7/30/90 (default 30), umbral configurable. 3 tests en
  `TestAdminSla` (auth, shape del JSON, fallback de `days` inválido).

## [v0.47.0] — 2026-10-17 — SLA: instrumentación de primer contacto

### Añadido (Fase 0 — SLA de primer contacto: instrumentación)
- **Tabla `lead_first_contact`** (`db_schema.py` + migración v7): PK `lead_id`
  (idempotente), `professional_id`, `contact_at`, `source`, y
  `business_hours_elapsed` precalculado. Índices en `contact_at` y `professional_id`.
- **`services/sla.py`**: `record_first_contact()` idempotente (gana la primera
  señal) y `business_hours_between()` puro (lun–vie 09:00–18:00, tz del servidor).
- **Marcaje en 4 fuentes**, siempre post-commit con conexión propia (fuera de la
  transacción crítica): move a etapa `contacted`+ (`models/pipeline.py`), toggle
  a contacted (`routes/professional/tracking.py`), reveal de teléfono y link de
  WhatsApp (`routes/lead_bp.py`), y click en llamar/SMS (`whatsapp_event`).
- **Backfill** (`_backfill_first_contact` en `db_migrations.py`, versión 7):
  registra la primera señal histórica por lead desde `lead_tracking.contacted_at`
  y `events`. Leads sin señal quedan `unassigned` y no sesgan el KPI.
- 17 tests en `tests/test_sla.py` (horas hábiles, marcaje idempotente, backfill).

## [v0.46.1] — 2026-10-17 — Revisión total de sistema

### Arreglado (Revisión total de sistema)
- **Webhook WhatsApp exento de CSRF real** (`factory.py`): `WTF_CSRF_EXEMPT_LIST`
  no existe en Flask-WTF, el webhook rechazaba en producción (en tests CSRF va
  apagado). Ahora usa `csrf.exempt(whatsapp_bp)`.
- **IDOR en lead por ID** — decoradores `admin_required`/`professional_required`
  responden JSON 401/403 cuando se pide JSON (antes siempre redirect 302),
  para que los clientes API no caigan en loops de login.
- **Path traversal en descarga de docs** (`routes/admin_bp.py`,
  `routes/professional/docs.py`): validación de `basename` sin `..` en
  `doc_path`.
- **Dedup con cierre de carrera** (`routes/client_bp.py`): si dos requests
  concurrentes insertan la misma búsqueda, el perdedor se borra y responde 409
  con el `existing_lead_id` ganador, sin notificar de más.
- **Email duplicado en perfil** (`routes/profile/core.py`): `PUT /api/profile/user`
  con email de otra cuenta → 409 `profile.email_taken` (antes 500 o duplicado).
- **Rate limits** en endpoints mutantes sin protección: report lead, toggle
  status, pipeline move/bulk-move, calendario CRUD/move/complete, exports
  CSV/XLSX/PDF, whatsapp-event, contact-admin, reset-password. 429 ahora
  i18n-keyed (`error.rate_limited`).
- **`/health`** cierra la conexión en `finally` (antes podía filtrar).
- **Aviso de fallback de cobertura** y seeds: `phone_area_codes` definido en
  `db_schema.py` (antes solo en seeds); admin seed tolera carrera multi-worker.
- **Frontend**: approve/reject pisaba la columna de org (`main.js`, celda 5);
  XSS/attribute-breakout en `sms:` link y `o.icon` (`professional.js`,
  `form-options.js`); campos de budget sin null-check (`budget.js`); duplicados
  `data-period` (`admin.html`); escape de IP/fecha en sesiones y actividad
  (`profile.js`); confirmación antes de descartar reporte (`admin.js`).
- **i18n**: keys faltantes `org.remove_member`, `user.search_city`,
  `admin.loading`, `dashboard.call_clicks` (con `{count}`), `error.rate_limited`;
  español hardcoded en `admin.html`/`profile.html` movido a keys; gate de
  paridad `TestJsI18nParity` valida que toda key usada en JS exista en `i18n.js`.

## [v0.46.0] — 2026-10-16 — Priorización por match

### Añadido (Fase 5 — Priorización por match)
- **`sort=match` en `GET /api/leads`** (`routes/professional/leads.py`): puntúa con
  `score_lead_for_coverage`, ordena desc y pagina en memoria (tope 5000, default
  intacto, "Todos" siempre disponible). Respuesta incluye `match_score` solo en
  ese modo.
- **Opción "Mejor match"** en el select de orden (`templates/professional.html`,
  key `pro.sort_match` ES/EN) + 3 tests en `TestMatchSort`.

---

## [v0.45.0] — 2026-10-16 — Dedup real de leads

### Añadido (Fase 4 — Dedup real de leads)
- **409 ante búsqueda duplicada** (`routes/client_bp.py`): mismo usuario + tipo +
  zona + teléfono en 90 días → `409 {duplicate, existing_lead_id}`. Nunca bloquea:
  `allow_duplicate: true` crea igual (misma idempotency key).
- **Flujo Retomar/Crear igual** (`static/js/forms.js`): ante 409, `showConfirm` —
  Cancelar va a `/mi-perfil`, Aceptar reintenta con `allow_duplicate`.
- Keys `client.duplicate_*` ES/EN (py + js) + 4 tests en `TestLeadDedup`.

---

## [v0.44.0] — 2026-10-16 — Timeline unificado por lead

### Añadido (Fase 3 — Timeline unificado)
- **Timeline por lead** (`models/timeline.py`, `routes/professional/timeline.py`):
  `GET /api/leads/<id>/timeline` agrega creación, pipeline, tracking, versiones,
  telemetría y reportes en una lista cronológica (solo lectura). Visible también
  en `/profesional/lead/<id>` (sección Historial, server-render, sin JS nuevo).
  Keys i18n `timeline.*` ES/EN + `tests/test_timeline.py` (5 tests).

---

## [v0.43.3] — 2026-10-16 — Fixes P1 robustez
- **OTP anti-abuso** (`routes/phone_bp.py`): `send-code` 100→5 req/min (frena
  SMS-bombing), `verify` 100→10 req/min (el lockout de 5 intentos ya existía).
- **Tests node en el repo**: `tests/package.json` (`commonjs`) — `node --test`
  verde in-situ (30/30).
- **Hilo de notificación con app context** (`routes/client_bp.py`): render de
  emails e i18n con contexto explícito en vez de fallbacks.

---

## [v0.43.2] — 2026-10-16 — Fixes P0 concurrencia

### Corregido (Fase 1 — P0 concurrencia)
- **Notificaciones fuera de la transacción** (`services/notifications.py`): el batch hace
  inserts + `commit` primero y envía SMTP/WhatsApp después — el lock de SQLite ya no
  queda abierto durante I/O lento.
- **Poda de `idempotency_keys`** (`routes/client_bp.py`): placeholders huérfanos >1h y
  keys >30 días se eliminan en cada submit.
- **Toggle atómico** (`routes/professional/tracking.py`): flip en una sola sentencia
  (`UPDATE ... 1 - x ... RETURNING`), sin ventana leer-y-escribir.
- **`restore_report` ante duplicado** (`routes/admin_bp.py`): violación del índice
  único → 400 en vez de 500.
- **Bulk-move transaccional** (`models/pipeline.py`): `move_lead_stage_batch()` en una
  sola transacción all-or-nothing (ids inexistentes se ignoran).

---

## [v0.43.1] — 2026-10-16 — Idempotencia y dedup (concurrencia)

### Añadido
- **Idempotencia en `POST /api/submit`**: header `X-Idempotency-Key` (o `idempotency_key` en body) con tabla `idempotency_keys`; reintentos con la misma key retornan el lead existente (`deduplicated: true`) sin insertar ni notificar de más. Incluye `lead_id` en la respuesta.
- **Backstops únicos parciales**: `idx_lead_reports_pending_once` (un pending por profesional+lead) e `idx_notif_lead_created_once` (una notificación de creación por profesional+lead), con limpieza de duplicados históricos en la migración.

### Corregido
- **Doble-submit frontend**: guard `submitting` + key UUID por formulario en `forms.js` (doble click / Enter repetido).
- **`auto_assign_lead` atómico**: `UPDATE ... WHERE assigned_to IS NULL`; el perdedor de una carrera relee al ganador.
- **`notify_lead_created` idempotente**: `INSERT OR IGNORE` + solo envía email/WhatsApp si el insert ganó; segunda ejecución no duplica ni reenvía.
- **`notify_lead_status_change` con dedup de ventana (5 min)** por mismo estado: cubre admin y cliente sin suprimir `visto`→`contactado` legítimos.
- **`report_lead` ante carrera**: violación del índice único → 400 `already_reported` en vez de 500.
- **`toggle-status` ante carrera**: INSERT en conflicto → relee y aplica el flip (sin 500).
- **`move_lead_stage` no-op**: mismo origen y destino no escribe historial ni toca tracking.
- **Calendario**: guard `calSaving` en `saveCalEvent` (doble click no duplica eventos).
- **Test de teardown**: robusto al contexto ambiente del plugin pytest (verifica cierre real).

---

## [v0.43.0] — 2026-10-15 — Testing Fase 6 (Auditoría)

### Añadido
- **103 tests nuevos**: `test_admin_bp` (21: approval, leads, reports, usuarios, notificaciones), `test_errors` (24: handlers 400–504 HTML+JSON), `test_security` (30: scan XSS + atomicidad), `test_export_helpers` (9), `test_matching` (11), `test_middleware` (8: remember, conn scoped, idioma).
- **Scan XSS como test**: campos controlados por usuario deben interpolarse con `escapeHtml`/`escapePipelineHtml` (detectó y corrigió `data-label` del panorama).
- `verify_coherence.py` sigue al split (lee `db_schema.py` + subpaquetes de rutas).
- Suite: **727 pytest** + 30 node verdes, coherencia 94/94.

### Corregido
- **Deadlock SQLite del batch F2**: `log_action` reutiliza `notif_conn` (writes sin commit bloqueaban su propia conexión).

---

## [v0.42.0] — 2026-10-15 — Calidad Fase 3 (Auditoría)

### Cambiado
- **Splits**: `models.py` → paquete `models/` (10 módulos + re-exports); `app_setup.init_db` → `db_schema` + `db_migrations` + `db_seeds` (schema verificado idéntico en DBs frescas); `professional_bp` → `routes/professional/` (9 módulos) y `profile_bp` → `routes/profile/` (6 módulos), todos <500 líneas, blueprint names intactos.
- **`config.py`** usa `dotenv.load_dotenv()`; **`lead_bp`** reutiliza `rate_limit.check_rate()` (store único; `conftest` simplificado).
- **SQL**: `date_format_sql()` con allowlist, `top()` validado (ORDER BY ya allowlisteado).
- **Nombres**: `delete_reported_lead` → `mark_report_deleted`.
- **Sin `pass` silenciosos**: 17 bloques ahora loguean (debug/warning/exception según criticidad).
- Suite parcial: 120+76+52+42 passed en subsets por split.

---

## [v0.41.0] — 2026-10-15 — Performance Fase 2 (Auditoría)

### Cambiado
- **N+1 eliminados**: `get_professional_coverage_batch()` (2 queries) en `auto_assign_lead`; `_create_notification()` acepta `conn` y `notify_lead_created` inserta en batch con 1 conexión.
- **Conexiones request-scoped**: `models.get_db_connection()` cachea en `g` con proxy de close no-op; `close_db_connection` cierra ambas en teardown.
- **Índices**: `idx_leads_assigned`, `idx_leads_property_type`, `idx_lead_reports_lead_reported`, `idx_notifications_user_created`.
- **`table_columns()`** reutiliza la conexión del request en vez de abrir raw.
- Suite parcial: 46 passed (assignment, notifications, database).

---

## [v0.40.0] — 2026-10-15 — Seguridad Fase 1 (Auditoría)

### Corregido
- **Connection leak**: `restore_session_from_remember_cookie` cierra su conexión (`try/finally`).
- **Atomicidad**: `update_lead_versioned()` (versión + UPDATE en 1 transacción) y `update_user_account()` (email + teléfono + perfil en 1 transacción); rutas responden 500 si falla.
- **Confirm nativo**: último `confirm()` (`deletePhoneAreaCode`) migrado a `showConfirm()`.
- **FK constraints**: `PRAGMA foreign_keys = ON` en SQLite fuera de tests (gating por `PYTEST_CURRENT_TEST`; deletes verificados seguros).

### Verificado (sin cambio necesario)
- **XSS `admin.js`**: re-auditoría completa — todas las interpolaciones de datos usan `escapeHtml()` (profesionales, reportes, lead detail, form options, miembros, area codes, log).
- Suite parcial: 48 passed (remember, admin, notifications).

---

## [v0.39.0] — 2026-10-15 — Frontend Fase 5 (Auditoría)

### Añadido
- **Módulos JS**: `main.js` (1587→393 líneas) partido en `toasts.js`, `modals.js`, `forms.js`, `budget.js`, `scroll.js` (cargan tras `main.js` en `base.html`); `shared/chips.js` elimina la duplicación user/edit_lead.
- **IIFE por archivo** con `window.*` explícito como única API pública; verificado por script (42/42 declaraciones únicas, exports resueltos, sin referencias cruzadas rotas).
- **Cero handlers inline**: 189 `onclick` + 48 `on*` + 54 generados por JS migrados a `delegateActions(map, event)` (`click`/`change`/`input`/`keydown`/`keyup`/`mouseover`) con `data-action`; CSP sin `unpkg.com`.
- **Assets locales**: Lucide v0.468.0 self-hosted, hero `static/img/hero.jpg` (también `og:image`), sin preload redundante de fonts, `width/height` + `fetchpriority` en hero.
- **Higiene**: `escapeHtml` único (el fallback muerto de `auth.js` eliminado), 20 `catch` vacíos con `console.error` (+ toast donde hay acción de usuario).

### Corregido
- Tests JS adaptados a módulos IIFE (stubs + `window.*`, carga de `forms.js`); indietro: `combineCountryAreaPhone` y callers de coverage/teléfono.
- Suite: 624 pytest + 30 node verdes, coherencia 94/94.

---

## [v0.38.0] — 2026-10-15 — i18n Fase 4 (Auditoría)

### Añadido
- **i18n completo en templates** — 0 líneas de español hardcoded en 19 templates/emails (verificado por test de scan):
  - 72 keys nuevas ES/EN (`user.*`, `otp.*`, `admin.*`, `profile.*`, `seo.*`, `landing.*`, `pro.pt_*`, `auth.*`, `edit_lead.*`, `email.*`, `contact.*`); total 1300/1300 con paridad.
  - `user.html`, `admin.html`, `profile.html`: labels, tooltips, aria-labels, placeholders, OTP (`otp.digit_label` con interpolación `{n}`).
  - `base.html`: meta/OG/Twitter description + keywords + JSON-LD (`@graph`) traducidos; `og:locale` e `inLanguage` dinámicos (`es_AR`/`en_US`).
  - `landing.html`: título + JSON-LD Organization/FAQ (reutiliza keys `faq.*` del cuerpo, fuente única).
  - `professional.html`: chips de tipo de propiedad + headers de tabla.
  - `login.html`/`register.html`: `data-auth-rules` traducidos (validados como JSON tras render).
  - `contact_buttons.html`: aria-labels + mensaje de WhatsApp por idioma (verificado ES/EN).
  - Emails: `professional_status`, `status_change`, `report_deleted` (subjects backend ya usaban `t()`).
- Tests nuevos en `tests/test_i18n.py`: scan anti-hardcode (con whitelist documentada: valores de formulario, strings de lógica, nombres nativos), keys fase 4, render EN (register/login/`og:locale`). Total suite: 624 passed, coherencia 94/94.

---

## [v0.37.0] — 2026-10-15 — Multi-Tenant (Fase 4)

### Añadido
- **Miembros de organización con roles** — tabla `org_members` (org_id, user_id, role, UNIQUE) con roles `owner`/`admin`/`member`, índices y backfill desde `professionals.org_id` (`app_setup.py`).
- `models.py`: `ORG_ROLES`, `get_org_members`, `add_org_member`, `remove_org_member`, `set_member_role`, `get_user_orgs`, `get_my_org`; sync bidireccional con `professionals.org_id`; cascada en deactivate/delete; `member_count` cuenta `org_members`.
- API admin en `routes/organizations_bp.py`: `GET/POST /api/admin/organizations/<id>/members`, `PUT/DELETE .../members/<user_id>` (todo `@admin_required`, i18n ES/EN); `POST /api/admin/organizations` acepta `slug` opcional (duplicado explícito → 409).
- API profesional en `routes/professional_bp.py`: `GET /api/professional/my-org` (org + miembros) y `GET /api/professional/org-leads` (pool compartido, límite 100).
- UI admin: conteo de miembros clicable + modal de miembros (alta por ID + rol, cambio de rol, baja) (`admin.html`, `admin.js`); 25 keys i18n ES/EN (`org.*`) en `translations.py` + `i18n.js`.
- Tests nuevos: `tests/test_multitenant.py` (15 tests CRUD/miembros/roles/pool/permisos). Total suite: 618 passed, coherencia 94/94.

---

## [v0.36.1] — 2026-10-15

### Añadido
- **Panorama de solicitudes** — `GET /api/leads/panorama` (total, `my_total`, top zonas/provincias/países); el estado vacío de Mis leads muestra el panorama con chips que aplican zona + Todos.
- **Mini-feed de actividad** en tabs Leads (colapsable debajo de la tabla), Stats y Calendario (sidebar), con "Ver todo" al Dashboard; se refresca con filtros y movimientos.
- **Barra global de filtros** en vista profesional (buscador + Mis/Todos + limpiar, sincronizada con el panel de Leads) + filtro por tipo en Calendario.
- **Botón Reiniciar cobertura** en Mi perfil (`DELETE /api/profile/professional/coverage`, con confirmación).
- Keys i18n ES/EN: `leads.panorama*`, `leads.empty_my_leads`, `leads.show_all`, `dash.view_all`, `cal.invalid_range`, `pagination.prev/next`, `profile.coverage_reset*`, `admin.save`, `error.required_fields`.

### Corregido
- Duplicados en feed de actividad (move→contactado generaba 2 eventos; tarjeta duplicada en Dashboard).
- Calendario: todo el día deshabilita horarios; fin posterior a inicio (cliente + servidor); color deriva del tipo.
- Login dark: contraste del ojo, inputs underline transparentes, labels gold-light.
- `api/submit` 400 por presupuesto `"0 - max"` (se envía max-only); log de motivo en `_reject`.
- `FLASK_DEBUG=true` vs `== '1'` (CSP/cookies caían en prod); `calendar-arrow-left` → `history`; sourcemap fantasma de Chart.js.
- Funciones de leads a scope global (inline onclick + Pipeline); scroll arriba al cambiar de tab; preview con fallback a detalle.
- Password de perfil en `<form>` real (gestores de claves); modales admin con frame flex sin saltos.
- Suite: 603 passed, coherencia 94/94.

### Añadido (previo sin release)
- **Coverage de profesionales** — sistema de cobertura para matching de leads:
  - Tabla `professional_coverage` + índice `idx_pro_coverage_user` (creados en `app_setup.py`).
  - `get_professional_coverage()` / `set_professional_coverage()` en `models.py` con fallback legacy a `zone`/`specialty` y flag `configured`.
  - `services/matching.py` (nuevo): `score_lead_for_coverage` y `lead_matches_coverage` con pesos (specialty exacta 100 / parcial 50, zona 30, provincia 20, `MIN_MATCH_SCORE = 1`).
  - `services/assignment.py`: `auto_assign_lead` reescrito con scoring compartido; sin asignación forzada si ningún profesional matchea (queda `assigned_to = NULL`).
  - `/api/leads` expone `matches_coverage`; `_get_pro_geo_filter` filtra por provincia/país + zonas de cobertura multi-zona.
  - `GET/PUT /api/profile/professional/coverage` (permite hasta `MAX_COVERAGE_VALUES = 20` valores).
  - Tests nuevos: `test_assignment.py`, `test_professional_leads.py` (`TestMatchesCoverageBadge`), `test_profile.py` (`TestProfessionalCoverageAPI`).

### Cambiado
- Headers de export CSV/XLSX de profesionales ahora incluyen columna `ID` y usan `.split(',')` sobre los headers guardados en DB.

### Corregido
- **Stats vacías** en vista de profesional: estado vacío explícito (`renderStatsSection` + `#statsEmptyState`) y fin del auto-select en bucle al cambiar mes.
- **CSRF**: inputs `csrf_token` faltantes en `forgot_password.html` y `reset_password.html`.
- **Remember 30 días**: `PERMANENT_SESSION_LIFETIME` alineado con `REMEMBER_TOKEN_DAYS`; `session.permanent = True` solo con el checkbox "recordarme".
- **Notificaciones admin→profesional**: `actor_id` registrado correctamente (broadcast e individual) y modal usa `user_id` real (`openNotifyModal`).

---

## [v0.36.0] — Calendario (Fase 3)

### Añadido
- **Calendario** — 4to tab en `/profesional` (Leads | Dashboard | Stats | Calendar):
  - Tabla `calendar_events` (professional_id, lead_id nullable, title, description, event_date, start/end_time, event_type, location, color, all_day, completed) con índices (`app_setup.py`).
  - API en `routes/professional_bp.py` (todo `@professional_required` + cuenta aprobada): `GET /api/calendar/events?month=|start=&end=`, `POST`, `PUT/DELETE /api/calendar/events/<id>`, `POST .../move`, `POST .../complete`, `GET .../upcoming?days=&limit=` (validación de fecha/hora/tipo/lead).
  - `models.py`: `CALENDAR_EVENT_TYPES`, CRUD + `get_upcoming_events` (solo eventos propios).
  - UI: vista mes (grid 42 celdas, pills, +N), semana (grilla horaria con bloques posicionados) y día, mini-calendario navegable, próximos 7 días, modal crear/editar con chips de tipo, búsqueda de lead y borrado; vista en `localStorage` (`professional.html`, `professional.js`, `professional.css`); 35 keys i18n ES/EN (`cal.*`).
  - Tests nuevos: `tests/test_calendar.py` (9 tests CRUD/move/lead/upcoming/permisos).
- **Corregido**: `admin.save` no existía como key (mostraba la key cruda en modales de admin).

## [v0.35.0] — Dashboard Ejecutivo (Fase 2)

### Añadido
- **Dashboard Ejecutivo** — 3er tab en `/profesional` (Leads | Dashboard | Stats), cálculo en tiempo real (sin tabla de snapshots):
  - API en `routes/professional_bp.py` (todo `@professional_required` + cuenta aprobada, respeta `?my_leads=`): `GET /api/dashboard/summary` (total, nuevos hoy/semana, contact_rate, pipeline_active, avg_budget, vs_last_week, top_zone/type), `GET /api/dashboard/trends?days=30` (serie diaria con ceros), `GET /api/dashboard/pipeline` (funnel por etapa), `GET /api/dashboard/activity?limit=20` (moves + contacted/seen, click abre preview), `GET /api/dashboard/top-metrics` (zonas, tipos propiedad/operación).
  - UI: 6 KPI cards, tendencia Chart.js línea 30d, funnel con barras por color de etapa, barras top zonas, dona tipos propiedad, feed de actividad con tiempo relativo; respeta filtros/Mis leads (`professional.html`, `professional.js`, `professional.css`); 15 keys i18n ES/EN (`dash.*`).
  - Tests nuevos: `tests/test_dashboard.py` (7 tests summary/trends/pipeline/activity/vacío/top-metrics/permisos). Total suite: 585 passed.

## [v0.34.0] — Pipeline Kanban (Fase 1)

### Añadido
- **Pipeline Kanban** — tablero de 8 etapas por profesional en `/profesional` (toggle Lista | Pipeline):
  - Tablas `lead_stages` (professional_id, lead_id, stage, updated_at, UNIQUE) + `lead_stage_history` (from/to, changed_at) con índices (`app_setup.py`).
  - API en `routes/professional_bp.py` (todo `@professional_required` + cuenta aprobada): `GET /api/pipeline/stages`, `GET /api/pipeline/leads?stage=X` (filtros search/type/property_type/zone + `my_leads`, `days_in_stage`), `POST /api/pipeline/lead/<id>/move`, `POST /api/pipeline/leads/bulk-move`, `GET /api/pipeline/stats` (conteos + días promedio en etapa + movimientos).
  - `models.py`: `PIPELINE_STAGES`, `get_lead_stage`, `get_pipeline_counts`, `move_lead_stage` (upsert + historial + `lead_tracking.contacted=1` desde `contacted`), `get_pipeline_stats`.
  - UI: 8 columnas con conteos, cards con dots de días en etapa, drag & drop nativo (HTML5, sin dependencias), click en card abre el preview existente; respeta filtros actuales (`professional.html`, `professional.js`, `professional.css`); 18 keys i18n ES/EN (`pipeline.*`).
  - Tests nuevos: `tests/test_pipeline.py` (13 tests move/historial/upsert/stages/stats/bulk/permisos). Total suite: 578 passed.

## [v0.33.0] — 2026-10

### Añadido
- **Organizaciones (Fase 4)** — gestión de organizaciones con pool de leads compartido:
  - Tabla `organizations` (name, slug único, description, is_active) + `org_id` nullable en `professionals` y `leads` con índices (`app_setup.py`).
  - CRUD en `models.py`: `create/get/update/deactivate/delete_organization`, `set_professional_organization`, `set_lead_organization` (validan org activa; deactivate/delete desasignan en cascada).
  - Blueprint nuevo `routes/organizations_bp.py`: `GET/POST /api/admin/organizations`, `PUT/DELETE /api/admin/organizations/<id>`, `POST .../deactivate`, `PUT /api/admin/professionals/<id>/organization`, `PUT /api/admin/leads/<id>/organization` (todo `@admin_required`, i18n ES/EN).
  - Profesionales con `org_id` ven los leads de su org en `my_leads=1` (pool compartido); `matches_coverage` se sigue calculando como señal informativa (`professional_bp.py`).
  - UI admin: tab Organizaciones + modal crear/editar + selects de org en profesionales y detalle de lead (`admin.html`, `admin.js`); 24 keys i18n ES/EN (`org.*`, `admin.org_*`).
  - Tests nuevos: `tests/test_organizations.py` (13 tests CRUD/permisos/slug) + `TestOrgScopedLeads` en `test_professional_leads.py` (4 tests). Total suite: 560 passed.

### Corregido
- **Paridad i18n JS**: 10 claves usadas por el CRUD de organizaciones (`admin.org_*`, `org.name_required`, `success.saved`) agregadas a `static/js/i18n.js` (ES/EN); sin esto la UI mostraba las keys crudas.

---

## [v0.31.3] — 2026-08

### Corregido
- Carga de notificaciones fallaba con `pages<=1` (`querySelector('.font-serif p')` → null). Commit `15866a4`.

## [v0.31.2]

### Añadido
- Scroll reveal extendido, transición de tabs/paneles y micro-interacciones hover. Commit `d0c905c`.

## [v0.31.1]

### Corregido
- Tokens de movimiento auto-referenciales dejaban vistas vacías y forgot-password roto. Commit `f3ed49e`.

## [v0.31.0]

### Añadido
- Motion language — tokens de movimiento, a11y reduced-motion y perf. Commit `8f02ca7`.

## [v0.30.2]

### Corregido
- Dropdown de búsqueda de ciudad sin desborde horizontal en móvil (<=480px). Commit `14ca1a1`.

## [v0.30.1]

### Cambiado
- Docs: README actualizado (528 tests, multi-país, roadmap). Commit `bb20ec5`.

## [v0.30.0]

### Añadido
- Teléfono multi-país — módulo `PhoneSuggest`, 10 países y validación backend. Commit `b514ee7`.

## [v0.29.1]

### Cambiado
- Docs: tabla de tags actualizada (118 versiones, cobertura completa). Commit `b6d489c`.

## [v0.29.0]

### Añadido
- Suite de animaciones, pulido de interfaz y autocompletado telefónico (búsqueda única de ciudad, fix número inválido). Commit `b51b3a4`.

## [v0.28.8]

### Cambiado
- Separar `requirements-dev`, completar `.env-example` y actualizar docs. Commit `63393a9`.

## [v0.28.7]

### Añadido
- 59 tests (assignment, webhook, database, client, public, profile). Commit `999c715`.

## [v0.28.6]

### Corregido
- Deprecación `datetime.utcnow`, logger duplicado, logging silencioso. Commit `284105e`.

## [v0.28.5]

### Cambiado
- Renombrar `export_helpers` y consolidar allowlist profesional. Commit `766fc2a`.

## [v0.28.4]

### Cambiado
- i18n: páginas de error 409/410/413/429 y rate limit traducidas. Commit `253d4d8`.

## [v0.28.3]

### Corregido
- No limpiar datos de prueba en producción + cache de filtros. Commit `f86df81`.

## [v0.28.2]

### Cambiado
- Docs: README con `phone_area_codes`, admin password, conteo de tests. Commit `5c08ffb`.

## [v0.28.1]

### Corregido
- Migrar autocomplete a DB, admin password, validación duplicada, seed. Commit `dcd4c9e`.

## [v0.28.0]

### Corregido
- Parsing de cookies, `now_sql` con formato, email sender y paths en tests. Commit `91f97d9`.

## [v0.27.1]

### Añadido
- Diferenciar notificaciones por tipo (iconos, colores, badge). Commit `62beec1`.

## [v0.27.0]

### Añadido
- Tests CRUD para `phone_area_codes` (20 tests). Commit `21379fe`.

## [v0.26.11]

### Añadido
- Datos de DB para selects de provincia + i18n. Commit `1e397d4`.

## [v0.26.10]

### Añadido
- Pestaña admin de códigos de área con buscador y CRUD. Commit `b9d3eca`.

## [v0.26.9]

### Añadido
- Tabla `phone_area_codes`, modelos CRUD y API admin. Commit `83524a3`.

## [v0.26.8]

### Cambiado
- Cargar `phone-areas.js` en tests de sugerencia telefónica. Commit `0b9c6d0`.

## [v0.26.7]

### Corregido
- Atributos de accesibilidad `tel` al formulario de registro. Commit `dd44ffb`.

## [v0.26.6]

### Corregido
- Selects dinámicos de provincia y detección de ciudad. Commit `f3983cc`.

## [v0.26.5]

### Añadido
- Diccionario de códigos de área argentinos. Commit `d9058ee`.

## [v0.26.4]

### Corregido
- Bug de extracción de código de área en `formatPhoneWithCountry`. Commit `e971897`.

## [v0.26.3]

### Corregido
- Asegurar prefijo `9` en lead form y profile phone flows. Commit `b300cee`.

## [v0.26.2]

### Corregido
- Anteponer siempre el `9` para números argentinos. Commit `cd9764c`.

## [v0.26.1]

### Añadido
- Filtro por provincia, label dinámico estado/provincia, página de notificaciones. Commit `52e173b`.

## [v0.26.0]

### Añadido
- i18n: claves para country selector y notificaciones. Commit `c27ac12`.

## [v0.25.12]

### Añadido
- Admin: pestaña de notificaciones con toggles y send log. Commit `3567fe2`.

## [v0.25.11]

### Añadido
- Panel de historial de notificaciones expandible con paginación/delete. Commit `2167d45`.

## [v0.25.10]

### Añadido
- API de historial de notificaciones con delete y paginación. Commit `11f9c26`.

## [v0.25.9]

### Añadido
- Country en perfil de profesional, geo filters y notificaciones. Commit `1efab5e`.

## [v0.25.8]

### Añadido
- Country selector en el formulario de lead con provincias dinámicas. Commit `09ca267`.

## [v0.25.7]

### Añadido
- Categoría de form options "country", seed de 11 países, migraciones DB. Commit `f96f027`.

## [v0.25.6]

### Corregido
- CSS `.field-error` duplicado en `user.css`. Commit `6837e41`.

## [v0.25.5]

### Cambiado
- Teardown_appcontext como safety-net (connection-per-request). Commit `bb64273`.

## [v0.24.4]

### Corregido
- Batch de queries N+1 en `auto_assign_lead`. Commit `978ad87`.

## [v0.24.3]

### Añadido
- Cache in-memory para `user_preferences` y `form_options` (TTL 60s). Commit `bd2f1b4`.

## [v0.24.2]

### Cambiado
- Eliminar queries de DB duplicadas en decoradores de auth (`g.user`). Commit `d623a65`.

## [v0.24.1]

### Corregido
- Quick wins: eliminar `sleep`, `print` → logger, consolidar conexiones de login. Commit `4819d68`.

## [v0.24.0]

### Añadido
- Paginación, asignación automática de leads y notificaciones internas. Commit `de3aadd`.

## [v0.23.1]

### Cambiado
- `.gitignore` mejorado para safe git pull. Commit `9abcaf0`.

## [v0.23.0]

### Corregido
- 12 security/quality fixes — webhook, XSS, N+1, CSRF, PDF, rate limiting. Commit `4ad4e4b`.

## [v0.22.1]

### Cambiado
- Docs: README actualizado (CSRF, password recovery, DevOps, Twilio fixes). Commit `9f2b55a`.

## [v0.22.0]

### Añadido
- Protección CSRF con Flask-WTF. Commit `a654093`.

## [v0.21.2]

### Añadido
- DevOps: script de backup, CI/CD, Sentry, Dependabot, staging. Commit `88feac6`.

## [v0.21.1]

### Añadido
- Flujo de recuperación de contraseña self-service (forgot/reset). Commit `6cd66bb`.

## [v0.21.0]

### Corregido
- 19 bugs — SMS, webhook, phone update, SQLi, XSS, i18n. Commit `5d17947`.

## [v0.20.7]

### Corregido
- Recargar página al cambiar idioma en `profile.js`. Commit `9a2a610`.

## [v0.20.6]

### Cambiado
- Docs: deploy checklist + README/AGENTS actualizados. Commit `42b9f1d`.

## [v0.20.5]

### Añadido
- i18n Fase 4 — JS dinámico traducido (~280 keys, 10 archivos JS). Commit `70f0f44`.

## [v0.20.4]

### Añadido
- i18n Fase 3 — Backend traducido (812 keys, 14 archivos Python). Commit `46e0837`.

## [v0.20.3]

### Añadido
- i18n Fase 2 — Templates traducidos (300+ keys, 16 templates). Commit `5d49f58`.

## [v0.20.2]

### Añadido
- Motor i18n core con diccionario de traducciones ES/EN. Commit `60b529b`.

## [v0.20.1]

### Corregido
- Tildes/ñ + fix de scope en `profesional.js`. Commit `97b4454`.

## [v0.20.0]

### Añadido
- Budget matching en notificaciones, notificador WhatsApp, channel routing. Commit `2ea6210`.

## [v0.19.0]

### Corregido
- Autocomplete `one-time-code` en inputs OTP + error handlers. Commit `68806b6`.

## [v0.18.4]

### Añadido
- Tests: cobertura de perfil de usuario con leads, avatar y preferencias. Commit `a3978c1`.

## [v0.18.3]

### Corregido
- Control de acceso por roles en rutas críticas. Commit `7a24e44`.

## [v0.18.2]

### Añadido
- Sitemap dinámico con lastmod y prioridad a la ruta profesional. Commit `776d30a`.

## [v0.18.1]

### Cambiado
- Frontend: accesibilidad, diseño responsive, botones y limpieza CSS. Commit `c041635`.

## [v0.18.0]

### Añadido
- Contadores de vistas y contactos en leads del usuario. Commit `b2ba845`.

## [v0.17.0]

### Añadido
- KPI bar, period toolbar, acciones en 2 filas, lead preview drawer. Commit `b092328`.

## [v0.16.6]

### Añadido
- Telemetría de click en teléfonos (admin) + fixes de dark mode. Commit `029df0a`.

## [v0.16.5]

### Añadido
- Export de stats (profesional), refactor de tabs y mejoras de leads. Commit `470180a`.

## [v0.16.4]

### Añadido
- Webhook de verificación WhatsApp con soporte de button template. Commit `a0fd1c1`.

## [v0.16.3]

### Corregido
- Modales fuera de bloque Jinja, XSS en 6 archivos JS. Commit `9e6dbb1`.

## [v0.16.2]

### Corregido
- a11y: labels, aria-labels y atributos `for` en todos los templates. Commit `7e8289d`.

## [v0.16.1]

### Añadido
- Sistema de notificaciones, filtrado de leads por profesional, provincia/zona. Commit `df60a20`.

## [v0.16.0]

### Añadido
- Integración Twilio SMS/WhatsApp para verificación telefónica. Commit `fc23f5f`.

## [v0.15.2]

### Añadido
- Códigos de área por ciudad (4 dígitos) + botón de corrección. Commit `8bbe451`.

## [v0.15.1]

### Corregido
- Dashboard, status buttons, search icon y Chart.js local. Commit `1f6ef3e`.

## [v0.15.0]

### Añadido
- Opciones de formulario admin-manageable y correcciones. Commit `00e86e7`.

## [v0.14.19]

### Corregido
- Seguridad, rendimiento, accesibilidad y SEO. Commit `72f453a`.

## [v0.14.18]

### Añadido
- Animaciones de interfaz y mejoras de UX. Commit `8a8d135`.

## [v0.14.17]

### Cambiado
- Documentación externa completa. Commit `47deff7`.

## [v0.14.16]

### Corregido
- Bugs y aumento de rate limits para testing. Commit `9f86536`.

## [v0.14.15]

### Corregido
- Accesibilidad, dark mode y bugs de diseño. Commit `2399f89`.

## [v0.14.14]

### Corregido
- Seguridad, UX y documentación. Commit `fd0438d`.

## [v0.14.13]

### Corregido
- UX header, seguridad, verificación telefónica y edición de leads. Commit `103fb59`.

## [v0.14.12]

### Cambiado
- Refactor frontend: modales, dark mode, responsive, JS externo, accesibilidad. Commit `1a3c223`.

## [v0.14.11]

### Cambiado
- Refactor: modularización de `app.py` en blueprints (Application Factory). Commit `767d355`.

## [v0.14.10]

### Corregido
- Teléfonos: PII leaks, coherencia de validación, hardening y limpieza. Commit `505bb91`.

## [v0.14.9]

### Añadido
- Login/Register: "recordarme" con cookie firmada y validación pre-envío. Commit `f64b5f5`.

## [v0.14.8]

### Añadido
- Verificación de teléfonos, contacto WhatsApp/SMS y telemetría. Commit `61e93d6`.

## [v0.14.7]

### Añadido
- SEO, accesibilidad y tests: validación SMS, meta tags, WCAG y pytest. Commit `0ae4834`.

## [v0.14.6]

### Corregido
- Formato del presupuesto en `user.html`. Commit `0c1ec78`.

## [v0.14.5]

### Cambiado
- Mejoras generales de UI/UX. Commit `d697995`.

## [v0.14.4]

### Corregido
- Teléfono no editable desde solicitud (primera vez). Commit `f32f388`.

## [v0.14.3]

### Corregido
- Pequeños bug fixes en `professional.html`. Commit `0318732`.

## [v0.14.2]

### Añadido
- Contacto WhatsApp/SMS, seguridad y limpieza de código. Commit `7196f54`.

## [v0.14.1]

### Cambiado
- Mejora de `agents.md`, `design.md` y `README.md`. Commit `b2c670a`.

## [v0.14.0]

### Añadido
- Función de WhatsApp en `professionals.html`. Commit `b7f8a7d`.

## [v0.13.3]

### Corregido
- Mejora general del modo oscuro y arreglos mínimos de configuración. Commit `27a4c39`.

## [v0.13.2]

### Añadido
- Carga de imagen y modo oscuro en `profile.html`. Commit `ed2e06d`.

## [v0.13.1]

### Cambiado
- UI/UX y validaciones en `profile.html`. Commit `f1f1960`.

## [v0.13.0]

### Añadido
- Función de configuración de usuario. Commit `5a87fd2`.

## [v0.12.4]

### Cambiado
- README: tecnologías actualizadas. Commit `f51b437`.

## [v0.12.3]

### Corregido
- Problemas visuales en `user.html`. Commit `1f0e7c1`.

## [v0.12.2]

### Añadido
- Restauración de reportes de leads. Commit `81e297e`.

## [v0.12.1]

### Añadido
- Función de reporte de leads (profesionales y admin). Commit `44cb147`.

## [v0.12.0]

### Añadido
- Toggle visto/contactado en `professional.html`. Commit `6638719`.

## [v0.11.6]

### Añadido
- UI/UX improvements: landing page interactiva y FAQ. Commit `e291b60`.

## [v0.11.5]

### Añadido
- Mejora UI/UX, coherencia visual y accesibilidad. Commit `d74261e`.

## [v0.11.3]

### Cambiado
- Merge PR #2 desde `arreglo-version-antigua`. Commit `1a756d1`.

## [v0.11.2]

### Añadido
- Seguridad: validaciones, XSS, rate limit y PDF. Commit `78d0c51`.

## [v0.11.1]

### Corregido
- Correcciones menores a los templates. Commit `0a0e5d9`.

## [v0.11.0]

### Cambiado
- Refactor: extracción de módulos, rate limiting, validaciones, headers de seguridad. Commit `66e0d4c`.

## [v0.10.3]

### Corregido
- Coherencia de tablas en `user.html` y `professional.html`. Commit `0729d2f`.

## [v0.10.2]

### Añadido
- `requirements.txt` y README mejorado. Commit `4fc1ab0`.

## [v0.0.12]

### Corregido
- Filtros y baja de profesionales en admin. Commit `ab03d47`.

## [v0.0.11]

### Corregido
- Filtros arreglados en `professional.html` y `admin.html`. Commit `ca1522c`.

## [v0.0.10]

### Añadido
- Descarga de matrícula y reseteo de contraseñas. Commit `2931f7f`.

## [v0.0.9]

### Añadido
- Filtros en Admin y Profesionales. Commit `32ddc2e`.

## [v0.0.8]

### Añadido
- MVP completo con cambios. Commit `fd32e59`.

## [v0.0.7]

### Cambiado
- Merge branch `main` de GitHub (ArchEstate-MASK-). Commit `585f617`.

## [v0.0.6]

### Añadido
- Commit inicial: Proyecto ArchEstate con validación de usuarios y leads. Commit `a81599c`.

## [v0.0.5]

### Añadido
- Add files via upload. Commit `8a78432`.

## [v0.0.4]

### Cambiado
- Update README.md. Commit `5d7f418`.

## [v0.0.3]

### Cambiado
- README con instrucciones de setup de virtualenv. Commit `df2b05c`.

## [v0.0.2]

### Cambiado
- README con detalles del proyecto e instalación. Commit `ced5d99`.

## [v0.0.1]

### Añadido
- Initial commit. Commit `9415ad9`.

---

> **Nota sobre huecos de numeración:** `v0.11.4` y `v0.25.0`–`v0.25.4` no tienen commit asociado en `main` (huecos históricos). `v0.11.3`/`v0.11.4` apuntaban originalmente a la rama `arreglo-version-antigua`; `v0.11.4` fue eliminado y `v0.11.3` re-apuntado al merge de `main`.
