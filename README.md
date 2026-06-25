# ArchEstate — The Private Ledger

<div align="center">

![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-3.x-000000?style=for-the-badge&logo=flask&logoColor=white)
![SQLite](https://img.shields.io/badge/SQLite-3.x-003B57?style=for-the-badge&logo=sqlite&logoColor=white)
![Tailwind](https://img.shields.io/badge/Tailwind_CSS-3.4-06B6D4?style=for-the-badge&logo=tailwind-css&logoColor=white)
![Chart.js](https://img.shields.io/badge/Chart.js-4.4-FF6384?style=for-the-badge&logo=chartdotjs&logoColor=white)
![Lucide](https://img.shields.io/badge/Lucide_Icons-0.468-735A3A?style=for-the-badge&logo=lucide&logoColor=white)
![License](https://img.shields.io/badge/License-Private-blue?style=for-the-badge)

![Tests](https://img.shields.io/badge/Tests-351%20Passed-brightgreen?style=for-the-badge&logo=pytest&logoColor=white)
![Status](https://img.shields.io/badge/Status-MVP%20Avanzado-0078D4?style=for-the-badge)
![Updated](https://img.shields.io/badge/Updated-Junio%202026-orange?style=for-the-badge)

---

**Plataforma privada de gestión inmobiliaria y arquitectónica**

Conecta clientes de alto nivel adquisitivo con profesionales verificados del sector inmobiliario y arquitectónico.

</div>

---

## Problema que Resuelve

| Problema | Solución ArchEstate |
|----------|---------------------|
| Leads sin contexto técnico suficiente | Formulario dinámico con 20+ especificaciones y opciones gestionables desde admin |
| Datos de clientes expuestos innecesariamente | Revelación bajo demanda con auditoría completa |
| Profesionales no verificados | Directorio con validación documental y aprobación manual |
| Falta de trazabilidad en operaciones | Log de auditoría en tiempo real + versionado de leads |
| Gestión manual de cuentas | Panel admin con baja/reactivación, reset de contraseña y preferencias de usuario |
| Formularios rígidos con opciones hardcodeadas | CRUD de opciones de formulario (11 categorías) configurable desde admin |
| Experiencia de usuario genérica | Dark mode completo, animaciones scroll-triggered, diseño responsive con Tailwind |

---

## Stack Tecnológico

| Capa | Tecnología | Versión |
|------|------------|---------|
| **Backend** | Python 3 + Flask | 3.10+ / 3.x |
| **Base de Datos** | SQLite3 (WAL mode) | stdlib |
| **Frontend** | HTML5 + Vanilla JS | — |
| **Estilos** | Tailwind CSS (CDN) | 3.4 |
| **Gráficas** | Chart.js | 4.4.0 (CDN) |
| **Icons** | Lucide Icons | 0.468.0 (CDN) |
| **Phone validation** | phonenumbers (libphonenumber) | 8.13+ |
| **Phone verification** | Twilio SDK (SMS + WhatsApp) | 9.x+ |
| **Export** | openpyxl (XLSX), fpdf (PDF) | 3.1+ / 1.7+ |
| **Timezone** | pytz | 2023.3+ |
| **Tests** | pytest + freezegun + monkeypatch | 9.x |

---

## Funcionalidades

### Portal de Clientes

| Funcionalidad | Descripción |
|---------------|-------------|
| Formulario multi-sección | Especificaciones técnicas completas: tipo, zona, presupuesto, ambientes, metros², amenities |
| Opciones dinámicas | Tipos de propiedad, operación, moneda, cochera, orientación, etc. cargados desde admin via API |
| Steppers +/− | Selector numérico para ambientes, habitaciones y baños |
| Chips de selección | Cochera, orientación, estado y antigüedad con toggle visual |
| Coherencia automática | "A estrenar" fuerza "Hasta 5 años" automáticamente |
| Barrio privado | Sub-opciones: Club House, seguridad, canchas, lagunas |
| Piscina Infinity | Condicional: solo Casa + Piscina checkeada |
| Presupuesto interactivo | Popup con slider dual range, selección de moneda y rango min/max |
| Validación en tiempo real | Email, teléfono, presupuesto, username con feedback visual |

### Verificación Telefónica

| Funcionalidad | Descripción |
|---------------|-------------|
| Formato internacional | Validación con libphonenumber, normalización a E.164 |
| OTP por SMS/WhatsApp | Twilio real o simulado según `TWILIO_SIMULATE` |
| Auto-envío OTP | Se envía automáticamente al abrir el modal de verificación |
| Selector de canal | Preferencia SMS/WhatsApp guardada en `user_preferences` |
| Badges de verificación | Icono de canal (smartphone/message-circle) en perfil, dashboard y admin |
| Brute-force protection | Lockout tras 5 intentos fallidos (`failed_attempts`) |
| Preview en vivo | Formato E.164 visible debajo del input durante escritura |
| Consent logging | Registro de consentimiento por canal en `consent_log` |

### Dashboard de Profesionales

| Funcionalidad | Descripción |
|---------------|-------------|
| Panel de estado pendiente | Tracker de pasos con fondo oscuro y badges de progreso |
| Upload de documentación | Drag & drop, preview por tipo (PDF/imagen), barra de progreso, validación cliente+servidor |
| Tabla de leads | Badges: tipo, cochera, orientación, estado, antigüedad + specs compactas |
| Filtros avanzados | Tipo de operación, vivienda, zona, rango de inversión con tags de filtros activos |
| Toggle Visto/Contactado | Persistencia en DB con animación pulse |
| WhatsApp / SMS | Server-side redirect a wa.me con fallback SMS + telemetría |
| Reportes | Teléfonos inválidos con modal, rate limiting y revisión admin |
| Exportación | CSV y XLSX con datos completos |
| Panel documental | Colapsable para profesionales aprobados con estado de actualización |

### Perfil Profesional Extendido

| Funcionalidad | Descripción |
|---------------|-------------|
| Foto de perfil | Upload con preview, crop automático |
| Bio profesional | Texto libre con límite de caracteres |
| Experiencia | Años de experiencia y servicios ofrecidos |
| Portfolio | Gestión de items con imágenes |
| Disponibilidad horaria | Configuración de horarios |
| Links sociales | Redes sociales con íconos |
| Rango de honorarios | Fee range min/max |

### Panel de Administración

| Tab | Funcionalidades |
|-----|-----------------|
| **Dashboard** | KPIs animados con contadores, tooltips y subtextos contextuales. Selector de período (7d/30d/90d/1a). Toggle Doughnut↔Barra. Filtro de zonas inline. Toggle Línea↔Barras mensual. Exportar PNG de gráficos. Botón refresh global. |
| **Profesionales** | Aprobación/rechazo/desaprobación por fila. Baja y reactivación con modal confirmatorio. Descarga de documentación. Filtros de búsqueda, estado y especialidad. |
| **Usuarios** | Tabla con búsqueda en tiempo real y filtro por rol. Badge de estado por fila. Reset de contraseña con validación de fortaleza. Baja/reactivación con campo de motivo. Protección: no se puede operar sobre otros admins ni sobre uno mismo. |
| **Reportes de Leads** | Vista de leads reportados con acciones: eliminar lead, descartar reporte, restaurar. Detalle en modal con información del reporte. |
| **Opciones de Formulario** | CRUD completo de opciones: crear, editar, activar/desactivar, eliminar. 11 categorías: property_type, operation_type, currency, parking, orientation, condition, age, budget_range, province, architectural_style, amenities. Validación de duplicados y categorías. |

### Gestión de Opciones de Formulario

| Funcionalidad | Descripción |
|---------------|-------------|
| CRUD completo | Crear, leer, actualizar y eliminar opciones desde el panel admin |
| 11 categorías | property_type, operation_type, currency, parking, orientation, condition, age, budget_range, province, architectural_style, amenities |
| Renderizado dinámico | `form-options.js` renderiza botones, chips, selects y botones activos desde la API |
| Validación de duplicados | Previene opciones con el mismo valor en una categoría (constraint UNIQUE) |
| Activar/Desactivar | Toggle de estado sin eliminar, opciones inactivas no aparecen en formularios públicos |
| Seed inicial | 50+ opciones predefinidas cargadas automáticamente al iniciar |

### Perfil y Configuración de Usuario

| Funcionalidad | Descripción |
|---------------|-------------|
| Datos personales | Edición de email, teléfono, nombre, bio |
| Cambio de contraseña | Con validación de fortaleza en tiempo real |
| Avatar | Upload con preview y eliminación |
| Preferencias | Theme (dark/light), idioma, notificaciones, canal preferido |
| Sesiones activas | Historial de logins con IP, user_agent, timestamp. Cierre de sesión específica |
| Actividad reciente | Log de acciones del usuario |
| Remember Me | Login persistente via cookies HttpOnly con token selector/validator |

### Seguridad

| Medida | Implementación |
|--------|----------------|
| Sesiones Flask | Roles: admin, professional, client con flags `HttpOnly`, `SameSite=Lax`, `Secure` |
| Decoradores | `@login_required`, `@admin_required`, `@professional_required` — todos verifican `is_active` |
| Cuentas deshabilitadas | Pierden sesión activa inmediatamente |
| Hash de contraseñas | werkzeug con salt |
| Rate limiting | File-backed (JSON + atomic writes) — sobrevive reinicios |
| Brute-force OTP | 5 intentos, lockout con `failed_attempts` |
| SQL allowlist | Updates de perfil y leads solo permiten campos definidos en `ALLOWED_PROFILE_FIELDS` |
| Auditoría | Teléfonos revelados, uploads, aprobaciones, bajas, resets, reportes, remember tokens |
| CSP Header | Content-Security-Policy con allowlists para CDN |
| Admin password | Aleatorio en producción (impreso en consola al arrancar) |
| Session regeneration | Post-login para prevenir session fixation |
| Error handlers | HTML para navegadores, JSON para API: 400/404/409/410/429/500 |

### Frontend / UX

| Funcionalidad | Descripción |
|---------------|-------------|
| Dark mode | Toggle en navbar, persistencia en `user_preferences.theme`, CSS variables, transición 400ms |
| Scroll animations | IntersectionObserver con fade-in-up, slide-in-left/right, stagger delays |
| Skeleton loading | Shimmer placeholders para carga de datos |
| Modal animations | Fade + scale transitions (0.2s) |
| Back to top | Botón fijo con scroll trigger, respeta prefers-reduced-motion |
| Flash messages | Auto-dismissing (5s) con categorías success/error/info |
| Toasts | `showToast()` desde main.js, posición fija bottom-right |
| Hover effects | lift, scale, glow, bright, ripple en cards y botones |
| Password strength | Barra animada 5 etapas (gray/rose/amber/blue/emerald) |
| Username hint | Disponibilidad en tiempo real con debounce |
| Form banners | Errores client-side con estilo rose |
| Budget popup | Slider dual range con inputs numéricos y checkbox "Sin límite" |
| Upload widget | Dropzone → Preview → Progress → Success con estados visuales |
| Status buttons | Visto/Contactado con animación pulse y fill icons |
| Contact buttons | WhatsApp/SMS con tooltips y dark mode adaptado |
| Filter tags | Chips activos con botón X individual |
| Budget display | Currency tag + amount en tablas con hover dotted/solid |

### Rendimiento

| Optimización | Descripción |
|--------------|-------------|
| Cache en `g` | `before_request` carga usuario actual, evita queries repetidas |
| Audit log limit | `LIMIT 200` en consultas de auditoría |
| SQLite WAL | `PRAGMA journal_mode=WAL` + `busy_timeout=5000` en cada conexión |
| Form options cache | `FilterOptionsCache` en `app_setup.py` |

### Accesibilidad (WCAG 2.2)

| Medida | Implementación |
|--------|----------------|
| Skip link | `.skip-link` — aparece al Tab desde el top |
| Focus visible | `outline: 2px solid #735A3A` en todos los interactivos |
| Target size | Mínimo 24×24px en botones y links |
| Modales | `role="dialog"`, `aria-modal="true"`, foco atrapado, Escape cierra |
| Labels | Programáticamente asociados a inputs |
| Reduced motion | `prefers-reduced-motion` coverage completo |
| ARIA | `aria-current="page"` en nav mobile, `aria-label` en botones solo-ícono |

### SEO

| Elemento | Implementación |
|----------|----------------|
| `robots.txt` | Bloquea `/admin/`, `/api/`, `/mi-perfil` |
| `sitemap.xml` | Páginas públicas indexables |
| JSON-LD | Schema `Organization` en landing page |
| Canonical | `<link rel="canonical">` dinámico |
| Meta tags | Títulos únicos por página (50-60 chars), Open Graph + Twitter Cards |
| `lang` | `<html lang="es-AR">` declarado |

---

## Estructura del Proyecto

```
archestate/
├── app.py                    # Entry point (6 líneas)
├── factory.py                # Application Factory: config + middleware + errors + blueprints
├── config.py                 # Reads .env, constants
├── models.py                 # DB access, user CRUD, lead CRUD, form options, preferences
├── app_setup.py              # Schema init + migrations, FilterOptionsCache, form options seed
├── decorators.py             # @login_required, @admin_required, @professional_required
├── rate_limit.py             # File-backed rate limiting (JSON + atomic writes)
├── middleware.py              # Security headers, remember-cookie restore, theme inject
├── errors.py                 # Error handlers (400/404/409/410/429/500)
├── utils.py                  # Phone normalization, logging, remember tokens
├── validators.py             # Email, phone, password, budget, zone validation
├── routes/
│   ├── auth_bp.py            # Login, register, logout
│   ├── public_bp.py          # Landing page, lead detail public
│   ├── client_bp.py          # /usuario, /api/submit
│   ├── professional_bp.py    # /profesional, leads, docs, reports, WhatsApp
│   ├── admin_bp.py           # /admin, stats, user management, reports, telemetry
│   ├── phone_bp.py           # Phone update, OTP send/verify, brute-force
│   ├── lead_bp.py            # WhatsApp redirect, telemetry, lead reports
│   └── form_options_bp.py    # CRUD de opciones de formulario (admin)
├── routes_profile.py         # Profile, lead editing, avatar, settings, sessions, activity
├── services/
│   └── verifier.py           # OTP verifier: SmsSimulated, WhatsAppSimulated, TwilioSms, TwilioWhatsApp + VerifierRouter
├── static/
│   ├── css/                  # base, landing, user, professional, admin, profile
│   ├── js/                   # main, user, professional, admin, profile, edit_lead,
│   │                         #   usermgmt, auth, landing, dark-mode, tailwind-config,
│   │                         #   form-options
│   ├── robots.txt            # SEO — bloquea admin/api
│   ├── sitemap.xml           # SEO — páginas públicas
│   └── uploads/docs/         # Professional document uploads
├── templates/                # 17 templates (base, landing, login, register,
│                             #   user, professional, admin, user_management,
│                             #   edit_lead, lead_detail, profile,
│                             #   errors/400, errors/404, errors/409,
│                             #   errors/410, errors/429, errors/500)
├── tests/                    # 302 tests (pytest + freezegun + monkeypatch)
├── design.md                 # Design system tokens and patterns
├── AGENTS.md                 # AI agent guide
└── requirements.txt
```

---

## Esquema de Base de Datos

### `users`
| Columna | Tipo | Notas |
|---------|------|-------|
| `id` | INTEGER PK | |
| `username` | TEXT UNIQUE | |
| `email` | TEXT | |
| `phone` | TEXT | Actualizable por el usuario |
| `hash` | TEXT | werkzeug hash |
| `role` | TEXT | `admin` / `professional` / `client` |
| `doc_path` | TEXT | Filename en `static/uploads/docs/` |
| `is_active` | INTEGER | `1` activo / `0` dado de baja |
| `phone_verified` | INTEGER | `1` si verificó OTP |
| `phone_e164` | TEXT | Número normalizado E.164 |
| `phone_number_type` | TEXT | mobile / fixed_line / voip |
| `phone_format_valid` | INTEGER | `1` si libphonenumber lo valida |
| `verification_code` | TEXT | OTP actual |
| `verification_expires` | DATETIME | Expiración del OTP |
| `failed_attempts` | INTEGER | Intentos fallidos de OTP (lockout a 5) |
| `verification_channel` | TEXT | `sms` / `whatsapp` / `''` — canal usado para verificar |

### `leads`
| Columna | Tipo | Notas |
|---------|------|-------|
| `id` | INTEGER PK | |
| `type` | TEXT | Comprar / Construir / Remodelar |
| `property_type` | TEXT | Dinámico desde `form_options` |
| `zone` | TEXT | |
| `province` | TEXT | Provincia argentina |
| `budget` | TEXT | Valor numérico como string |
| `currency` | TEXT | Dinámico desde `form_options` (ARG/USD/EUR) |
| `phone` | TEXT | |
| `email` | TEXT | |
| `user_id` | INTEGER FK | → `users.id` |
| `phone_format_valid` | INTEGER | `1` si el formato es válido |
| `bedrooms` | INTEGER | |
| `bathrooms` | INTEGER | |
| `ambientes` | INTEGER | Concepto argentino |
| `total_area` | INTEGER | m² |
| `usable_m2` | INTEGER | Para departamentos |
| `land_area` | INTEGER | Para casas (terreno) |
| `built_area` | INTEGER | Para casas (construido) |
| `floor_block` | TEXT | Dpto: piso/bloque |
| `elevator` | TEXT | Dpto: sí/no |
| `pool` | TEXT | Casa: sí/no |
| `community_pool` | TEXT | Dpto: piscina comunitaria |
| `parking` | TEXT | Dinámico desde `form_options` |
| `orientation` | TEXT | Dinámico desde `form_options` |
| `property_condition` | TEXT | Dinámico desde `form_options` |
| `property_age` | TEXT | Dinámico desde `form_options` |
| `amenities` | TEXT | Comma-separated, dinámico desde `form_options` |
| `architectural_style` | TEXT | Dinámico desde `form_options` |
| `additional_features` | TEXT | Notas adicionales del cliente |
| `timestamp` | DATETIME | UTC, convertido a UTC-3 al mostrar |

### `professionals`
| Columna | Tipo | Notas |
|---------|------|-------|
| `id` | INTEGER PK | |
| `user_id` | INTEGER FK | → `users.id` (puede ser NULL en datos legacy) |
| `name` | TEXT | |
| `license` | TEXT UNIQUE | Matrícula |
| `specialty` | TEXT | |
| `status` | TEXT | `pending` / `approved` / `rejected` |
| `license_verified` | INTEGER | `1` si verificada |

### `professional_profiles`
| Columna | Tipo | Notas |
|---------|------|-------|
| `user_id` | INTEGER FK UNIQUE | → `users.id` |
| `photo_path` | TEXT | Foto de perfil |
| `bio_pro` | TEXT | Bio profesional |
| `experience_years` | INTEGER | |
| `services_offered` | TEXT | JSON array |
| `portfolio` | TEXT | JSON array |
| `availability` | TEXT | JSON object |
| `social_links` | TEXT | JSON object |
| `fee_range_min` / `fee_range_max` | REAL | Rango de honorarios |
| `professional_address` | TEXT | |

### `form_options`
| Columna | Tipo | Notas |
|---------|------|-------|
| `id` | INTEGER PK | |
| `category` | TEXT NOT NULL | Categoría de la opción |
| `value` | TEXT NOT NULL | Valor interno |
| `label` | TEXT NOT NULL | Etiqueta visible |
| `icon` | TEXT DEFAULT '' | Nombre de ícono Lucide |
| `sort_order` | INTEGER DEFAULT 0 | Orden de aparición |
| `is_active` | INTEGER DEFAULT 1 | `1` activa / `0` inactiva |
| | | UNIQUE(category, value) |

### `lead_versions`
| Columna | Tipo | Notas |
|---------|------|-------|
| `id` | INTEGER PK | |
| `lead_id` | INTEGER FK | → `leads.id` |
| `version` | INTEGER | Número incremental |
| `data_snapshot` | TEXT | JSON con estado previo |
| `created_by` | INTEGER FK | → `users.id` |
| `change_summary` | TEXT | |
| `edited_at` | DATETIME | |

### `lead_tracking`
| Columna | Tipo | Notas |
|---------|------|-------|
| `professional_id` | INTEGER FK | → `users.id` |
| `lead_id` | INTEGER FK | → `leads.id` |
| `seen` | INTEGER | `1` si vio el lead |
| `contacted` | INTEGER | `1` si contactó |
| `seen_at` / `contacted_at` | DATETIME | |
| | | UNIQUE(professional_id, lead_id) |

### `lead_reports`
| Columna | Tipo | Notas |
|---------|------|-------|
| `id` | INTEGER PK | |
| `lead_id` | INTEGER FK | → `leads.id` |
| `reported_by` | INTEGER FK | → `users.id` |
| `reason` | TEXT | `telefono_inexistente` (default) |
| `notes` | TEXT | Notas del profesional |
| `status` | TEXT | `pending` / `deleted` / `dismissed` |
| `reviewed_by` | TEXT | Username del admin |
| `reviewed_at` | DATETIME | |

### `audit_log`
| Columna | Tipo | Notas |
|---------|------|-------|
| `id` | INTEGER PK | |
| `timestamp` | DATETIME | |
| `action` | TEXT | Descripción de la acción |
| `target` | TEXT | Objeto afectado |
| `admin` | TEXT | Username del operador |
| `user_id` | INTEGER FK | → `users.id` |

### Otras tablas
- **`user_preferences`** — theme, language, notification toggles, preferred_channel
- **`user_login_history`** — IP, user_agent, timestamps de login
- **`remember_tokens`** — selector/validator hash para "recordarme"
- **`consent_log`** — consentimiento de verificación por canal
- **`events`** — telemetría de clicks, envíos OTP, etc.

---

## Endpoints de la API

### Leads
| Método | Endpoint | Descripción |
|--------|----------|-------------|
| `POST` | `/api/submit` | Crear lead (requiere sesión) |
| `GET` | `/api/leads` | Lista con filtros: `search`, `type`, `property_type`, `zone`, `budget_range`, `sort`, `order` |
| `GET` | `/api/leads/export` | Exportar CSV |
| `GET` | `/api/leads/export/xlsx` | Exportar XLSX |
| `GET` | `/api/leads/filter-options` | Valores distintos para filtros |
| `GET` | `/api/lead/<id>/phone` | Revelar teléfono (auditado) |
| `GET` | `/api/lead/<id>/download` | PDF del lead |
| `POST` | `/api/lead/<id>/toggle-status` | Toggle Visto/Contactado |
| `POST` | `/api/lead/<id>/report` | Reportar teléfono inválido |
| `POST` | `/api/lead/<id>/whatsapp-event` | Telemetría de clicks WhatsApp/SMS |

### Form Options
| Método | Endpoint | Descripción |
|--------|----------|-------------|
| `GET` | `/api/form-options` | Opciones activas agrupadas por categoría (público) |
| `GET` | `/api/form-options/all` | Todas las opciones incluyendo inactivas (admin) |
| `POST` | `/api/form-options` | Crear opción (admin) |
| `PUT` | `/api/form-options/<id>` | Actualizar opción (admin) |
| `DELETE` | `/api/form-options/<id>` | Eliminar opción (admin) |

### Phone Verification
| Método | Endpoint | Descripción |
|--------|----------|-------------|
| `POST` | `/api/user/update-phone` | Actualizar teléfono (requiere sesión) |
| `POST` | `/api/phone/send-code` | Enviar OTP por SMS/WhatsApp |
| `POST` | `/api/phone/verify` | Verificar código OTP |

### Profile & Settings
| Método | Endpoint | Descripción |
|--------|----------|-------------|
| `GET` | `/api/profile/user` | Datos del usuario autenticado |
| `PUT` | `/api/profile/user` | Actualizar email, teléfono, nombre, bio |
| `PUT` | `/api/profile/user/password` | Cambiar contraseña |
| `POST` | `/api/profile/user/avatar` | Subir avatar |
| `DELETE` | `/api/profile/user/avatar` | Eliminar avatar |
| `GET` | `/api/profile/settings` | Preferencias del usuario |
| `PUT` | `/api/profile/settings` | Actualizar preferencias |
| `GET` | `/api/profile/sessions` | Historial de sesiones |
| `DELETE` | `/api/profile/sessions/<id>` | Cerrar sesión específica |
| `GET` | `/api/profile/activity` | Actividad reciente |

### Lead Editing
| Método | Endpoint | Descripción |
|--------|----------|-------------|
| `GET` | `/api/profile/leads` | Leads del usuario |
| `GET` | `/api/profile/lead/<id>` | Detalle de lead |
| `PUT` | `/api/profile/lead/<id>` | Editar lead (campos permitidos) |
| `GET` | `/api/profile/lead/<id>/versions` | Historial de versiones |

### Professional Profile
| Método | Endpoint | Descripción |
|--------|----------|-------------|
| `GET` | `/api/profile/professional` | Básico |
| `PUT` | `/api/profile/professional` | Actualizar specialty/title |
| `GET` | `/api/profile/professional/full` | Perfil extendido |
| `PUT` | `/api/profile/professional/full` | Actualizar perfil extendido |
| `POST` | `/api/profile/professional/photo` | Subir foto |
| `DELETE` | `/api/profile/professional/photo` | Eliminar foto |
| `GET` | `/api/professional/doc-status` | Estado del documento |
| `POST` | `/api/professional/upload` | Subir documentación |

### Admin
| Método | Endpoint | Descripción |
|--------|----------|-------------|
| `GET` | `/api/admin/stats` | Estadísticas para gráficas |
| `GET` | `/api/admin/professionals` | Lista con filtros |
| `POST` | `/api/admin/professional/<id>/status` | Aprobar / Rechazar |
| `GET` | `/api/admin/users` | Lista con filtros `search`, `role`, `active` |
| `POST` | `/api/admin/user/<id>/reset-password` | Reset de contraseña |
| `POST` | `/api/admin/user/<id>/set-active` | Dar de baja / Reactivar |
| `GET` | `/api/admin/reports` | Reportes de leads |
| `POST` | `/api/admin/report/<id>/delete` | Eliminar lead reportado |
| `POST` | `/api/admin/report/<id>/dismiss` | Descartar reporte |
| `POST` | `/api/admin/report/<id>/restore` | Restaurar reporte |
| `GET` | `/api/admin/telemetry` | Métricas de uso |

---

## Usuarios de Prueba

| Rol | Usuario | Contraseña |
|-----|---------|------------|
| **Admin** | `admin` | `admin123` (solo dev/test) |
| **Profesional** | `pro` | `pro123` |

> En producción, el admin se crea con password aleatorio (impreso en consola al arrancar). Cambiar credenciales después del primer login.

---

## Instalación

```bash
git clone <repo-url> && cd archestate
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env          # Configurar variables de entorno
python app.py                  # La BD se inicializa automáticamente al arrancar
```

Acceder en `http://127.0.0.1:5000`

### Ejecutar Tests

```bash
python -m pytest tests/ -q            # Todos (351)
python -m pytest tests/ -x -v         # Parar en primera falla, verbose
python -m pytest tests/test_file.py   # Archivo individual
```

---

## Variables de Entorno

Las credenciales de Twilio se configuran en el archivo `.env`:

| Variable | Descripción |
|----------|-------------|
| `TWILIO_ACCOUNT_SID` | SID de la cuenta Twilio |
| `TWILIO_AUTH_TOKEN` | Token de autenticación |
| `TWILIO_PHONE_NUMBER` | Número de Twilio para SMS |
| `TWILIO_WHATSAPP_FROM` | Número de WhatsApp sandbox |
| `TWILIO_WHATSAPP_CONTENT_SID` | Content SID para plantillas WhatsApp |
| `TWILIO_SIMULATE` | `true` = códigos en consola, `false` = envío real |

> En desarrollo, `TWILIO_SIMULATE=true` evita consumir créditos del trial.

---

## Roadmap

- [x] Tests automatizados (351 tests)
- [x] Verificación telefónica con OTP
- [x] Edición de leads con versionado
- [x] Tracking Visto/Contactado
- [x] Integración WhatsApp (server-side redirect)
- [x] Perfil profesional extendido
- [x] Baja/reactivación de usuarios
- [x] Session cookie flags + CSP header
- [x] Admin password aleatorio en producción
- [x] Error handlers HTML para navegadores
- [x] Cache de usuario en `g` (rendimiento)
- [x] `aria-current="page"` en nav mobile
- [x] `robots.txt` + `sitemap.xml`
- [x] JSON-LD structured data
- [x] Dark mode completo (admin, user, profile, professional)
- [x] CRUD de opciones de formulario (admin)
- [x] Remember Me (login persistente)
- [x] Preferencias de usuario (theme, idioma, notificaciones)
- [x] Historial de sesiones y actividad
- [x] Validación de duplicados en opciones de formulario
- [x] Integración Twilio (SMS + WhatsApp real o simulado)
- [x] Selector de canal de verificación (SMS/WhatsApp)
- [x] Badges de verificación con icono de canal
- [x] Auto-envío de OTP al abrir modal
- [ ] CSRF protection en formularios
- [ ] Notificaciones internas entre admin y profesional
- [ ] Asignación automática de leads por especialidad y zona
- [ ] Paginación en tabla de leads
