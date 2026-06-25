# Plan: Jerarquía visual Headers > Datos en tablas

**Fecha:** 2026-06-23
**Objetivo:** Los `<th>` de todas las tablas deben dominar visualmente a los `<td>`, manteniendo colores originales del proyecto.

## Cambios

### `<th>` — Todos los archivos
- `p-4` → `px-4 py-4` (más padding vertical)
- `text-[10px]` → `text-[11px]` (un punto más grande)
- `font-bold` → `font-extrabold` (mayor peso visual)

### `<thead>` `<tr>` — Borde dorado separador
- Clase custom `table-header-border` en `base.css`
- Aplicar en `<tr>` dentro de `<thead>` (NO en `<thead>`)

### `<td>` — Datos más sutiles
- `text-sm` → `text-[13px]`
- `text-midnight/60` o `/70` → `text-midnight/50` (normalizar)
- IDs: `font-mono text-xs text-midnight/60` → `font-mono text-[11px] text-midnight/40`

### `<tr>` filas — Borde más sutil
- `border-b border-midnight/5` → `border-b border-midnight/[0.03]`

### Tabla Form Options — Unificar
- `<th>`: `text-midnight/40` → `text-gold`
- `<thead>` `<tr>`: `bg-paper-dark/50` → `bg-paper-dark` + `table-header-border`

### Tabla Sessions (profile.css)
- `.sessions-table th`: padding → `0.875rem 0.75rem`, font-size → `11px`, font-weight → `800`
- `.sessions-table td`: font-size → `0.75rem`
- Agregar `border-bottom: 2px solid rgba(115,90,58,0.25)` + dark variant

### Bugs preexistentes
- `usermgmt.js:23`: `colspan="6"` → `colspan="7"`
- `usermgmt.js:130`: `colspan="6"` → `colspan="7"`

## Archivos modificados
- `templates/admin.html` — 3 tablas
- `templates/professional.html` — 1 tabla
- `templates/user_management.html` — 1 tabla
- `templates/profile.html` — 1 tabla
- `static/js/admin.js` — td classes
- `static/js/professional.js` — td classes
- `static/js/usermgmt.js` — td classes + colspan fix
- `static/js/profile.js` — td classes
- `static/css/base.css` — .table-header-border
- `static/css/profile.css` — sessions table
- `design.md` — actualizar sección Tablas
- `AGENTS.md` — agregar convención
