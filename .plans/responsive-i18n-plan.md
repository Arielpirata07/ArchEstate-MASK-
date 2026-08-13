# Plan: Responsividad + Cross-Browser + i18n — ArchEstate

> **Fecha**: 2026-08-11
> **Estado**: Plan aprobado, listo para implementar
> **Archivos afectados**: 19 (6 HTML responsive, 1 CSS cross-browser, 12 HTML+1 Python i18n)

---

## Resumen Ejecutivo

| Categoría | Archivos | Cambios | Esfuerzo |
|-----------|----------|---------|----------|
| **Responsive** | 6 HTML | 13 | Bajo |
| **Cross-browser** | 1 CSS | 1 | Bajo |
| **i18n — Templates existentes** | 5 HTML | ~150 strings | Alto |
| **i18n — Keys nuevas** | 1 Python | ~100 keys | Medio |
| **i18n — Email templates** | 6 HTML | ~100 strings | Alto |
| **TOTAL** | **19 archivos** | **~365 cambios** | **Alto** |

---

## PARTE A: RESPONSIVIDAD (13 cambios en 6 archivos)

**Versión de Tailwind**: v3.4.17 (standalone CLI)
**Breakpoints**: `sm: 640px`, `md: 768px`, `lg: 1024px`
**Compatibilidad**: Universal (todos los navegadores modernos 2018+)

| # | Archivo | Línea | Clase Actual | Cambio Propuesto | Compatibilidad |
|---|---------|-------|-------------|-----------------|---------------|
| 1 | `base.html` | 165 | `text-[10px] text-white/40...` | Agregar `hidden sm:inline` | ✅ Universal |
| 2 | `admin.html` | 13 | `flex justify-between items-end` | `flex flex-col md:flex-row justify-between items-start md:items-end gap-4` | ✅ Universal |
| 3 | `admin.html` | 19 | `flex gap-2` | `overflow-x-auto flex gap-2 pb-2` | ✅ Universal |
| 4 | `professional.html` | 142 | `grid grid-cols-4 gap-3` | `grid grid-cols-2 md:grid-cols-4 gap-3` | ✅ Universal |
| 5 | `profile.html` | 74 | `flex items-start gap-8` | `flex flex-col sm:flex-row items-start gap-4 sm:gap-8` | ✅ Universal |
| 6 | `profile.html` | 69 | `lg:col-span-4 p-8 lg:p-10` | `lg:col-span-4 p-4 sm:p-8 lg:p-10` | ✅ Universal |
| 7 | `profile.html` | 11 | `flex items-center justify-between` | `flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4` | ✅ Universal |
| 8 | `user.html` | 25 | `p-12 lg:p-16` | `p-6 sm:p-12 lg:p-16` | ✅ Universal |
| 9 | `user.html` | 42 | `p-12 lg:p-16` | `p-6 sm:p-12 lg:p-16` | ✅ Universal |
| 10 | `user.html` | 118 | `h-[300px]` | `h-[200px] sm:h-[300px]` | ✅ Universal |
| 11 | `user.html` | 355 | `grid grid-cols-2 gap-4` | `grid grid-cols-1 sm:grid-cols-2 gap-4` | ✅ Universal |
| 12 | `user_management.html` | 13 | `flex justify-between items-end` | `flex flex-col md:flex-row justify-between items-start md:items-end gap-4` | ✅ Universal |
| 13 | `user_management.html` | 26 | `flex items-end gap-3` | `flex flex-wrap items-end gap-3` | ✅ Universal |

### Detalle de Cambios

#### 1. `base.html:165` — Ocultar username en mobile
```html
<!-- ANTES -->
<span class="text-[10px] text-white/40 uppercase font-bold tracking-tighter">{{ active_role }}: {{ session.get('username') }}</span>

<!-- DESPUÉS -->
<span class="hidden sm:inline text-[10px] text-white/40 uppercase font-bold tracking-tighter">{{ active_role }}: {{ session.get('username') }}</span>
```
**Razón**: En mobile el username + rol desborda la navbar junto con los otros elementos.

#### 2-3. `admin.html:13,19` — Header responsive con tabs scroll
```html
<!-- ANTES -->
<div class="flex justify-between items-end border-b border-midnight/10 pb-6 header-entrance">
    ...
    <div class="flex gap-2">

<!-- DESPUÉS -->
<div class="flex flex-col md:flex-row justify-between items-start md:items-end border-b border-midnight/10 pb-6 header-entrance gap-4">
    ...
    <div class="overflow-x-auto flex gap-2 pb-2">
```
**Razón**: 7 tabs en fila desbordan en mobile. `overflow-x-auto` permite scroll horizontal. El CSS en `admin.css:182-196` ya maneja `white-space: nowrap` y `flex-shrink: 0`.

#### 4. `professional.html:142` — KPI grid responsive
```html
<!-- ANTES -->
<div class="grid grid-cols-4 gap-3">

<!-- DESPUÉS -->
<div class="grid grid-cols-2 md:grid-cols-4 gap-3">
```
**Razón**: 4 columnas KPI en mobile son demasiado compactas. Con `grid-cols-2` se ven 2x2, legibles.

#### 5-7. `profile.html:74,69,11` — Avatar y header responsive
```html
<!-- ANTES (línea 74) -->
<div class="flex items-start gap-8 mb-8">
<!-- DESPUÉS -->
<div class="flex flex-col sm:flex-row items-start gap-4 sm:gap-8 mb-8">

<!-- ANTES (línea 69) -->
<div class="lg:col-span-4 p-8 lg:p-10 settings-content">
<!-- DESPUÉS -->
<div class="lg:col-span-4 p-4 sm:p-8 lg:p-10 settings-content">

<!-- ANTES (línea 11) -->
<div class="flex items-center justify-between mb-8 header-entrance">
<!-- DESPUÉS -->
<div class="flex flex-col sm:flex-row items-start sm:items-center justify-between mb-8 header-entrance gap-4">
```
**Razón**: Avatar (120px) + formulario se comprimen en mobile. Padding excesivo en mobile.

#### 8-10. `user.html:25,42,118` — Formulario responsive
```html
<!-- ANTES (línea 25) -->
<div class="aside-ambient ... p-12 lg:p-16 ...">
<!-- DESPUÉS -->
<div class="aside-ambient ... p-6 sm:p-12 lg:p-16 ...">

<!-- ANTES (línea 42) -->
<div class="bg-white p-12 lg:p-16 ...">
<!-- DESPUÉS -->
<div class="bg-white p-6 sm:p-12 lg:p-16 ...">

<!-- ANTES (línea 118) -->
<div class="relative w-full max-w-5xl h-[300px] ...">
<!-- DESPUÉS -->
<div class="relative w-full max-w-5xl h-[200px] sm:h-[300px] ...">
```

#### 11. `user.html:355` — Gated community grid
```html
<!-- ANTES -->
<div class="grid grid-cols-2 gap-4">
<!-- DESPUÉS -->
<div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
```

#### 12-13. `user_management.html:13,26` — Header y filtros
```html
<!-- ANTES (línea 13) -->
<div class="flex justify-between items-end ...">
<!-- DESPUÉS -->
<div class="flex flex-col md:flex-row justify-between items-start md:items-end ... gap-4">

<!-- ANTES (línea 26) -->
<div class="flex items-end gap-3">
<!-- DESPUÉS -->
<div class="flex flex-wrap items-end gap-3">
```

### Cosas que YA están correctas (no requieren cambio)

| Archivo | Línea | Estado |
|---------|-------|--------|
| `professional.html` | 21 | ✅ `flex flex-col md:flex-row` |
| `professional.html` | 27 | ✅ `flex flex-wrap items-center gap-3` |
| `professional.html` | 188 | ✅ Filtros `grid-cols-1 md:grid-cols-3` |
| `professional.html` | 469 | ✅ Stats `grid-cols-2 md:grid-cols-4` |
| `professional.html` | 516 | ✅ Charts `grid-cols-1 md:grid-cols-2` |
| `landing.html` | 136 | ✅ Cards `grid-cols-1 md:grid-cols-3` |
| `landing.html` | 165 | ✅ Stats `grid-cols-2 md:grid-cols-4` |
| `landing.html` | 203 | ✅ Steps `grid-cols-1 md:grid-cols-3` |
| `admin.html` | 77 | ✅ KPI `grid-cols-2 md:grid-cols-5` |
| `admin.html` | 136 | ✅ Charts `grid-cols-1 md:grid-cols-2` |
| `admin.html` | 316 | ✅ Audit filters `grid-cols-1 md:grid-cols-4` |
| `admin.html` | 400 | ✅ Professionals `grid-cols-1 lg:grid-cols-3` |
| `admin.html` | 652 | ✅ Form options `overflow-x-auto` |
| `admin.html` | 698 | ✅ Phone area codes `overflow-x-auto` |
| `lead_detail.html` | 7 | ✅ `flex-col md:flex-row` |
| `lead_detail.html` | 18 | ✅ `grid-cols-1 lg:grid-cols-2` |
| `profile.html` | 22 | ✅ `grid-cols-1 lg:grid-cols-5` |
| `profile.html` | 97 | ✅ `grid-cols-1 md:grid-cols-2` |
| `login.html` | 6 | ✅ `max-w-md mx-auto px-4` |
| `base.html` | 116-183 | ✅ Navbar con `md:hidden` menu button |

---

## PARTE B: CROSS-BROWSER (1 cambio en 1 archivo)

| # | Archivo | Línea | Cambio | Compatibilidad |
|---|---------|-------|--------|---------------|
| 14 | `admin.css` | 6-21 | Agregar `scrollbar-width: thin; scrollbar-color` para Firefox | Chrome 121+, Firefox 64+, Safari 16+ |

### Detalle

`admin.css` tiene custom scrollbar styling (líneas 6-21) que solo funciona en WebKit/Chrome:

```css
/* ANTES - solo WebKit */
.overflow-y-auto::-webkit-scrollbar { width: 4px; }
.overflow-y-auto::-webkit-scrollbar-track { background: transparent; }
.overflow-y-auto::-webkit-scrollbar-thumb { ... }

/* DESPUÉS - agregar Firefox */
.overflow-y-auto {
    scrollbar-width: thin;
    scrollbar-color: rgba(115, 90, 58, 0.2) transparent;
}
.overflow-y-auto::-webkit-scrollbar { width: 4px; }
/* ... resto igual */
```

---

## PARTE C: TRADUCCIONES i18n

### Estado Actual

| Diccionario | Keys ES | Keys EN | Estado |
|-------------|---------|---------|--------|
| `i18n/translations.py` | 961 | 961 | ✅ Completo |
| `static/js/i18n.js` | 412 | 412 | ✅ Completo |
| Templates HTML | — | — | ❌ ~150+ strings hardcoded |

**El problema NO es que falten keys en los diccionarios.** El problema es que los templates no las usan.

---

### C1. Templates CRÍTICos (0% i18n)

#### `templates/lead_detail.html` — ~40 strings hardcoded

Toda la página está en español sin usar `{{ t() }}`. Keys existentes en `translations.py` que coinciden:

| Línea | Texto hardcoded | Key existente |
|-------|----------------|---------------|
| 10 | `Detalles de la Solicitud` | `prof.pdf_title` |
| 22 | `Tipo de Operación` | `prof.pdf_operation_type` |
| 27 | `Zona Geográfica` | `prof.pdf_geographic_zone` |
| 33 | `Provincia` | `prof.pdf_province_label` |
| 39 | `Presupuesto` | `prof.pdf_budget` |
| 58 | `Estilo Arquitectónico` | `prof.pdf_architectural_style` |
| 63 | `Contacto Directo` | `prof.pdf_direct_contact` |
| 73 | `Formato Válido` | Nueva key |
| 83 | `Registrado` | `prof.pdf_registered` |
| 93 | `Especificaciones Técnicas` | `prof.pdf_tech_specs` |
| 97 | `Ambientes` | `prof.pdf_rooms` |
| 101 | `Habitaciones` | `prof.pdf_bedrooms` |
| 105 | `Baños` | `prof.pdf_bathrooms` |
| 112 | `Superficie Total` | `prof.pdf_total_area` |
| 116 | `Estacionamiento` | `prof.pdf_parking` |
| 117 | `Sin preferencia` | Nueva key |
| 123 | `Orientación` | `prof.pdf_orientation` |
| 124 | `Indiferente` | Nueva key |
| 127 | `Estado` | `prof.pdf_condition` |
| 133 | `Antigüedad` | `prof.pdf_age` |
| 138 | `Extras y Comodidades` | `prof.pdf_amenities` |
| 149 | `No especificadas` | `prof.not_specified_fem_pl` |
| 156 | `Detalles del Departamento` | `user.dept_details` |
| 159 | `Piso / Bloque` | `prof.pdf_floor_block` |
| 163 | `Metros Útiles` | `prof.pdf_usable_m2` |
| 167 | `Ascensor` | `prof.pdf_elevator` |
| 171 | `Piscina Comunitaria` | Nueva key |
| 178 | `Detalles de la Propiedad` | `prof.pdf_property_details` |
| 181 | `Superficie de Terreno` | `prof.pdf_land_area` |
| 185 | `Superficie Construida` | `prof.pdf_built_area` |
| 189 | `Piscina` | `prof.pdf_pool` |
| 196 | `Detalles del Dúplex` | `user.duplex_details` |
| 214 | `Detalles del Penthouse` | `user.penthouse_details` |
| 217 | `Piso` | `user.penthouse_floor` |
| 225 | `Ascensor Privado` | `user.private_elevator` |
| 232 | `Detalles del Local Comercial` | `user.local_details` |
| 239 | `Frente` | `user.frontage` |
| 243 | `Piso / Planta` | `user.local_floor` |
| 247 | `Altura del Local` | `user.local_height` |
| Todos | `No especificado` | `prof.not_specified` |

#### `templates/edit_lead.html` — ~50 strings hardcoded

| Línea | Texto hardcoded | Key sugerida |
|-------|----------------|-------------|
| 3 | `Editar Solicitud` | `edit_lead.title` |
| 27 | `Editar Solicitud` | `edit_lead.title` |
| 29 | `Modifica los parámetros de tu solicitud...` | `edit_lead.subtitle` |
| 33 | `Solicitud #` | `edit_lead.request_number` |
| 41 | `Volver a Configuración` | `edit_lead.back_to_settings` |
| 49 | `Parámetros Editables` | `edit_lead.editable_params` |
| 50 | `Edita solo las secciones que necesites...` | `edit_lead.editable_desc` |
| 57 | `Campos Inmutables` | `edit_lead.immutable_fields` |
| 84 | `Parámetros Principales` | `user.main_params` |
| 104 | `Presupuesto` | `user.budget` |
| 120 | `Estilo Arquitectónico` | `user.arch_style` |
| 125 | `Teléfono` | `user.phone` |
| 130 | `Editar en Configuración` | `user.edit_in_settings` |
| 141 | `Espacios` | `edit_lead.spaces` |
| 147-165 | `Ambientes`, `Habitaciones`, `Baños` | `user.rooms`, `user.bedrooms`, `user.bathrooms` |
| 181-207 | `Superficies`, labels de m² | Keys existentes |
| 223 | `Características` | `edit_lead.features` |
| 229-282 | `Ascensor`, `Piscina`, etc. | Keys existentes en `user.*` |
| 298 | `Extras y Comodidades` | `edit_lead.extras` |
| 361 | `Guardar Cambios` | `edit_lead.save` |
| 365 | `Cancelar` | `edit_lead.cancel` |
| 378 | `Historial de Versiones` | `edit_lead.version_history` |

---

### C2. Templates con strings hardcoded PARCIAL

#### `templates/professional.html` — ~20 strings

| Línea | Texto | Key sugerida |
|-------|-------|-------------|
| 190 | `Búsqueda rápida` | `pro.quick_search` |
| 198 | `Tipo de Operación` | `pro.operation_type` |
| 201-203 | `Comprar Propiedad`, `Remodelación Integral`, `Construir desde Cero` | `pro.buy_property`, `pro.remodelation`, `pro.build_from_scratch` |
| 286 | `Buscar` | `pro.search` |
| 301 | `OK = Tel. válido` | `pro.phone_valid` |
| 309 | `Cambiar orden` | `pro.toggle_order` |
| 318-325 | Headers de tabla | Keys existentes parciales |
| 528 | `Zonas` (chart) | `pro.zones` |
| 546 | `Tipo de Operación` (chart) | `pro.operation_type` |
| 567 | `Vista rápida` | `pro.quick_view` |
| 257-273 | Chips de presupuesto | `pro.budget_up_to`, `pro.budget_over` |

#### `templates/admin.html` — ~30 strings

| Línea | Texto | Key sugerida |
|-------|-------|-------------|
| 297 | `Sin datos de telemetría...` | `admin.no_telemetry_data` |
| 318 | `Profesional` | `admin.professional` |
| 324 | `Evento` | `admin.event` |
| 327 | `Revelado` | `admin.revealed` |
| 332 | `Desde` | `admin.from` |
| 336 | `Hasta` | `admin.to` |
| 354-358 | Headers de tabla | Keys existentes parciales |
| 385 | `Página anterior` | `admin.prev_page` |
| 389 | `Página siguiente` | `admin.next_page` |
| 443 | `profesionales encontrados` | `admin.pros_found` |
| 453 | `Ordenar por:` | `admin.sort_by` |
| 456-458 | `Nombre`, `Matrícula`, `Especialidad` | `admin.name`, `admin.license`, `admin.specialty` |
| 538 | `Fin del registro reciente` | `admin.end_of_recent_log` |
| 644 | `Buscar opción...` | `admin.search_option_placeholder` |
| 666 | `Cargando...` | `admin.loading` |
| 756-792 | Modal text hardcoded | Keys needed |

#### `templates/user.html` — ~12 strings

| Línea | Texto | Key sugerida |
|-------|-------|-------------|
| 134 | `Sin límite máximo` | `user.no_max_limit` |
| 140 | `Restablecer` | `user.reset` |
| 144 | `Aceptar` | `user.accept` |
| 325, 390 | `Los metros construidos superan el 80%...` | `user.area_warning` |
| 343 | `Pileta cubierta` | `user.indoor_pool` |
| 362 | `Club House` | `user.club_house` |
| 366 | `Canchas deportivas` | `user.sports_courts` |
| 370 | `Lagunas artificiales` | `user.artificial_lagoons` |
| 420 | `Piso` | `user.floor` |
| 443 | `Vista 360°` | `user.view_360` |
| 567 | `Buscar ciudad` | `user.search_city` |

---

### C3. Plantillas de EMAIL — 100+ strings hardcoded

Los emails se renderizan con `render_template()` Flask, que SÍ tiene acceso a `{{ t() }}` via `inject_language()` context processor (`middleware.py:136`). **SÍ es posible usar `{{ t() }}` en emails.**

| Archivo | Strings hardcoded |
|---------|-------------------|
| `email/base.html` | Footer: "Este es un correo automático..." |
| `email/lead_assigned.html` | ~30 labels (Operación, Presupuesto, Zona, etc.) |
| `email/password_reset.html` | Titulo, cuerpo, CTA |
| `email/report_deleted.html` | ~10 labels |
| `email/status_change.html` | ~10 labels |
| `email/professional_status.html` | ~5 labels |

---

### C4. Keys que necesitan crearse

```python
# lead_detail.html
'lead_detail.valid_format': {'es': 'Formato Válido', 'en': 'Valid Format'},
'lead_detail.back_to_panel': {'es': 'Volver al panel', 'en': 'Back to panel'},
'lead_detail.no_preference': {'es': 'Sin preferencia', 'en': 'No preference'},
'lead_detail.indifferent': {'es': 'Indiferente', 'en': 'Indifferent'},
'lead_detail.community_pool': {'es': 'Piscina Comunitaria', 'en': 'Community Pool'},

# edit_lead.html
'edit_lead.title': {'es': 'Editar Solicitud', 'en': 'Edit Request'},
'edit_lead.subtitle': {'es': 'Modifica los parámetros de tu solicitud...', 'en': 'Modify your request parameters...'},
'edit_lead.request_number': {'es': 'Solicitud #', 'en': 'Request #'},
'edit_lead.back_to_settings': {'es': 'Volver a Configuración', 'en': 'Back to Settings'},
'edit_lead.editable_params': {'es': 'Parámetros Editables', 'en': 'Editable Parameters'},
'edit_lead.editable_desc': {'es': 'Edita solo las secciones que necesites actualizar.', 'en': 'Only edit the sections you need to update.'},
'edit_lead.immutable_fields': {'es': 'Campos Inmutables', 'en': 'Immutable Fields'},
'edit_lead.immutable_desc': {'es': 'Estos campos no pueden ser alterados.', 'en': 'These fields cannot be modified.'},
'edit_lead.operation_type': {'es': 'Tipo de Operación', 'en': 'Operation Type'},
'edit_lead.property_type': {'es': 'Tipo de Propiedad', 'en': 'Property Type'},
'edit_lead.registration_date': {'es': 'Fecha de Registro', 'en': 'Registration Date'},
'edit_lead.editable_params': {'es': 'Parámetros Editables', 'en': 'Editable Parameters'},
'edit_lead.editable_desc': {'es': 'Edita solo las secciones que necesites actualizar.', 'en': 'Only edit the sections you need to update.'},
'edit_lead.spaces': {'es': 'Espacios', 'en': 'Spaces'},
'edit_lead.superfaces': {'es': 'Superficies', 'en': 'Areas'},
'edit_lead.floor_block': {'es': 'Piso / Bloque', 'en': 'Floor / Block'},
'edit_lead.features': {'es': 'Características', 'en': 'Features'},
'edit_lead.extras': {'es': 'Extras y Comodidades', 'en': 'Extras & Amenities'},
'edit_lead.save': {'es': 'Guardar Cambios', 'en': 'Save Changes'},
'edit_lead.cancel': {'es': 'Cancelar', 'en': 'Cancel'},
'edit_lead.saved_ok': {'es': 'Guardado correctamente', 'en': 'Saved successfully'},
'edit_lead.version_history': {'es': 'Historial de Versiones', 'en': 'Version History'},
'edit_lead.version': {'es': 'Versión', 'en': 'Version'},
'edit_lead.no_summary': {'es': 'Sin resumen de cambios', 'en': 'No change summary'},
'edit_lead.area_warning': {'es': 'Los metros construidos superan el 80% del terreno.', 'en': 'Built area exceeds 80% of land.'},

# professional.html
'pro.quick_search': {'es': 'Búsqueda rápida', 'en': 'Quick search'},
'pro.operation_type': {'es': 'Tipo de Operación', 'en': 'Operation Type'},
'pro.buy_property': {'es': 'Comprar Propiedad', 'en': 'Buy Property'},
'pro.remodelation': {'es': 'Remodelación Integral', 'en': 'Full Remodelation'},
'pro.build_from_scratch': {'es': 'Construir desde Cero', 'en': 'Build from Scratch'},
'pro.search': {'es': 'Buscar', 'en': 'Search'},
'pro.phone_valid': {'es': 'OK = Tel. válido', 'en': 'OK = Valid phone'},
'pro.toggle_order': {'es': 'Cambiar orden', 'en': 'Toggle order'},
'pro.quick_view': {'es': 'Vista rápida', 'en': 'Quick view'},
'pro.close_quick_view': {'es': 'Cerrar vista rápida', 'en': 'Close quick view'},
'pro.zones': {'es': 'Zonas', 'en': 'Zones'},
'pro.budget_up_to': {'es': 'Hasta', 'en': 'Up to'},
'pro.budget_over': {'es': 'Más de', 'en': 'Over'},

# admin.html
'admin.no_telemetry_data': {'es': 'Sin datos de telemetría en este período', 'en': 'No telemetry data for this period'},
'admin.telemetry_events_note': {'es': 'Los eventos se registrarán a medida que los profesionales interactúen.', 'en': 'Events will be logged as professionals interact.'},
'admin.professional': {'es': 'Profesional', 'en': 'Professional'},
'admin.event': {'es': 'Evento', 'en': 'Event'},
'admin.revealed': {'es': 'Revelado', 'en': 'Revealed'},
'admin.from': {'es': 'Desde', 'en': 'From'},
'admin.to': {'es': 'Hasta', 'en': 'To'},
'admin.prev_page': {'es': 'Página anterior', 'en': 'Previous page'},
'admin.next_page': {'es': 'Página siguiente', 'en': 'Next page'},
'admin.pros_found': {'es': 'profesionales encontrados', 'en': 'professionals found'},
'admin.sort_by': {'es': 'Ordenar por:', 'en': 'Sort by:'},
'admin.name': {'es': 'Nombre', 'en': 'Name'},
'admin.license': {'es': 'Matrícula', 'en': 'License'},
'admin.specialty': {'es': 'Especialidad', 'en': 'Specialty'},
'admin.loading': {'es': 'Cargando...', 'en': 'Loading...'},
'admin.search_option_placeholder': {'es': 'Buscar opción...', 'en': 'Search option...'},
'admin.cancel': {'es': 'Cancelar', 'en': 'Cancel'},
'admin.admin_action': {'es': 'Acción administrativa', 'en': 'Admin action'},
'admin.disable_account': {'es': 'Dar de Baja', 'en': 'Disable Account'},
'admin.user_label': {'es': 'Usuario:', 'en': 'User:'},
'admin.close': {'es': 'Cerrar', 'en': 'Close'},
'admin.disable_warning': {'es': 'El usuario perderá acceso inmediatamente...', 'en': 'The user will lose access immediately...'},
'admin.reason_optional': {'es': 'Motivo (opcional)', 'en': 'Reason (optional)'},
'admin.disable_reason_placeholder': {'es': 'Ej: Datos falsos, spam, conducta inapropiada...', 'en': 'E.g.: Fake data, spam, inappropriate behavior...'},
'admin.disable': {'es': 'Dar de Baja', 'en': 'Disable'},
'admin.end_of_recent_log': {'es': 'Fin del registro reciente', 'en': 'End of recent log'},
'admin.events_will_appear': {'es': 'Los eventos aparecerán cuando los profesionales interactúen con los teléfonos.', 'en': 'Events will appear when professionals interact with phones.'},
'admin.no_access': {'es': 'Sin acceso registrado', 'en': 'No access recorded'},

# user.html
'user.no_max_limit': {'es': 'Sin límite máximo', 'en': 'No max limit'},
'user.reset': {'es': 'Restablecer', 'en': 'Reset'},
'user.accept': {'es': 'Aceptar', 'en': 'Accept'},
'user.area_warning': {'es': 'Los metros construidos superan el 80% del terreno.', 'en': 'Built area exceeds 80% of land.'},
'user.indoor_pool': {'es': 'Pileta cubierta', 'en': 'Indoor pool'},
'user.club_house': {'es': 'Club House', 'en': 'Club House'},
'user.sports_courts': {'es': 'Canchas deportivas', 'en': 'Sports courts'},
'user.artificial_lagoons': {'es': 'Lagunas artificiales', 'en': 'Artificial lagoons'},
'user.floor': {'es': 'Piso', 'en': 'Floor'},
'user.view_360': {'es': 'Vista 360°', 'en': '360° View'},
'user.search_city': {'es': 'Buscar ciudad', 'en': 'Search city'},

# email templates
'email.auto_footer': {'es': 'Este es un correo automático de ArchEstate. No respondas a este mensaje.', 'en': 'This is an automated email from ArchEstate. Do not reply to this message.'},
'email.new_lead': {'es': 'Nuevo lead disponible', 'en': 'New lead available'},
'email.for_your_specialty': {'es': 'Para tu especialidad', 'en': 'For your specialty'},
'email.greeting': {'es': 'Hola', 'en': 'Hello'},
'email.new_lead_desc': {'es': 'Se ha registrado un nuevo lead que puede ser de tu interés. Acá tenés los detalles:', 'en': 'A new lead has been registered that may be of your interest. Here are the details:'},
'email.operation': {'es': 'Operación', 'en': 'Operation'},
'email.budget': {'es': 'Presupuesto', 'en': 'Budget'},
'email.location': {'es': 'Ubicación', 'en': 'Location'},
'email.zone': {'es': 'Zona', 'en': 'Zone'},
'email.province': {'es': 'Provincia', 'en': 'Province'},
'email.property': {'es': 'Propiedad', 'en': 'Property'},
'email.type': {'es': 'Tipo', 'en': 'Type'},
'email.bedrooms': {'es': 'Dormitorios', 'en': 'Bedrooms'},
'email.bathrooms': {'es': 'Baños', 'en': 'Bathrooms'},
'email.rooms': {'es': 'Ambientes', 'en': 'Rooms'},
'email.total_area': {'es': 'Superficie total', 'en': 'Total area'},
'email.usable_area': {'es': 'Superficie utilizable', 'en': 'Usable area'},
'email.land': {'es': 'Terreno', 'en': 'Land'},
'email.built': {'es': 'Construido', 'en': 'Built'},
'email.features': {'es': 'Características', 'en': 'Features'},
'email.parking': {'es': 'Cochera', 'en': 'Parking'},
'email.orientation': {'es': 'Orientación', 'en': 'Orientation'},
'email.condition': {'es': 'Estado', 'en': 'Condition'},
'email.age': {'es': 'Antigüedad', 'en': 'Age'},
'email.style': {'es': 'Estilo', 'en': 'Style'},
'email.elevator': {'es': 'Ascensor', 'en': 'Elevator'},
'email.pool': {'es': 'Piscina', 'en': 'Pool'},
'email.community_pool': {'es': 'Piscina comunitaria', 'en': 'Community pool'},
'email.floor_block': {'es': 'Piso/Bloque', 'en': 'Floor/Block'},
'email.amenities': {'es': 'Amenities', 'en': 'Amenities'},
'email.client_notes': {'es': 'Notas del cliente', 'en': 'Client notes'},
'email.view_lead': {'es': 'Ver lead en el panel', 'en': 'View lead in panel'},
'email.report_processed': {'es': 'Reporte procesado', 'en': 'Report processed'},
'email.lead_deleted_admin': {'es': 'Lead eliminado por administrador', 'en': 'Lead deleted by admin'},
'email.action': {'es': 'Acción', 'en': 'Action'},
'email.deleted': {'es': 'Eliminado', 'en': 'Deleted'},
'email.report_reason': {'es': 'Motivo del reporte', 'en': 'Report reason'},
'email.status_update': {'es': 'Actualización de lead', 'en': 'Lead update'},
'email.new_status': {'es': 'Nuevo estado', 'en': 'New status'},
'email.account_status': {'es': 'Estado de tu cuenta', 'en': 'Your account status'},
'email.approved': {'es': 'aprobada', 'en': 'approved'},
'email.rejected': {'es': 'rechazada', 'en': 'rejected'},
'email.not_approved': {'es': 'Cuenta no aprobada', 'en': 'Account not approved'},
'email.approved_msg': {'es': '¡Tu cuenta ha sido aprobada! Ya puedes acceder a la plataforma.', 'en': 'Your account has been approved! You can now access the platform.'},
'email.rejected_msg': {'es': 'Tu cuenta no fue aprobada. Por favor, contactá al administrador.', 'en': 'Your account was not approved. Please contact the administrator.'},
'email.password_reset_title': {'es': 'Restablece tu contraseña', 'en': 'Reset your password'},
'email.password_reset_subtitle': {'es': 'Solicitud de recuperación', 'en': 'Password recovery request'},
'email.password_reset_desc': {'es': 'Recibimos una solicitud para restablecer tu contraseña.', 'en': 'We received a request to reset your password.'},
'email.password_reset_cta': {'es': 'Restablecer contraseña', 'en': 'Reset password'},
'email.password_reset_expiry': {'es': 'Este enlace expira en 1 hora.', 'en': 'This link expires in 1 hour.'},
'email.password_reset_ignore': {'es': 'Si no solicitaste este cambio, ignorá este mensaje.', 'en': 'If you did not request this change, ignore this message.'},
```

---

## Orden de Implementación

### Fase 1: Responsive (cambios 1-13)
- Impacto visual inmediato
- Bajo riesgo
- Testing manual en 320px, 768px, 1024px, 1280px

### Fase 2: Cross-browser (cambio 14)
- Scrollbar Firefox en admin

### Fase 3: i18n keys nuevas
- Crear las ~100 keys faltantes en `translations.py`

### Fase 4: i18n `lead_detail.html`
- Template más crítico (0% traducido)
- Usar keys existentes de `prof.pdf_*`

### Fase 5: i18n `edit_lead.html`
- Template crítico (0% traducido)

### Fase 6: i18n `professional.html`
- Filtros, headers de tabla, charts

### Fase 7: i18n `admin.html`
- Filtros, headers, modals

### Fase 8: i18n `user.html`
- Strings dispersos

### Fase 9: i18n Email templates
- Último (menor prioridad visual)
- Los emails ya pueden usar `{{ t() }}` via context processor

---

## Verificación

### Responsive
- [ ] Desktop (1280px+): sin cambios visuales
- [ ] Tablet (768px-1024px): tabs admin scrollan, avatar stackea
- [ ] Mobile (320px-640px): navbar compacta, formularios legibles, KPIs 2x2

### Cross-browser
- [ ] Chrome: scrollbar custom funciona
- [ ] Firefox: scrollbar thin funciona
- [ ] Safari: scrollbar custom funciona
- [ ] Edge: scrollbar custom funciona

### i18n
- [ ] Cambiar idioma a EN en `/mi-perfil`
- [ ] Verificar `lead_detail.html` en inglés
- [ ] Verificar `edit_lead.html` en inglés
- [ ] Verificar `professional.html` filtros en inglés
- [ ] Verificar `admin.html` panel en inglés
- [ ] Verificar emails en inglés (enviar lead, reset password, etc.)
- [ ] Verificar `user.html` formulario en inglés

---

## Notas Técnicas

- **Tailwind v3.4.17**: Standalone CLI binary, sin npm
- **Plugins**: `plugins: []` vacío — no se necesita `scrollbar-hide` plugin
- **Vendor prefixes**: Ya correctos en `base.css`, `user.css`, `profile.css`, `admin.css`
- **`scrollbar-hide`**: NO existe como utility Tailwind — se implementa via CSS manual en `admin.css`
- **Email templates**: SÍ tienen acceso a `{{ t() }}` via `inject_language()` context processor en `middleware.py:136`
- **CSS Grid fallback**: IE11 tiene soporte parcial — no se garantiza (ya EOL)
- **Flex `gap`**: Requiere Chrome 84+, Firefox 63+, Safari 14.1+ — seguro para targets 2020+
