# Changelog — fix duplicación de área (contra 14ca1a1)

A diferencia de los patches anteriores de esta serie, este está armado **directamente
sobre el commit real de GitHub** (`14ca1a1`, el del rewrite multi-país), no sobre una
versión vieja — así que debería aplicar limpio con `git apply` siempre que no hayan
seguido tocando estos mismos archivos en el medio. Igual, verificá antes de aplicar:
si ya cambiaste `applyProvincePrefix`/`applyPhoneProvincePrefix` de nuevo, avisame.

## Qué se confirmó roto

Antes de tocar nada, reproduje el bug empíricamente contra el código real (no contra
mi sandbox) con un script de Node que simula 3 cambios de provincia seguidos:

- `profile.js` → `applyProvincePrefix()`: terminaba con **18 dígitos** en vez de 11.
- `user.js` → `applyPhoneProvincePrefix()`: terminaba con **16 dígitos** en vez de 11.

El rewrite multi-país (`phone-suggest.js`, 10 países, datos desde la DB) es sólido en
arquitectura, pero estas dos funciones específicas siguen con la lógica vieja: solo
intentan sacar el código de área **que se está por aplicar ahora**, no cualquier
código que haya quedado pegado de una selección anterior de provincia.

## Fix

Mismo enfoque que ya había probado, pero ahora integrado con el módulo nuevo:

- Uso `PhoneSuggest.phoneAreaCodes(countryCode)` como fuente de códigos conocidos
  (en vez de derivarlos de las opciones del `<select>` a mano) — así queda
  automáticamente sincronizado con lo que venga de la DB para cada país, no
  hardcodeado a Argentina.
- Loop de hasta 4 pasadas que en cada una intenta sacar un marcador de móvil (9/15,
  solo para `+54`) y un código de área conocido, hasta que ninguno de los dos
  matchee más. Esto cubre haber cambiado de provincia cualquier cantidad de veces,
  no solo una — lo verifiqué con el mismo escenario de 3 cambios y ahora da
  exactamente 11 dígitos en ambos archivos, sin importar el orden en que se elijan
  las provincias.
- De paso generalicé un chequeo en `user.js` que tenía el código de país argentino
  (`'54'`) hardcodeado para decidir si recortar el prefijo internacional — ahora usa
  el código del país seleccionado (`countryCode.replace('+', '')`), evitando que un
  número de otro país que casualmente empiece con "54" se corte mal.

## Datos: se revirtieron mis 3 correcciones anteriores, las repuse

El rewrite volvió a dejar `app_setup.py` con los códigos de área incorrectos que ya
había corregido en una ronda anterior (probablemente porque ese bloque se reescribió
desde otra base). Repuse las 3 correcciones verificadas:

- Tandil: `239` → `249`
- Necochea: `249` → `2262` (estaba pisado con el código real de Tandil)
- Puerto Iguazú: `377` → `3757`

**Además**, encontré que `static/js/phone-suggest.js` tiene su propio dataset estático
de fallback (`AR_PHONE_AREAS`, usado solo si falla el fetch a la DB) con los mismos 3
errores — lo corregí ahí también para que no queden desincronizados. Ojo: al hacer
esto me equivoqué una vez (inventé una ciudad "Olavarría" para el código huérfano
`239` sin verificarla) y lo revertí antes de commitear — mencionalo si ves algo raro
en el diff de esa zona, quedó limpio pero vale la pena que lo mires vos también.

## Tests

Usé los archivos y helpers de test que ya existen en este codebase (no armé archivos
paralelos como en la ronda anterior):

- `tests/profile_phone_suggestion.test.js` — agregué un test que simula 3 cambios de
  provincia seguidos contra `profile.js`.
- `tests/user_phone_flow.test.js` — mismo caso, usando el helper `buildContext` que
  ya estaba en el archivo, contra `user.js`.

Correlos con `node --test tests/*.test.js` — 14/14 en verde, junto con 528/528 tests
Python y 94/94 checks de coherencia.

## Verificación final

```
node --test tests/*.test.js   → 14 passed
pytest tests/                 → 528 passed
python verify_coherence.py    → 94/94
```

Y los 3 códigos de área corregidos validan correctamente contra `phonenumbers`
(la misma librería que usa `validators.py` en el backend).
