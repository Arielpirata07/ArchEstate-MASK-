# Changelog de fixes — ronda 3

Continúa `fixes-changelog.md` (rondas 1-2). El patch adjunto
(`archestate-session3-fixes.patch`) es **acumulativo**: reemplaza al patch anterior,
no es un delta — incluye todo lo de las rondas 1 y 2 más lo de acá. Aplicar solo
este archivo alcanza.

Mismas reglas que antes: no usar `git apply` literal (el patch está armado sobre
`b51b3a4`), verificar cada punto contra el código actual antes de tocar nada, correr
tests después de cada bloque.

---

## 7. Colores en modo oscuro (botón "crear cuenta" e íconos de login/register)

**No era un bug de código — era un build desactualizado.** `static/css/tailwind.css`
es el CSS que realmente sirve el navegador (Tailwind está precompilado, no corre por
CDN en runtime). Estaba compilado el 30/07, pero `register.html`/`login.html`
recibieron cambios de UI el 04/08 — las clases `dark:bg-gold` (botón) y
`dark:text-white/30` (íconos) estaban en el HTML pero no existían como reglas CSS
compiladas. El navegador las ignoraba silenciosamente.

**Fix:**
- Subí la opacidad de los íconos de `/30` a `/50` (7 íconos entre `login.html` y
  `register.html`) para mejor contraste una vez que la regla exista.
- Reconstruí `static/css/tailwind.css` corriendo `scripts/tailwindcss -c
  tailwind.config.js -i static/css/tailwind.src.css -o static/css/tailwind.css
  --minify` (el binario no tenía permiso de ejecución — también corregido).

**Importante:** este build hay que repetirlo cada vez que se agreguen o cambien
clases `dark:`/nuevas en templates. Si OpenCode no corre este comando como parte de
su flujo, cualquier cambio de estilo nuevo se va a "perder" silenciosamente de la
misma forma. Vale la pena agregarlo a un pre-commit hook o al pipeline de CI.

---

## 8. Autocompletado de teléfono que formatea pero no guarda

Recorrí a fondo la lógica de formateo en `profile.js` (configuración) y `main.js`
(solicitudes) — el código en sí arma números bien formados. El problema real está en
la **data**, no en el JS: **12 de los 70 códigos de área argentinos sembrados en
`phone_area_codes` no son códigos válidos para ningún largo de número posible**
(lo verifiqué programáticamente contra la librería `phonenumbers`, la misma que usa
la validación del backend). El autocompletado arma un número prolijo con un código
de área que después el backend rechaza siempre, sin importar cómo se formatee.

**Verificados y corregidos con fuente real (búsqueda web):**
- Tandil: `239` → `249`
- Necochea: `249` → `2262` (estaba pisado con el código real de Tandil)
- Puerto Iguazú: `377` → `3757`

**Sin verificar — no los toqué para no meter datos igual de malos:**
`2652`/Tupungato, `2653`/Tunuyán, `2811`/Concepción, `2814`/Monteros, `346`/(el
nombre de ciudad en el seed actual es raro, revisar), `375`/Goya, `378`/Oberá,
`3833`/Andalgalá, `3752`/Paso de los Libres, `3753`/Monte Caseros. Cualquiera de
estos va a reproducir el mismo bug ("formatea bien, rechaza al guardar") hasta que
se corrija con una fuente real (ENACOM o similar).

**Archivos:** `app_setup.py` (los 3 códigos corregidos).

---

## 9. Carga de imagen — solo la primera vez funciona

**Causa raíz:** el nombre de archivo del avatar/foto es fijo por usuario
(`user_{id}_avatar.{ext}`, sin timestamp ni hash). El endpoint de subida devolvía
siempre la misma URL (`avatar_url`/`photo_url`). Cuando subís una imagen nueva con
la misma extensión, el navegador ve la MISMA URL de antes y reutiliza la versión
cacheada — no vuelve a pedir el archivo. Por eso "no cambia excepto que actualices
la página" (el refresh fuerza a ignorar el caché en ese escenario).

**Fix:** el backend agrega un query param de cache-busting (`?v=<timestamp>`) a la
URL que devuelve en la respuesta JSON, tanto para el avatar de usuario como para la
foto de perfil profesional. La imagen guardada en la base sigue sin el query param
(no afecta la carga normal de la página, solo la respuesta inmediata después de
subir).

**Archivos:** `routes_profile.py` (`api_upload_avatar`, `api_upload_professional_photo`).

---

## 10. Los 4 KPI ("modales") con datos de leads no reflejan la realidad

Encontré la causa exacta. Los 4 cards (Nuevos / Contactados / Tasa de contacto /
Total) en la vista de leads del profesional se calculaban en el frontend a partir de
`data.leads` — pero esa lista **es solo la página actual** (25 leads por página,
paginado). Si un profesional tiene más de 25 leads, el "Total" mostraba como mucho
25 (lo que trajera esa página), no el total real — mismo problema para "Nuevos" y
"Contactados".

**Fix:** el backend (`/api/leads`) ahora calcula los agregados sobre el **set
completo filtrado** (antes de aplicar LIMIT/OFFSET), no sobre la página, y los
devuelve como `kpi_total`, `kpi_unseen`, `kpi_contacted` en la respuesta. El
frontend usa esos valores en la carga principal (`loadLeads`); la actualización
optimista tras marcar visto/contactado sigue recalculando localmente sobre los
leads visibles como aproximación rápida (se corrige solo en el próximo `loadLeads`).

Agregué un test (`TestLeadKpiAggregates`) que crea 30 leads y confirma que los KPI
reportan el total real aunque la página traiga solo 25.

**Archivos:** `routes/professional_bp.py`, `static/js/professional.js`,
`tests/test_professional_leads.py`.

---

## 11. "Crear solicitudes" en configuración de profesionales — resuelto

Con tu aclaración quedó claro: la pestaña "Solicitudes" (`{{ t('profile.leads') }}`,
id interno `panel-solicitudes`) en `profile.html` es una feature **pensada para
clientes** — muestra los leads que el usuario mismo envió por el formulario público
(`models.get_user_leads(user_id)`, filtra por `leads.user_id`), con un link "crear
solicitud" al formulario público cuando no hay ninguno.

El bug: esa pestaña no estaba condicionada por rol, así que también le aparecía a
los profesionales — donde no tiene sentido, porque un profesional nunca envía sus
propias solicitudes (solo las recibe, en su dashboard dedicado que ya tiene sus
propios KPIs y tabla). Por eso la tabla estaba siempre vacía y "no permitía
gestionar ninguna solicitud": no es que estuviera rota, es que nunca iba a tener
datos para ese tipo de cuenta.

**Fix:** oculté la pestaña y su panel para cuentas con `role == 'professional'`,
con el mismo patrón condicional que ya usa la pestaña "Profesional" un poco más
abajo en el mismo archivo.

**Archivos:** `templates/profile.html`.

---

Con esto quedan resueltos los 13 puntos originales.
