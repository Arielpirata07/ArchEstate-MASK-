# Explicación para OpenCode — pantalla de cobertura + mejoras

Este patch (`archestate-coverage-ui.patch`) **reemplaza** al de la ronda anterior con
el mismo nombre — no son acumulables, aplicá solo este. Armado directamente sobre
`052fc4b` (el HEAD de GitHub al momento de generarlo). Probá `git apply --check`
primero.

## Qué construye (recordatorio de la ronda anterior)

Sección "Cobertura de leads" en la pestaña "Profesional" de `profile.html`,
conectada a `GET/PUT /api/profile/professional/coverage` (backend que ya existía
sin ninguna UI). Zonas como tags de texto libre + especialidades como checkboxes
sacadas de `form_options.property_type`.

## Qué se agregó en esta vuelta (las "mejoras al propio fix")

**1. Aviso cuando todavía no configuraste nada explícitamente**
`get_professional_coverage()` en el backend devuelve `configured: false` cuando el
profesional nunca guardó cobertura propia — en ese caso, lo que se ve en pantalla
son los valores heredados de su perfil general (zona/especialidad únicas). Antes
esto era invisible: el profesional veía datos precargados sin saber que son un
fallback, no algo que realmente confirmó. Ahora se muestra un banner explicándolo,
que desaparece apenas guarda por primera vez.

**2. Contador y límite de 20 zonas, con validación proactiva**
El backend rechaza más de 20 zonas (`models.MAX_COVERAGE_VALUES`), pero antes el
único feedback era un error genérico después de mandar el request. Ahora:
- Contador visible "X/20" que se actualiza en vivo.
- Al llegar a 20, se deshabilita el input y el botón de agregar — no hace falta
  llegar a que el backend lo rechace.
- Si por algún motivo se intenta agregar de más igual (input reactivado a mano,
  etc.), la función revalida internamente y muestra el mismo mensaje de límite en
  vez de mandar el request y fallar.

**3. Error inline al agregar una zona duplicada**
Antes, agregar una zona que ya estaba en la lista simplemente no hacía nada — sin
explicación, parecía que el botón no funcionaba. Ahora muestra "Esa zona ya está en
la lista" debajo del input.

**4. Estado de guardado en el botón**
Mientras el PUT está en curso, el botón se deshabilita y el texto cambia a
"Guardando..." — evita que un click doble mande dos requests de guardado
superpuestos. Se restaura solo (`finally`) tanto si el guardado sale bien como si
falla.

## Ojo con esto (el mismo patrón de siempre, otra vez)

Textos que arma el JS dinámicamente (contador, mensajes de error inline, label del
botón mientras guarda) necesitan la clave en **`static/js/i18n.js`**, no solo en
`i18n/translations.py`. Ya agregué las que hacían falta para esta pantalla
(`profile.coverage_zone_limit`, `profile.coverage_zone_duplicate`, `profile.saving`,
y `profile.coverage_save` — esta última la necesito en JS porque ahora el botón
restaura su propio label después de guardar, antes solo se renderizaba una vez
desde Jinja). Si en el futuro tocan textos de esta sección, repasen los dos
archivos.

## Tests

`tests/profile_coverage.test.js` pasó de 5 a 12 tests. Mejoré también el mock de
`classList` en el archivo (antes `toggle()`/`contains()` no llevaban estado real,
ahora sí — necesario para poder testear que el aviso de fallback y los estados
disabled se muestran/ocultan correctamente, no solo que la función corre sin
tirar error).

## Verificación

```
node --test tests/*.test.js   → 26 passed
pytest tests/                 → 543 passed
python verify_coherence.py    → 94/94
```
