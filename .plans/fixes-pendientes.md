# ArchEstate — Fixes Pendientes (Sección "Todavía sin investigar")

> Referencia: `fixes-changelog.md`. Estado previo: Bloque 1 (coverage) y Bloque 2 (puntos 2-6) aplicados — 542 pytest + 12 node tests verdes.

## Objetivo
Arreglar los 5 items que el changelog dejó "sin investigar", con diagnóstico verificado contra el código actual y referencias archivo:línea.

---

## Ítem 1 — Teléfono que formatea pero no permite guardar

**Veredicto: bug real, confirmado con phonenumbers.**

### 1a. `static/js/profile.js` — duplicación de código de área (guardar desde `/mi-perfil`)
- **Bloque:** líneas ~228-243 (función de formato que llama `formatProfilePhone`/`getSelectedArgentineAreaCode`).
- **Causa:** se corta el prefijo de área del `local` ANTES de manejar el `9`/`15` móvil. Con input `9 11 2345 6789` → `local='91123456789'` no arranca con `'11'`/`'011'` → no se corta el área → se corta el `9` → queda `local='1123456789'` → output `+54 9 11 1123456789` (**inválido** → HTTP 400 al guardar).
- **Fix:** reordenar la normalización: (1) quitar código de país, (2) quitar trunk `0`, (3) detectar y extraer el prefijo móvil `9`/`15` del `local`, (4) recién ahí quitar el prefijo de área, (5) recomponer `+54 9 <área> <subscriber>`.
- **Verificación:** script python con phonenumbers sobre la tabla de inputs (abajo).

### 1b. `static/js/main.js` — rama `+54` del submit de solicitud (líneas ~406-411)
- **Causa:** concatena `'9' + d` sin antes quitar `+54`/`549` si el input ya viene formateado; falla también con `15...` y `011...`. Produce `+54 95491123456789`, `+54 951123456789`, `+54 901123456789` (**inválidos**).
- **Fix:** normalización robusta idéntica a 1a, con branches para `+54` presente, trunk `0`, y prefijos `9`/`15`.
- **Nota:** el caso `11 2345 6789` (área sin `9`) ya produce `+54 91123456789` (válido) — no romper ese caso.

### 1c. Chile — `static/js/phone-suggest.js` (`suggestCL` línea 197, `formatNational` +56 línea 316)
- **Diagnóstico:** la estructura ya es `+56 9 XXXX XXXX`. El rechazo de `+56 9 1234 5678` es un rango de abonado no asignado en los datos de phonenumbers (limitación del paquete de datos, no del formato).
- **Acción:** documentar como limitación conocida. No reescribir el formato.

### Verificación ítem 1
```bash
.venv/bin/python - <<'EOF'
import phonenumbers
cases = ['+54 9 11 1123456789', '+54 91123456789', '+54 95491123456789',
         '+54 951123456789', '+54 901123456789', '+54 9 3541 388 368']
for c in cases:
    print(c, 'OK' if phonenumbers.is_valid_number(phonenumbers.parse(c, 'AR')) else 'BAD')
EOF
python -m pytest tests/ -q
node --test tests/*.test.js
node --check static/js/profile.js static/js/main.js
```

---

## Ítem 2 — Dark mode: botón "Crear Cuenta" / íconos register-login

**Veredicto: bug real.**

- **Causa raíz:** `static/css/base.css:877` `.dark .bg-midnight { background: var(--bg-card) !important; }` (y línea 878 `hover`) ganan contra `dark:bg-gold` (sin `!important`). `base.css:867` secuestra `dark:text-midnight` a color claro.
- **Afectados:**
  - `templates/register.html:184` — botón `bg-midnight dark:bg-gold text-white dark:text-midnight` → invisible en dark (`#1a2332` sobre card `#1a2332`, contraste 1.0:1).
  - `templates/login.html:86` — hover `dark:hover:bg-gold` pierde contra `.dark .hover\:bg-midnight:hover` (línea 878).
  - `templates/lead_detail.html:13` — mismo patrón `bg-midnight dark:bg-gold` (volver a vista profesional).
- **Fix (clase dedicada, aprobada por el usuario):**
  - `static/css/base.css`: agregar `.btn-cta-gold` que defina bg/texto/hover en claro y oscuro sin pelear con los `!important` (p. ej. claro: bg midnight/texto blanco/hover dorado; oscuro: bg dorado/texto oscuro/hover dorado claro).
  - Reemplazar las clases de utilidad en `register.html:184`, `login.html:86` y `lead_detail.html:13` por `.btn-cta-gold` (conservando `btn-submit btn-shimmer`).

### Verificación ítem 2
```bash
node --check static/js/*.js   # si se toca JS
python -m pytest tests/ -q
# Inspección manual: toggle dark en /register y /login
```

---

## Ítem 3 — Carga de imagen en configuración: solo la primera vez

**Veredicto: bug real (caché del navegador).**

- **Causa:** nombre de archivo constante en `routes_profile.py` (`user_{id}_avatar.{ext}` línea ~390; `pro_{id}_photo.{ext}` línea ~506) + asignación sin cache-busting en `profile.js:156` (avatar) y `:1238` (foto pro). Tras delete + re-upload, el navegador sirve la imagen vieja en caché.
- **Fix (`static/js/profile.js`):**
  - Línea 156: `img.src = data.avatar_url + '?v=' + Date.now()`
  - Línea 1238: `img.src = data.photo_url + '?v=' + Date.now()`
  - Verificar handlers de delete (líneas 184 y 1266) — ya setean placeholder `/static/img/default-avatar.svg`, sin cambio necesario.

### Verificación ítem 3
```bash
node --check static/js/profile.js
python -m pytest tests/ -q
# Manual: upload avatar → delete → upload → se ve la nueva sin recargar
```

---

## Ítem 4 — "Modales" de leads en vista de profesional

**Veredicto: parcial — no hay 4 modales.** Los 2 overlays (Lead Preview Drawer y Report Modal) ya usan datos reales. El bug real son las **4 tarjetas KPI**.

- **Causa:** `professional.js:496` `renderLeadKpis(data.leads)` calcula solo sobre la página (per_page=25 forzado, línea ~482) mientras la tarjeta de total usa `data.total` global (`professional.js:497`). Con >25 leads los KPIs se contradicen. `renderLeadKpis` está en `professional.js:825-857`.
- **Backend:** `routes/professional_bp.py` `/api/leads` (respuesta en líneas 238-245): agregar `unseen_total` y `contacted_total` (COUNT agregado con el MISMO filtro que `total`, join con `lead_tracking` por `professional_id`).
- **Frontend:** `renderLeadKpis` usa `data.total`, `data.unseen_total`, `data.contacted_total`; `contactRate = contacted / (total - unseen)`.

### Verificación ítem 4
```bash
python -m pytest tests/ -q
node --check static/js/professional.js
# Manual: profesional con >25 leads → totales globales coherentes en las 4 tarjetas
```

---

## Ítem 5 — "Crear solicitudes" en configuración

**Veredicto: decisión de producto confirmada por el usuario — solo clientes gestionan solicitudes.**

- **Diagnóstico:** la pestaña "Solicitudes" de `profile.html` tiene CTA "Crear solicitud" (líneas 568-570) → `url_for('client.user_view')` → `/usuario`, pero `client_bp.py:30-32` redirige a todo rol `professional` al home. La tabla de historial ya funciona (`/api/profile/leads` + `models.get_user_leads`, `models.py:173`).
- **Fix (`templates/profile.html:568-570`):** mostrar el CTA solo para no-profesionales:
  ```jinja
  {% if not user or user.role != 'professional' %}
      <a href="{{ url_for('client.user_view') }}" ...>{{ t('profile.create_lead') }}</a>
  {% endif %}
  ```
- **No tocar** `client_bp.py:30-32` — el bloqueo es intencional. Los profesionales ven su historial (view-only) y se comunican con clientes por WhatsApp/SMS y con admin vía notificaciones.

### Verificación ítem 5
```bash
python -m pytest tests/ -q
# Manual: /mi-perfil como profesional → sin CTA "Crear solicitud"; historial visible
```

---

## Orden de ejecución y comandos finales

1. Ítem 2 (dark) → 2. Ítem 3 (avatar) → 3. Ítem 4 (KPIs) → 4. Ítem 5 (CTA) → 5. Ítem 1 (teléfono, el más delicado).
2. Tras cada ítem correr la suite; al final corrida completa:
```bash
python -m pytest tests/ -q
node --test tests/*.test.js
node --check static/js/profile.js static/js/main.js static/js/professional.js
python verify_coherence.py
git diff --stat
```

## Riesgos / notas
- Los `!important` de `base.css:864-882` son una bomba global — la clase `.btn-cta-gold` evita pelearlos.
- No reescribir la rama "correcta" de `main.js` (`11 2345 6789` → `+54 91123456789`).
- Chile queda como limitación documentada (datos de phonenumbers), no como bug de formato.
- No hay cambios de backend para 1, 2, 3 y 5; solo el ítem 4 toca `professional_bp.py`.
