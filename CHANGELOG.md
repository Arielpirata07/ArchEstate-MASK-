# Changelog — ArchEstate

Formato basado en [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/), versionado [SemVer](https://semver.org/lang/es/). Las entradas están ordenadas de la más reciente a la más antigua.

> **Fuente profunda:** la tabla de tags completa (commit + descripción) vive en `.contexto-proyecto.md` (sección "Tags / Versionado"). El log de bugfixes por sesión está en `fixes-changelog.md`.

## [Unreleased]

### Añadido
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
