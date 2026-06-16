# Plan: Opciones de Formulario Admin-Manageable (V2 US)

## Objetivo
Migrar las opciones hardcodeadas de formularios (tipos de propiedad, monedas, estacionamiento, orientación, condición, antigüedad, etc.) a una tabla `form_options` administrable desde el panel de admin.

## Inventario de Opciones a Migrar

| Categoría | Valores actuales | Ubicaciones |
|---|---|---|
| `property_type` | departamento, casa, duplex, penthouse, local_comercial | validators.py:25, client_bp.py:92, user.html:48-64, professional.html:154-176, user.js:7-13 |
| `operation_type` | Comprar Propiedad, Remodelación Integral, Construir desde Cero | validators.py:26, client_bp.py:101, user.html:73-74, professional.html:135-137 |
| `currency` | ARG, USD, EUR | client_bp.py:96, user.html:101-103, edit_lead.html:117-119 |
| `parking` | sin_cochera, simple_cubierta, doble_cubierta, descubierta, garage | user.html:248-259, edit_lead.html:260-271 |
| `orientation` | Norte, Sur, Este, Oeste, Noreste, Noroeste, Sureste, Suroeste | user.html:268-284, edit_lead.html:279-296 |
| `condition` | A estrenar, Usado, A reciclar, En construcción | user.html:295-299, edit_lead.html:305-309 |
| `age` | Hasta 5 años, 5 a 15 años, 15 a 30 años, Más de 30 años | user.html:306-310, edit_lead.html:316-320 |
| `budget_range` | hasta_200k, 200k_500k, 500k_1m, 1m_2m, mas_2m | professional.html:189-207 |
| `province` | 24 provincias argentinas | user.html:164-189, edit_lead.html:85-110 |
| `architectural_style` | 20 estilos (Moderno, Clásico, etc.) | main.js:502-507 |
| `amenities` | 20+ valores (SUM, Terraza, Quincho, etc.) | user.html:338-541, edit_lead.html:338-384 |

## Enfoque: Inline Jinja + JS Renderer (NO async)

Las opciones se inlinean en el HTML via Jinja `tojson` al renderizar la página. No se usa fetch async. La API es solo para el admin CRUD.

**Por qué:** Elimina race conditions, no necesita fallback, funciona sin JS, y el formulario SIEMPRE tiene opciones.

## Archivos a Crear/Modificar

### Crear (3)
- `routes/form_options_bp.py` — Blueprint CRUD API
- `static/js/form-options.js` — Renderizado dinámico de chips/selects
- `tests/test_form_options.py` — Tests de API + modelo

### Modificar (14)
- `app_setup.py` — Tabla `form_options` + seed
- `models.py` — Funciones CRUD + `FORM_OPTION_CATEGORIES`
- `factory.py` — Registrar `form_options_bp`
- `templates/admin.html` — Tab "Opciones"
- `static/js/admin.js` — CRUD opciones + detail genérico
- `templates/user.html` — Inline options + containers dinámicos
- `templates/edit_lead.html` — Inline options + containers dinámicos
- `templates/professional.html` — Inline options + filtros dinámicos
- `static/js/user.js` — Renderizado dinámico
- `static/js/edit_lead.js` — Renderizado dinámico
- `static/js/professional.js` — Filtros dinámicos
- `validators.py` — Validación dinámica contra DB
- `routes/client_bp.py` — Eliminar constantes duplicadas
- `tests/conftest.py` — Fixture `admin_client`

## Orden de Ejecución (18 pasos)

1. DB + seed (`app_setup.py`)
2. Models CRUD (`models.py`)
3. Blueprint API (`routes/form_options_bp.py`)
4. Register blueprint (`factory.py`)
5. Admin UI tab (`templates/admin.html`)
6. Admin JS CRUD (`static/js/admin.js`)
7. form-options.js (`static/js/form-options.js`)
8. Templates inline (`user.html`, `edit_lead.html`, `professional.html`)
9. JS dinámico (`user.js`, `edit_lead.js`, `professional.js`)
10. Validadores (`validators.py` + `client_bp.py`)
11. Tests (`conftest.py` + `test_form_options.py`)
12. Full test suite

## Invariantes de Seguridad
- `INSERT OR IGNORE` + `UNIQUE(category, value)` previene duplicados
- `@admin_required` en todos los endpoints de escritura
- Jinja inline elimina race conditions
- Leads existentes se conservan aunque se desactiven opciones

## Criterios de Aceptación
1. Admin puede CRUD opciones desde tab "Opciones"
2. Formularios muestran opciones dinámicas desde DB
3. Filtros del profesional muestran opciones dinámicas
4. Opciones desactivadas no aparecen en formularios
5. Validación server-side consulta DB
6. Todos los 286 tests originales pasan
7. Tests nuevos pasan
