# Changelog de fixes — sesión de revisión con Claude

Este documento acompaña a `archestate-session2-fixes.patch`. Está pensado para que
OpenCode (u otra persona) pueda **verificar cada punto contra el código actual antes
de aplicarlo**, en vez de aplicar el patch a ciegas — el patch está armado sobre
`b51b3a4`, que puede no ser tu HEAD actual.

Para cada item: **síntoma reportado → causa raíz → qué cambia**. Si al revisar tu
código actual el problema ya no existe o está resuelto distinto, saltealo.

---

## 1. Feature: cobertura de zonas/especialidades por profesional

**Pedido:** el profesional puede ver todos los leads, pero diferenciados por match;
la cobertura (qué zonas/especialidades cubre) tiene que ser configurable desde su
perfil; un lead puede quedar sin asignar si nadie matchea sus características.

**Qué cambia:**
- Tabla nueva `professional_coverage` (`user_id`, `coverage_type` ['zone'|'specialty'],
  `value`) — reemplaza los campos únicos `zone`/`specialty` de `professionals` como
  fuente de verdad para matching, con fallback automático a esos campos legacy si el
  profesional no configuró nada nuevo (`models.get_professional_coverage`).
- `services/matching.py` (nuevo): scoring compartido entre asignación automática y
  listado de leads — una sola función de "qué es un match", en vez de dos lógicas
  separadas que podían desincronizarse.
- `services/assignment.py`: `auto_assign_lead` ya no fuerza una asignación arbitraria
  — si nadie tiene relación real con las características del lead (score < 1), el
  lead queda `assigned_to = NULL` a propósito.
- `routes/professional_bp.py`: cada lead en `/api/leads` trae `matches_coverage:
  true/false`. El filtro duro `my_leads=1` sigue siendo solo geográfico (provincia/
  país/zona) — la especialidad **no** excluye leads de la lista, solo afecta el
  badge. Esto es deliberado: un test ya existente (`test_my_leads_shows_all_when_no_
  zone_set`) confirmaba que ese es el comportamiento esperado del producto.
- `routes_profile.py`: `GET/PUT /api/profile/professional/coverage` — el profesional
  configura sus zonas/especialidades desde acá. **Falta la pantalla en `profile.html`**
  que llame a este endpoint — el backend está listo y testeado pero no hay UI todavía.

**Archivos:** `app_setup.py`, `models.py`, `services/assignment.py`,
`services/matching.py` (nuevo), `routes/professional_bp.py`, `routes_profile.py`,
`i18n/translations.py` (clave `profile.coverage_too_many`), tests.

---

## 2. Estadísticas vacías no mostraban mensaje claro

**Síntoma:** si un mes no tiene leads, no se ve un mensaje de "no hay datos".

**Causa raíz:** `loadMarketStats()` en `static/js/professional.js` saltaba en
silencio a otro mes con datos cuando el elegido daba `total: 0` — incluso cuando el
salto lo disparaba el propio usuario eligiendo el mes a mano en el dropdown
(`onchange="loadMarketStats()"` sin distinguir selección manual de carga inicial).

**Fix:** el cambio manual de mes (`onchange="loadMarketStats(false)"`) ya no permite
que el código pise la elección del usuario. Se agregó un bloque de empty state
(`#statsEmptyState`) en `templates/professional.html`, con la clave
`pro.stats_no_sales`.

**Archivos:** `static/js/professional.js`, `templates/professional.html`,
`i18n/translations.py`.

---

## 3. Recuperar contraseña → siempre 400

**Causa raíz:** `templates/forgot_password.html` y `templates/reset_password.html`
no tenían `<input type="hidden" name="csrf_token">`. Con Flask-WTF, cualquier POST
sin ese token se rechaza con 400 automáticamente.

**Fix:** agregado el input en ambos forms (mismo patrón que `login.html`/
`register.html`).

**Verificá primero:** si ya notaste este bug vos y lo arreglaste, este punto está de más.

**Archivos:** `templates/forgot_password.html`, `templates/reset_password.html`.

---

## 4. "Recordarme 30 días" no persistía

**Causa raíz doble:**
- `config.PERMANENT_SESSION_LIFETIME` estaba en `3600` (1 hora) — copiado de
  `SESSION_TIMEOUT` por error, no de `REMEMBER_TOKEN_DAYS` (30 días).
- `session.permanent = True` se seteaba en **todo** login en `routes/auth_bp.py`,
  no solo cuando se tildaba "recordarme".

**Fix:** `PERMANENT_SESSION_LIFETIME = REMEMBER_TOKEN_DAYS * 24 * 3600`.
`session.permanent = True` se movió adentro del bloque `if request.form.get
('remember') == 'on':`.

**Archivos:** `config.py`, `routes/auth_bp.py`.

---

## 5. Notificación admin → profesional (3 síntomas, causas distintas)

**5a. Botón mostraba el texto crudo `admin.send_notification_to`**
Causa: esa clave existe en `i18n/translations.py` (Python, server-side) pero nunca
se agregó a `static/js/i18n.js` (diccionario separado para `t()` del lado cliente).
Son dos fuentes de traducciones independientes que se desincronizan. También faltaba
`admin.notification_title_required`.
Fix: agregadas ambas claves a `static/js/i18n.js` (ES+EN).

**5b. La notificación no le llegaba al profesional / le llegaba al admin**
Causa real (la más importante de las tres): en `static/js/admin.js`, el botón
llamaba `openNotifyModal('${pro.id}', ...)` usando el ID de la tabla
`professionals`, no `pro.user_id` (el ID real en `users` que necesita
`send_internal_notification`). Como el ID de `professionals` suele ser bajo, podía
coincidir con el `user_id` del admin.
Fix: `openNotifyModal('${pro.user_id}', ...)`.

**5c. No se marcaba como "enviada" / no había diferenciación enviado-recibido**
Causa: `admin_send_notification()` en `routes/admin_bp.py` llamaba a
`send_internal_notification(target_user_id, title, body)` **sin pasar `actor_id`**
→ quedaba `NULL` en la tabla `notifications` → el log de "notificaciones enviadas"
del admin (que filtra por `actor_id`) nunca las encontraba.
Fix: se pasa `actor_id=session['user_id']`.
**Pendiente (no lo resolví):** la clave `notif.you_sent` ("Enviado por vos") existe
en `i18n.js` pero ningún JS la usa todavía — la lógica visual para diferenciar
enviado/recibido en la lista de notificaciones no está construida.

**Archivos:** `static/js/i18n.js`, `static/js/admin.js`, `routes/admin_bp.py`.

---

## 6. Export de leads (CSV/Excel) del profesional — headers rotos

No estaba en tu lista original, pero lo encontré revisando el patrón de "clave i18n
faltante → texto crudo en pantalla" (buscando la causa del bug #13 que reportaste).

**Bug 1:** `writer.writerow(t('prof.export_csv_headers', lang))` pasaba un **string**
en vez de una lista a `csv.writer` — lo escribía carácter por carácter (una columna
por letra). Mismo problema en el export a Excel (`prof.export_leads_headers`, que
además faltaba por completo en `translations.py`).
Fix: `.split(',')` en ambos call sites.

**Bug 2:** el header de CSV/Excel tenía 5 columnas de texto para 6 columnas de datos
reales (faltaba "ID") — quedaban corridas una posición.
Fix: agregado "ID" como primer header.

Además agregué ~12 claves faltantes más en `prof.export_*` y `profile.pdf_*` que
encontré con el mismo barrido (secciones del Excel, prefijos del PDF).

**Archivos:** `routes/professional_bp.py`, `i18n/translations.py`.

---

## Todavía sin investigar (de tu lista original)

No llegué a estos por límite de tiempo en la sesión — no están en el patch:

- Autocompletado de teléfono que formatea pero no permite guardar (config y
  solicitudes).
- Colores de botón "crear cuenta" / íconos de register-login en modo oscuro,
  mismo color que el modal.
- Carga de imagen en configuración: solo la primera vez funciona, eliminar y
  recargar otra no actualiza sin refrescar la página.
- "Crear solicitudes" en configuración de profesionales no permite gestionar
  ninguna solicitud (no encontré esta feature en el código que tengo — puede ser
  algo que agregaste en tu local más nuevo).
- Los 4 "modales" con datos de leads en la vista de profesional no reflejan datos
  reales.
