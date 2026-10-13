# Changelog — Fase 4: Organizaciones (asignación manual)

Armado directamente sobre `3a0b232` (HEAD al momento de generarlo). Probá
`git apply --check` primero.

## Diseño (resumen de lo que acordamos en el chat)

- **Cardinalidad simple**: una organización tiene muchos profesionales, un
  profesional tiene una sola organización (o ninguna). Nada de tabla puente
  `org_members` — un `org_id` nullable directo en `professionals` alcanza. Si en el
  futuro un profesional necesita pertenecer a más de una organización, esa
  migración (columna → tabla puente) es simple y conocida; no hacía falta
  diseñarla de antemano.
- **Leads**: `leads.org_id` nullable. Si un profesional pertenece a una
  organización, ve los leads de esa organización (pool compartido) — el matching
  por zona/especialidad se ignora como filtro duro para esos leads, pero
  `matches_coverage` se sigue calculando igual como señal informativa (no se tira
  la lógica que ya existía, solo deja de ser excluyente).
- **Asignación manual por admin** — confirmaste que por ahora no hay flujo de
  auto-registro por organización, así que no lo construí.

## Qué se agregó

**Schema** (`app_setup.py`): tabla `organizations` (id, name, slug único,
description, is_active, created_at) — creada temprano en el archivo, antes de
cualquier referencia a ella, a diferencia de mi primer intento donde quedó después
(funcionaba igual porque SQLite no valida FKs en ALTER TABLE, pero lo reordené por
prolijidad). `professionals.org_id` y `leads.org_id`, ambos nullable con índice.

**Backend**:
- `models.py`: `slugify()` (con desambiguación automática si el slug ya existe —
  "Inmobiliaria Sur" repetido da "inmobiliaria-sur-2"), CRUD de organizaciones,
  `set_professional_organization()` / `set_lead_organization()` con validación de
  que la org exista y esté activa antes de asignar.
- `routes/organizations_bp.py` (blueprint nuevo, registrado en `factory.py`): CRUD
  admin de organizaciones + los dos endpoints de asignación manual
  (`PUT /api/admin/professionals/<id>/organization`,
  `PUT /api/admin/leads/<id>/organization`).
- `routes/professional_bp.py`: `/api/leads?my_leads=1` ahora resuelve distinto
  según si `professional.org_id` está seteado — org-scoped si tiene organización,
  exactamente el comportamiento de siempre (geo/cobertura) si no la tiene. Un
  profesional independiente no nota ningún cambio.

**UI de admin**:
- Pestaña nueva "Organizaciones" (`admin.html` + `admin.js`): tabla con conteo de
  miembros por organización, modal de crear/editar, baja lógica (desactivar deja
  is_active=0 y desasigna automáticamente a todos sus profesionales y leads —
  nadie queda con una referencia a una organización inactiva).
- Tabla de "Profesionales" existente: columna nueva con un `<select>` inline para
  asignar/cambiar la organización de cada profesional sin salir de la tabla.
- Modal de detalle de un lead (el que ya existía, `viewLeadDetail`): mismo patrón
  de `<select>` para asignar ese lead a una organización. **No armé una tabla
  nueva de gestión masiva de leads** — no existía ninguna en el admin actual (el
  único endpoint de leads para admin es el detalle de uno por uno), así que
  agregar una tabla de leads completa hubiera sido un feature aparte, no parte de
  "asignación manual a organizaciones". Si querés eso, es un pedido separado.

## Tests

`tests/test_organizations.py` (12 tests nuevos): CRUD completo, dedupe de slug,
conteo de miembros, permisos (no-admin no puede gestionar organizaciones), y que
la baja lógica desasigna profesionales y leads correctamente.

`tests/test_professional_leads.py` (+4 tests): un profesional con organización ve
los leads de su organización aunque estén fuera de su zona configurada; no ve
leads de OTRA organización; un profesional sin organización sigue funcionando
exactamente igual que antes (test explícito de no-regresión); `matches_coverage`
se sigue calculando para profesionales con organización.

## Verificación

```
pytest tests/                 → 559 passed
python verify_coherence.py    → 94/94
```

(No corrí los tests JS en esta ronda porque no toqué ningún archivo `.js` con
tests asociados fuera de `admin.js`, que no tiene suite propia todavía — los 26
tests JS existentes de `profile.js`/`user.js` no se ven afectados por estos
cambios y ya estaban en verde en la ronda anterior.)
