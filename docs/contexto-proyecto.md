# ArchEstate — Contexto Completo del Proyecto

## Descripción General

Plataforma web para conectar clientes que buscan propiedades con profesionales del sector inmobiliario (corredores, tasadores, escribanos, etc.). Los clientes completan un formulario detallado de su búsqueda (lead), y los profesionales acceden a esos leads para contactarlos.

---

## Stack Tecnológico

| Componente | Tecnología |
|---|---|
| Backend | Python 3 + Flask (Application Factory) |
| Base de datos | SQLite (default) / PostgreSQL via `DATABASE_URL` |
| ORM | Ninguno — SQL raw con wrapper de compatibilidad (`services/database.py`) |
| Frontend | Jinja2 templates + Tailwind CSS + JavaScript vanilla |
| Íconos | Lucide (desde unpkg CDN) |
| Chart | Chart.js (bundle local) |
| Fuentes | Newsreader (serif) + Manrope (sans) via Google Fonts |
| SMS/WhatsApp | Twilio (simulado por defecto, real con credenciales) |
| Email | SMTP (Gmail/Outlook/etc.) |
| Autenticación | Flask sessions + remember-me tokens (cookie firmada) |
| Rate limiting | File-based JSON (pendiente migrar a Redis) |
| WSGI | Gunicorn |
| Despliegue | Render (Web Service) |

---

## Arquitectura

### Application Factory (`factory.py`)
```python
app = create_app()
```
1. Configura Flask (secret key, cookies, sesiones)
2. Registra middleware (`middleware.py`)
3. Registra error handlers (`errors.py`)
4. Inicializa DB (`app_setup.init_db()`)
5. Inyecta context processor con `form_options`
6. Registra ruta `/health`
7. Importa y registra 10 blueprints

### Blueprints (10)
| Blueprint | Archivo | Prefijo |
|---|---|---|
| `auth` | `routes/auth_bp.py` | `/` |
| `public` | `routes/public_bp.py` | `/` |
| `client` | `routes/client_bp.py` | `/` |
| `professional` | `routes/professional_bp.py` | `/` |
| `admin` | `routes/admin_bp.py` | `/` |
| `phone` | `routes/phone_bp.py` | `/` |
| `lead` | `routes/lead_bp.py` | `/api/lead` |
| `form_options` | `routes/form_options_bp.py` | `/api/` |
| `whatsapp` | `routes/whatsapp_bp.py` | `/` |
| `profile` | `routes_profile.py` | `/` |

### Middleware Pipeline (`middleware.py`)
En orden de ejecución:
1. `assign_request_id()` — UUID de 12 chars en `g.request_id`
2. `load_current_user()` — carga `g.user` desde `session.user_id`
3. `restore_session_from_remember_cookie()` — restaura sesión desde cookie `remember_token`
4. `security_headers()` (after_request) — CSP, HSTS, X-Frame-Options, etc.
5. `inject_request_id()` — context processor
6. `inject_theme()` — context processor (tema claro/oscuro)

### Error Handlers (`errors.py`)
11 handlers: 400, 403, 404, 409, 410, 413, 429, 500, 502, 503, 504
Cada uno devuelve HTML (template) o JSON según `Accept` header.

### Logging
Structured logging con módulo `logging`, configurado en `factory.py`:
```
%(asctime)s [%(levelname)s] %(name)s: %(message)s
```
No hay `print()` en bloques except (reemplazados por `logger.exception()`).

---

## Rutas Completas (75 endpoints + /health)

### Auth Blueprint — `routes/auth_bp.py`

| Método | Ruta | Función | Descripción |
|---|---|---|---|
| GET, POST | `/register` | `auth.register` | Registro con validación de username, email, phone, password; crea perfil profesional si corresponde |
| GET, POST | `/login` | `auth.login` | Login con verificación, bloqueo de inactivos, remember-me, redirect por rol |
| GET | `/logout` | `auth.logout` | Cierra sesión, revoca remember token, elimina cookie |
| GET | `/api/auth/check-username` | `auth.api_check_username` | Verifica disponibilidad de username vía AJAX |

### Public Blueprint — `routes/public_bp.py`

| Método | Ruta | Función | Descripción |
|---|---|---|---|
| GET | `/` | `public.index` | Landing page |
| GET | `/api/landing/stats` | `public.landing_stats` | Estadísticas para landing (total leads, profesionales, zonas, leads del mes) |
| GET | `/sitemap.xml` | `public.sitemap` | Sitemap XML dinámico (index + profesional) |
| GET | `/robots.txt` | `public.robots` | Robots.txt (deshabilita /admin/, /api/, /login, etc.) |
| GET | `/estadisticas` | `public.budget_stats` | Estadísticas de presupuestos desde DB |
| GET | `/estadisticas-popup` | `public.budget_stats_for_popup` | Valores fijos para popup de presupuesto |

### Client Blueprint — `routes/client_bp.py`

| Método | Ruta | Función | Descripción |
|---|---|---|---|
| GET | `/usuario` | `client.user_view` | Dashboard del cliente (formulario de solicitud + leads propios) |
| POST | `/api/submit` | `client.submit_lead` | Procesa y guarda un lead (con validación, rate limited) |

### Professional Blueprint — `routes/professional_bp.py`

| Método | Ruta | Función | Descripción |
|---|---|---|---|
| GET | `/profesional` | `professional.professional_view` | Dashboard profesional (pendiente/aprobado) |
| GET | `/profesional/lead/<id>` | `professional.lead_detail` | Detalle individual de lead |
| GET | `/api/leads` | `professional.get_leads_api` | Lista leads con filtros, búsqueda, ordenamiento, tracking |
| GET | `/api/leads/filter-options` | `professional.get_leads_filter_options` | Opciones de filtro disponibles |
| GET | `/api/leads/stats` | `professional.get_leads_stats` | Estadísticas agregadas de leads |
| GET | `/api/leads/stats/export` | `professional.export_stats_csv` | Exporta estadísticas a CSV |
| GET | `/api/leads/stats/export/xlsx` | `professional.export_stats_xlsx` | Exporta estadísticas a XLSX (múltiples sheets) |
| POST | `/api/leads/filter-options/invalidate` | `professional.invalidate_filter_cache` | Invalida caché de filtros |
| GET | `/api/leads/export` | `professional.export_leads_csv` | Exporta leads a CSV |
| GET | `/api/leads/export/xlsx` | `professional.export_leads_xlsx` | Exporta leads a XLSX |
| GET | `/api/lead/<id>/download` | `professional.download_lead_pdf` | Descarga lead como PDF |
| POST | `/api/lead/<id>/toggle-status` | `professional.toggle_lead_status` | Marca/desmarca lead como visto/contactado |
| POST | `/api/lead/<id>/report` | `professional.report_lead` | Reporta lead por teléfono inválido |
| GET | `/api/professional/doc-status` | `professional.get_doc_status` | Estado del documento subido |
| POST | `/api/professional/upload` | `professional.upload_professional_doc` | Sube documento profesional |
| GET | `/profesional/download_doc` | `professional.download_own_doc` | Descarga propio documento |

### Admin Blueprint — `routes/admin_bp.py`

| Método | Ruta | Función | Descripción |
|---|---|---|---|
| GET | `/admin` | `admin.admin_view` | Panel admin con audit logs |
| GET | `/api/professionals` | `admin.get_professionals_api` | Lista profesionales paginados |
| POST | `/api/admin/professional/<id>/status` | `admin.update_pro_status` | Aprueba/rechaza profesional |
| GET | `/api/admin/stats` | `admin.admin_stats` | Estadísticas del dashboard admin |
| GET | `/api/admin/lead/<id>` | `admin.admin_lead_detail` | Detalle de lead para admin |
| GET | `/api/admin/reports` | `admin.get_lead_reports` | Reportes de leads paginados |
| GET | `/api/admin/telemetry` | `admin.get_telemetry` | Telemetría (WhatsApp clicks, OTP, phone reveals, eventos) |
| GET | `/api/admin/phone-audit` | `admin.admin_phone_audit` | Auditoría de revelaciones de teléfono |
| POST | `/api/admin/report/<id>/delete` | `admin.delete_reported_lead` | Elimina lead reportado |
| POST | `/api/admin/report/<id>/dismiss` | `admin.dismiss_report` | Descarta reporte |
| POST | `/api/admin/report/<id>/restore` | `admin.restore_report` | Restaura reporte a pendiente |
| GET | `/admin/download_doc/<user_id>` | `admin.download_professional_doc` | Descarga documento de profesional |
| GET | `/admin/usuarios` | `admin.user_management_view` | Gestión de usuarios |
| GET | `/api/admin/users` | `admin.get_all_users` | Lista todos los usuarios (JSON) |
| POST | `/api/admin/user/<id>/reset-password` | `admin.admin_reset_password` | Resetea contraseña |
| POST | `/api/admin/user/<id>/set-active` | `admin.admin_set_user_active` | Activa/desactiva usuario |

### Phone Blueprint — `routes/phone_bp.py`

| Método | Ruta | Función | Descripción |
|---|---|---|---|
| POST | `/api/user/update-phone` | `phone.update_user_phone` | Actualiza teléfono (invalida OTP si cambia) |
| POST | `/api/phone/send-code` | `phone.send_verification_code` | Envía código OTP por SMS o WhatsApp |
| POST | `/api/phone/verify` | `phone.verify_phone_code` | Verifica código OTP (con rate limiting y bloqueo por intentos) |

### Lead Blueprint — `routes/lead_bp.py`

| Método | Ruta | Función | Descripción |
|---|---|---|---|
| GET | `/api/lead/<id>/r/whatsapp` | `lead.redirect_whatsapp` | Redirige a wa.me con UTM; rate-limited 60/h |
| GET | `/api/lead/<id>/phone` | `lead.reveal_phone` | Revela teléfono del lead al profesional; rate-limited 60/h |
| POST | `/api/lead/<id>/whatsapp-event` | `lead.whatsapp_event` | Registra eventos de telemetría |

### Form Options Blueprint — `routes/form_options_bp.py`

| Método | Ruta | Función | Descripción |
|---|---|---|---|
| GET | `/api/form-options` | `form_options.list_options` | Opciones activas agrupadas por categoría |
| GET | `/api/form-options/all` | `form_options.list_all_options` | Todas las opciones (activas e inactivas) |
| POST | `/api/form-options` | `form_options.create_option` | Crea nueva opción |
| PUT | `/api/form-options/<id>` | `form_options.update_option` | Actualiza opción existente |
| DELETE | `/api/form-options/<id>` | `form_options.delete_option` | Elimina opción |

### WhatsApp Blueprint — `routes/whatsapp_bp.py`

| Método | Ruta | Función | Descripción |
|---|---|---|---|
| POST | `/api/whatsapp/webhook` | `whatsapp.whatsapp_webhook` | Webhook de Twilio WhatsApp; valida firma, verifica teléfono si Body=VERIFICAR |

### Profile Blueprint — `routes_profile.py`

| Método | Ruta | Función | Descripción |
|---|---|---|---|
| GET | `/mi-perfil` | `profile.profile_view` | Página de perfil del usuario |
| GET | `/mi-perfil/lead/<id>/editar` | `profile.edit_lead_view` | Edición de lead con historial de versiones |
| GET | `/api/profile/leads` | `profile.api_get_user_leads` | Lista leads del usuario autenticado |
| GET | `/api/profile/lead/<id>` | `profile.api_get_lead` | Detalle de lead propio |
| PUT | `/api/profile/lead/<id>` | `profile.api_update_lead` | Actualiza lead (crea snapshot de versión) |
| GET | `/api/profile/lead/<id>/versions` | `profile.api_get_lead_versions` | Historial de versiones del lead |
| GET | `/api/profile/user` | `profile.api_get_user` | Datos del perfil del usuario |
| PUT | `/api/profile/user` | `profile.api_update_user` | Actualiza email, teléfono, nombre, bio |
| PUT | `/api/profile/user/password` | `profile.api_change_password` | Cambia contraseña (requiere contraseña actual) |
| GET | `/api/profile/professional` | `profile.api_get_professional` | Perfil profesional básico |
| PUT | `/api/profile/professional` | `profile.api_update_professional` | Actualiza specialty, title, province, zone |
| GET | `/api/profile/settings` | `profile.api_get_settings` | Preferencias del usuario |
| PUT | `/api/profile/settings` | `profile.api_update_settings` | Actualiza preferencias (theme, language, notifications, preferred_channel) |
| GET | `/api/profile/sessions` | `profile.api_get_sessions` | Historial de sesiones/login |
| DELETE | `/api/profile/sessions/<id>` | `profile.api_delete_session` | Elimina entrada de historial de sesión |
| GET | `/api/profile/activity` | `profile.api_get_activity` | Actividad reciente del usuario |
| POST | `/api/profile/user/avatar` | `profile.api_upload_avatar` | Sube avatar |
| DELETE | `/api/profile/user/avatar` | `profile.api_delete_avatar` | Elimina avatar |
| GET | `/api/profile/professional/full` | `profile.api_get_professional_full` | Perfil profesional extendido |
| PUT | `/api/profile/professional/full` | `profile.api_update_professional_full` | Actualiza perfil profesional extendido |
| POST | `/api/profile/professional/photo` | `profile.api_upload_professional_photo` | Sube foto profesional |
| DELETE | `/api/profile/professional/photo` | `profile.api_delete_professional_photo` | Elimina foto profesional |

### App-level

| Método | Ruta | Función | Descripción |
|---|---|---|---|
| GET | `/health` | `factory.health` | Health check con verificación de DB |

---

## Base de Datos — Schema Completo

### Tabla: `users`
Columna original | ALTER agregado después
---|---
`id INTEGER PRIMARY KEY AUTOINCREMENT` | `phone TEXT`
`username TEXT NOT NULL UNIQUE` | `phone_format_valid INTEGER DEFAULT 0`
`email TEXT NOT NULL DEFAULT ''` | `phone_verified INTEGER DEFAULT 0`
`hash TEXT NOT NULL` | `verification_code TEXT DEFAULT ''`
`role TEXT NOT NULL DEFAULT 'client'` | `verification_expires DATETIME`
`doc_path TEXT DEFAULT ''` | `phone_e164 TEXT DEFAULT ''`
`is_active INTEGER NOT NULL DEFAULT 1` | `phone_number_type TEXT DEFAULT ''`
 | `failed_attempts INTEGER DEFAULT 0`
 | `verification_channel TEXT DEFAULT ''`

### Tabla: `leads`
Columnas originales | ALTER agregado después
---|---
`id INTEGER PRIMARY KEY AUTOINCREMENT` | `architectural_style TEXT DEFAULT ''`
`type TEXT NOT NULL` | `bedrooms INTEGER DEFAULT 0`
`property_type TEXT NOT NULL DEFAULT 'departamento'` | `bathrooms INTEGER DEFAULT 0`
`zone TEXT NOT NULL` | `total_area INTEGER DEFAULT 0`
`budget TEXT NOT NULL` | `amenities TEXT DEFAULT ''`
`currency TEXT NOT NULL DEFAULT 'ARG'` | `ambientes INTEGER DEFAULT 0`
`phone TEXT NOT NULL` | `parking TEXT DEFAULT ''`
`email TEXT NOT NULL` | `orientation TEXT DEFAULT ''`
`floor_block TEXT DEFAULT ''` | `property_condition TEXT DEFAULT ''`
`usable_m2 INTEGER DEFAULT 0` | `property_age TEXT DEFAULT ''`
`elevator TEXT DEFAULT ''` | `province TEXT DEFAULT ''`
`land_area INTEGER DEFAULT 0` | `phone_format_valid INTEGER DEFAULT 0`
`built_area INTEGER DEFAULT 0` | `community_pool TEXT DEFAULT ''`
`pool TEXT DEFAULT ''` | `additional_features TEXT DEFAULT ''`
`timestamp DATETIME DEFAULT CURRENT_TIMESTAMP` | `user_id INTEGER REFERENCES users(id)`

### Tabla: `schema_version`
`version INTEGER PRIMARY KEY`, `applied_at TEXT NOT NULL DEFAULT (datetime('now'))`

### Tabla: `user_profiles`
`id INTEGER PRIMARY KEY AUTOINCREMENT`, `user_id INTEGER NOT NULL UNIQUE REFERENCES users(id)`, `first_name TEXT DEFAULT ''`, `last_name TEXT DEFAULT ''`, `bio TEXT DEFAULT ''`, `title TEXT DEFAULT ''`, `avatar_path TEXT DEFAULT ''`, `created_at DATETIME DEFAULT CURRENT_TIMESTAMP`, `updated_at DATETIME DEFAULT CURRENT_TIMESTAMP`

### Tabla: `lead_versions`
`id INTEGER PRIMARY KEY AUTOINCREMENT`, `lead_id INTEGER NOT NULL REFERENCES leads(id)`, `version INTEGER NOT NULL`, `data_snapshot TEXT NOT NULL`, `created_by INTEGER REFERENCES users(id)`, `change_summary TEXT DEFAULT ''`, `edited_at DATETIME DEFAULT CURRENT_TIMESTAMP`

### Tabla: `professionals`
`id INTEGER PRIMARY KEY AUTOINCREMENT`, `user_id INTEGER DEFAULT NULL REFERENCES users(id)`, `name TEXT NOT NULL`, `license TEXT NOT NULL UNIQUE`, `specialty TEXT NOT NULL`, `status TEXT NOT NULL DEFAULT 'pending'`, `license_verified INTEGER DEFAULT 0`, `province TEXT DEFAULT ''`, `zone TEXT DEFAULT ''`

### Tabla: `audit_log`
`id INTEGER PRIMARY KEY AUTOINCREMENT`, `timestamp DATETIME DEFAULT CURRENT_TIMESTAMP`, `action TEXT NOT NULL`, `target TEXT NOT NULL`, `admin TEXT NOT NULL`, `user_id INTEGER REFERENCES users(id)`

### Tabla: `lead_tracking`
`id INTEGER PRIMARY KEY AUTOINCREMENT`, `professional_id INTEGER NOT NULL`, `lead_id INTEGER NOT NULL`, `seen INTEGER NOT NULL DEFAULT 0`, `contacted INTEGER NOT NULL DEFAULT 0`, `seen_at DATETIME DEFAULT NULL`, `contacted_at DATETIME DEFAULT NULL`, `UNIQUE(professional_id, lead_id)`

### Tabla: `lead_reports`
`id INTEGER PRIMARY KEY AUTOINCREMENT`, `lead_id INTEGER NOT NULL`, `reported_by INTEGER NOT NULL`, `reason TEXT NOT NULL DEFAULT 'telefono_inexistente'`, `notes TEXT DEFAULT ''`, `status TEXT NOT NULL DEFAULT 'pending'`, `reviewed_by TEXT DEFAULT NULL`, `reviewed_at DATETIME DEFAULT NULL`, `created_at DATETIME DEFAULT CURRENT_TIMESTAMP`

### Tabla: `professional_profiles`
`id INTEGER PRIMARY KEY AUTOINCREMENT`, `user_id INTEGER NOT NULL UNIQUE REFERENCES users(id)`, `photo_path TEXT DEFAULT ''`, `bio_pro TEXT DEFAULT ''`, `experience_years INTEGER DEFAULT 0`, `services_offered TEXT DEFAULT '[]'`, `portfolio TEXT DEFAULT '[]'`, `availability TEXT DEFAULT '{}'`, `social_links TEXT DEFAULT '{}'`, `fee_range_min REAL DEFAULT 0`, `fee_range_max REAL DEFAULT 0`, `professional_address TEXT DEFAULT ''`, `created_at DATETIME DEFAULT CURRENT_TIMESTAMP`, `updated_at DATETIME DEFAULT CURRENT_TIMESTAMP`

### Tabla: `user_preferences`
`user_id INTEGER PRIMARY KEY REFERENCES users(id)`, `theme TEXT NOT NULL DEFAULT 'light'`, `language TEXT NOT NULL DEFAULT 'es'`, `email_notifications INTEGER NOT NULL DEFAULT 1`, `sms_notifications INTEGER NOT NULL DEFAULT 1`, `lead_alerts INTEGER NOT NULL DEFAULT 1`, `preferred_channel TEXT DEFAULT 'auto'`, `created_at DATETIME DEFAULT CURRENT_TIMESTAMP`, `updated_at DATETIME DEFAULT CURRENT_TIMESTAMP`

### Tabla: `user_login_history`
`id INTEGER PRIMARY KEY AUTOINCREMENT`, `user_id INTEGER NOT NULL REFERENCES users(id)`, `ip_address TEXT DEFAULT ''`, `user_agent TEXT DEFAULT ''`, `created_at DATETIME DEFAULT CURRENT_TIMESTAMP`, `last_active DATETIME DEFAULT CURRENT_TIMESTAMP`

### Tabla: `consent_log`
`id INTEGER PRIMARY KEY AUTOINCREMENT`, `user_id INTEGER NOT NULL REFERENCES users(id)`, `channel TEXT NOT NULL`, `ip TEXT DEFAULT ''`, `user_agent TEXT DEFAULT ''`, `created_at DATETIME DEFAULT CURRENT_TIMESTAMP`

### Tabla: `events`
`id INTEGER PRIMARY KEY AUTOINCREMENT`, `user_id INTEGER REFERENCES users(id)`, `lead_id INTEGER REFERENCES leads(id)`, `event TEXT NOT NULL`, `props_json TEXT DEFAULT ''`, `ip TEXT DEFAULT ''`, `ts DATETIME DEFAULT CURRENT_TIMESTAMP`

### Tabla: `remember_tokens`
`id INTEGER PRIMARY KEY AUTOINCREMENT`, `user_id INTEGER NOT NULL`, `selector TEXT NOT NULL UNIQUE`, `validator_hash TEXT NOT NULL`, `expires_at DATETIME NOT NULL`, `created_at DATETIME DEFAULT CURRENT_TIMESTAMP`, `ip_address TEXT DEFAULT ''`, `user_agent TEXT DEFAULT ''`

### Tabla: `form_options`
`id INTEGER PRIMARY KEY AUTOINCREMENT`, `category TEXT NOT NULL`, `value TEXT NOT NULL`, `label TEXT NOT NULL`, `icon TEXT DEFAULT ''`, `sort_order INTEGER DEFAULT 0`, `is_active INTEGER NOT NULL DEFAULT 1`, `UNIQUE(category, value)`

### Categorías de Form Options
```python
FORM_OPTION_CATEGORIES = [
    'property_type', 'operation_type', 'currency', 'parking',
    'orientation', 'condition', 'age', 'budget_range',
    'province', 'architectural_style', 'amenities'
]
```

---

## Capa de Modelos (`models.py`)

### Funciones de Usuario
| Función | Parámetros | Devuelve |
|---|---|---|
| `get_user_by_id(user_id)` | int | dict o None |
| `get_user_by_username(username)` | str | dict o None |
| `get_user_profile(user_id)` | int | dict o None (con datos de user_profiles JOIN) |
| `update_user_credentials(user_id, email, phone)` | int, str, str | bool (maneja cambio de phone → resetea verified) |
| `update_user_profile(user_id, data)` | int, dict | bool (solo ALLOWED_PROFILE_FIELDS) |
| `update_user_avatar(user_id, path)` | int, str | bool |
| `delete_user_avatar(user_id)` | int | bool |
| `get_user_avatar_path(user_id)` | int | str o None |
| `get_user_activity(user_id, limit=50)` | int, int | list[dict] |
| `get_user_login_history(user_id, limit=20)` | int, int | list[dict] |
| `delete_login_history_entry(entry_id, user_id)` | int, int | bool |

### Funciones de Lead
| Función | Parámetros | Devuelve |
|---|---|---|
| `get_leads(filters=None)` | dict opcional | list[dict] |
| `get_lead_by_id(lead_id)` | int | dict o None |
| `create_lead(data)` | dict | int (lastrowid) |
| `get_user_leads(user_id)` | int | list[dict] (con seen_count, contacted_count) |
| `get_lead_by_id_and_user(lead_id, user_id)` | int, int | dict o None |
| `update_lead(lead_id, data)` | int, dict | bool |
| `get_lead_max_version(lead_id)` | int | int |
| `create_lead_version(lead_id, version, snapshot, user_id, summary)` | varios | int |
| `get_lead_versions(lead_id)` | int | list[dict] |

### Funciones de Profesional
| Función | Parámetros | Devuelve |
|---|---|---|
| `get_professional_by_user_id(user_id)` | int | dict o None |
| `get_professional_by_name(name)` | str | dict o None |
| `get_professional_by_license(license_number)` | str | dict o None |
| `update_professional_profile(user_id, data)` | int, dict | bool |
| `get_professional_full_profile(user_id)` | int | dict o None |
| `create_or_update_professional_profile(user_id, data)` | int, dict | bool |
| `get_professional_photo_path(user_id)` | int | str o None |

### Funciones de Preferencias
| Función | Parámetros | Devuelve |
|---|---|---|
| `get_user_preferences(user_id)` | int | dict (con defaults) |
| `update_user_preferences(user_id, data)` | int, dict | bool |

### Funciones de Form Options
| Función | Parámetros | Devuelve |
|---|---|---|
| `get_form_options(category=None, active_only=True)` | str opcional, bool | list[dict] |
| `get_form_options_by_category(category, active_only=True)` | str, bool | list[str] (solo values) |
| `get_form_option_by_id(option_id)` | int | dict o None |
| `get_form_option_by_id_value(category, value)` | str, str | dict o None |
| `create_form_option(data)` | dict | int |
| `update_form_option(option_id, data)` | int, dict | bool |
| `delete_form_option(option_id)` | int | bool |

### Otras
| Función | Parámetros | Devuelve |
|---|---|---|
| `get_audit_logs(limit=100)` | int | list[dict] |

### Constantes
```python
ALLOWED_PROFILE_FIELDS = {'first_name', 'last_name', 'bio', 'title', 'avatar_path'}
```

---

## Servicios

### `services/database.py` — Abstracción de base de datos
Wrapper que soporta SQLite y PostgreSQL:
- `DBConnection` — objeto conexión con `.execute()`, `.commit()`, `.rollback()`, `.close()`
- `_DBCursor` — cursor con `.lastrowid`, `.rowcount`, `.fetchone()`, `.fetchall()`; convierte `?` → `%s` para PostgreSQL
- `CompatRow` — row que soporta `row['col']` y `row[0]` (dict + index access)
- `get_db_connection()` — elige driver según `config.DATABASE_URL`
- `table_columns(table)` — columnas de una tabla (PRAGMA / information_schema)
- `date_format_sql(column, fmt)` — formateo portable de fechas
- `now_sql()` — NOW() portable
- `is_integrity_error(exc)` — detecta UniqueViolation en ambos drivers

### `services/verifier.py` — Verificación telefónica
Jerarquía OTP:
```
OTPChannel (ABC)
├── SimulatedOTPVerifier (base para simulación)
│   ├── SmsSimulatedVerifier    → print en consola
│   └── WhatsAppSimulatedVerifier → print + link wa.me
├── TwilioSmsVerifier           → Twilio SMS real
└── TwilioWhatsAppVerifier      → Twilio WhatsApp con Content SID (template con botón)
VerifierRouter                  → elige verifier según canal + config
get_default_router()            → router con todos los verifiers registrados
```
- `send_otp(phone_e164, channel, username)` → punto de entrada único
- `TWILIO_SIMULATE=true` fuerza simulación aunque haya credenciales

### `services/email.py` — Envío de emails
`SMTPEmailSender` con fallback a console:
- `send(to, subject, html_body)` → envía por SMTP o imprime en consola

### `services/notifications.py` — Notificaciones transaccionales
- `notify_lead_created(lead_id)` — notifica a profesionales aprobados
- `notify_lead_status_change(lead_id, new_status)` — notifica al cliente
- `notify_professional_status_change(user_id, new_status)` — notifica al profesional
- `notify_report_deleted(report_id, lead_id)` — notifica al dueño del lead
Todas respetan `user_preferences.email_notifications` / `sms_notifications`.

---

## Frontend

### Templates (28 archivos)
```
base.html — Layout principal (nav, footer, scripts, meta tags, dark mode)
├── landing.html — Landing page
├── login.html — Login
├── register.html — Registro
├── user.html — Dashboard cliente (formulario + leads propios)
├── lead_detail.html — Detalle de lead
├── edit_lead.html — Edición de lead
├── professional.html — Dashboard profesional
├── admin.html — Panel admin
├── user_management.html — Gestión de usuarios
├── profile.html — Perfil/configuración
├── errors/400.html ... 504.html — 11 páginas de error
└── email/
    ├── base.html — Layout de emails
    ├── lead_assigned.html
    ├── status_change.html
    ├── professional_status.html
    └── report_deleted.html
```

### CSS (8 archivos en `static/css/`)
| Archivo | Propósito |
|---|---|
| `tailwind.css` | Tailwind compilado (producción) |
| `tailwind.src.css` | Tailwind fuente |
| `base.css` | Estilos globales, dark mode, validación, password strength |
| `admin.css` | Panel admin |
| `landing.css` | Landing page (animaciones, hero) |
| `professional.css` | Dashboard profesional (badges, botones, tablas) |
| `profile.css` | Perfil |
| `user.css` | Formulario cliente |

### JavaScript (13 archivos en `static/js/`)
| Archivo | Propósito |
|---|---|
| `tailwind-config.js` | Config Tailwind (colores custom, fonts) |
| `main.js` | Utilidades globales: toast, validación, budget popup, scroll, modales |
| `dark-mode.js` | Modo oscuro con persistencia |
| `form-options.js` | Carga dinámica de opciones de formulario |
| `user.js` | Interactividad formulario cliente, prefijos de provincia |
| `professional.js` | Dashboard profesional: filtros, botones de estado, upload |
| `admin.js` | Panel admin: acciones de usuario |
| `auth.js` | Validación client-side de login/registro |
| `profile.js` | Edición de perfil, verificación telefónica, avatar |
| `edit_lead.js` | Edición de lead |
| `landing.js` | Landing page (typing effect, contador) |
| `usermgmt.js` | Tabla de gestión de usuarios |
| `chart.umd.min.js` | Chart.js bundle |

### Design Tokens

**Colores custom:**
```js
midnight:       '#000410'  // Texto primario, fondos oscuros, botones
midnight-light: '#101E33'  // Navbar, superficies oscuras secundarias
gold:           '#735A3A'  // Acento principal, hover, bordes activos
gold-light:     '#A68A64'  // Acento secundario
paper:          '#FAF9F7'  // Fondo página (light mode)
paper-dark:     '#F4F3F1'  // Headers de cards, secciones
```
Usar siempre por nombre de clase (`bg-gold`, `text-midnight`), nunca raw hex en templates.

**Fuentes:**
- Serif (títulos): Newsreader (200–800, itálica)
- Sans (cuerpo): Manrope (200–800)
- Labels/badges: Manrope, `text-[10px]`/`text-[9px]`, bold, uppercase, `tracking-widest`

**Dark mode:**
- Toggle via `dark` class en `<html>`
- CSS variables en `base.css` mapean light→dark
- Preferencia persiste en `user_preferences.theme`

---

## Seguridad

### Autenticación
- Decoradores: `@login_required`, `@admin_required`, `@professional_required` (todos checkean `is_active`)
- Sesión regenerada post-login
- Remember-me con cookie firmada (selector:validator_hash + expires_at)
- Logout revoca remember token y elimina cookie

### Headers HTTP
```
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
Strict-Transport-Security: max-age=31536000; includeSubDomains
Referrer-Policy: strict-origin-when-cross-origin
Permissions-Policy: camera=(), microphone=(), geolocation=()
Content-Security-Policy: <diferenciado dev/prod>
```

### CSP (Content Security Policy)
- **Dev**: permite `cdn.tailwindcss.com`, `unpkg.com` (lucide), `fonts.googleapis.com`, `fonts.gstatic.com`
- **Prod**: solo `unpkg.com` (lucide), `fonts.googleapis.com`, `fonts.gstatic.com` — tailwind servido localmente

### Rate Limiting
- File-based (JSON en disco). Pendiente migrar a Redis.
- 100/min en `/login`, `/register`, `/api/submit`, `/api/phone/send-code`
- 6/min en `/api/phone/verify`
- 5/min en cambio de password
- 10/min en guardar perfil
- 60/h en `/api/lead/<id>/r/whatsapp` y `/api/lead/<id>/phone`

### OTP Brute Force Protection
- Máximo 5 intentos fallidos (`OTP_MAX_ATTEMPTS`)
- Lockout hasta que se solicite nuevo código
- Rate limiting separado para send (100/min) y verify (6/min)

### Protección de Datos
- Teléfono de lead solo revelado a profesionales autenticados y aprobados (`/api/lead/<id>/phone`)
- PII en audit_log no expone datos sensibles
- Upload de documentos/drivers validado por extensión (`ALLOWED_EXTENSIONS`)
- SQL allowlist para actualizaciones de perfil

---

## Configuración (`config.py`)

### Variables de Entorno Requeridas
| Variable | Default | Descripción |
|---|---|---|
| `SECRET_KEY` | — (obligatorio) | Clave secreta de Flask |
| `DATABASE_URL` | `''` (SQLite) | Para PostgreSQL: `postgresql://...` |
| `SITE_URL` | `''` | URL del sitio (links absolutos en WhatsApp/email) |
| `PREFER_SECURE_COOKIES` | `'0'` | `'true'` en producción (cookies `__Host-` + Secure) |

### Twilio
| Variable | Default |
|---|---|
| `TWILIO_ACCOUNT_SID` | `''` |
| `TWILIO_AUTH_TOKEN` | `''` |
| `TWILIO_PHONE_NUMBER` | `''` |
| `TWILIO_WHATSAPP_FROM` | `''` |
| `TWILIO_WHATSAPP_CONTENT_SID` | `''` |
| `TWILIO_WHATSAPP_BUTTON_CONTENT_SID` | `''` |
| `TWILIO_SIMULATE` | `true` (fuerza simulación aunque haya credenciales) |

### SMTP
| Variable | Default |
|---|---|
| `SMTP_HOST` | `smtp.gmail.com` |
| `SMTP_PORT` | `587` |
| `SMTP_USER` | `''` |
| `SMTP_PASS` | `''` |
| `SMTP_FROM` | `noreply@archestate.com` |

### OTP
| Constante | Valor |
|---|---|
| `OTP_TTL_MINUTES` | 10 |
| `OTP_MAX_ATTEMPTS` | 5 |

---

## Despliegue (Render)

**Tipo**: Web Service (Python)

**Build**: `pip install -r requirements.txt`

**Start**: `gunicorn wsgi:app --workers 4 --worker-class sync --timeout 120 --access-logfile - --error-logfile -`

**Archivo**: `render.yaml` (blueprint con todas las env vars)

**Dependencias** (`requirements.txt`):
```
flask, werkzeug, openpyxl, pytz, fpdf, phonenumbers, freezegun, twilio, gunicorn, psycopg2-binary
```

**Base de datos**: SQLite por defecto (disco persistente de Render). Listo para migrar a Neon PostgreSQL vía `DATABASE_URL`.

**Redis**: Pendiente migrar rate limiting de archivos a Redis (Render KV).

---

## Tags / Versionado

| Tag | Commit | Descripción |
|---|---|---|
| `v0.0.1` | `9415ad9` | Initial commit |
| `v0.0.2` | `ced5d99` | Revise README with project details and installation guide |
| `v0.0.3` | `df2b05c` | Update README with virtual environment setup instructions |
| `v0.0.4` | `5d7f418` | Update README.md |
| `v0.0.5` | `8a78432` | Add files via upload |
| `v0.0.6` | `a81599c` | Commit inicial: Proyecto ArchEstate con validación de usuarios y leads |
| `v0.0.7` | `585f617` | Merge branch 'main' de GitHub (ArchEstate-MASK-) |
| `v0.0.8` | `fd32e59` | MVP completo con cambios |
| `v0.0.9` | `32ddc2e` | Creacion de Filtros en Admin y Profesionales |
| `v0.0.10` | `2931f7f` | Descarga de matricula y reseteo de contraseñas implementado |
| `v0.0.11` | `ca1522c` | professional.html y admin.html: Filtros arreglados |
| `v0.0.12` | `ab03d47` | admin.html y app.py: Mejora de filtros y baja de profesionales |
| `v0.10.2` | `4fc1ab0` | requirements.txt agregado y README.md mejorado |
| `v0.10.3` | `0729d2f` | user.html y professional.html: Arreglo de tablas y coherencia |
| `v0.11.0` | `66e0d4c` | Refactor: extracción de módulos, rate limiting, validaciones, headers seguridad |
| `v0.11.1` | `0a0e5d9` | Correciones menores a los templates |
| `v0.11.2` | `78d0c51` | feat(security): validaciones, XSS, rate limit y PDF |
| `v0.11.3` | `1a756d1` | Merge pull request #2 from arreglo-version-antigua |
| `v0.11.5` | `d74261e` | feat: mejora UI/UX, coherencia visual y accesibilidad |
| `v0.11.6` | `e291b60` | ui/ux improvements: Landing page interactiva y FAQ |
| `v0.12.0` | `6638719` | professional.html: Toggle visto y contactado |
| `v0.12.1` | `44cb147` | professionals y admin: Funcion de reporte de leads |
| `v0.12.2` | `81e297e` | Funcion de reporte permite la restauracion |
| `v0.12.3` | `1f0e7c1` | user.html: Arreglo de problemas visuales |
| `v0.12.4` | `f51b437` | README.md: tecnologias actualizadas |
| `v0.13.0` | `5a87fd2` | Creacion de funcion de configuracion de usuario |
| `v0.13.1` | `f1f1960` | profile.html: M: Mejora en el ui/ux y en las validaciones |
| `v0.13.2` | `ed2e06d` | profile.html: Carga de imagen y modo oscuro |
| `v0.13.3` | `27a4c39` | Mejora general del modo oscuro y arreglos minimos de configuracion |
| `v0.14.0` | `b7f8a7d` | professionals.html: Funcion de whatsapp implementada |
| `v0.14.1` | `b2c670a` | Mejora de agents.md, design.md y README.md |
| `v0.14.2` | `7196f54` | feat: contacto WhatsApp/SMS, seguridad y limpieza de código |
| `v0.14.3` | `0318732` | professionals.html: Pequeños bug fixes |
| `v0.14.4` | `f32f388` | user.html: Teléfono no editable desde solicitud (primera vez) |
| `v0.14.5` | `d697995` | Mejoras generales en el ui/ux |
| `v0.14.6` | `0c1ec78` | user.html: Mejora del formato del presupuesto |
| `v0.14.7` | `0ae4834` | SEO, accesibilidad y tests: validación SMS, meta tags, WCAG y pytest |
| `v0.14.8` | `61e93d6` | Verificación de teléfonos, contacto WhatsApp/SMS y telemetría |
| `v0.14.9` | `f64b5f5` | Login/Register: recordarme con cookie firmada y validación pre-envío |
| `v0.14.10` | `505bb91` | Teléfonos: PII leaks, coherencia de validación, hardening y limpieza |
| `v0.14.11` | `767d355` | Refactorización: modularización de app.py en blueprints (Application Factory) |
| `v0.14.12` | `1a3c223` | Refactor frontend: modales, dark mode, responsive, JS externo, accesibilidad |
| `v0.14.13` | `103fb59` | fix: mejoras UX header, seguridad, verificación telefónica y edición de leads |
| `v0.14.14` | `fd0438d` | fix: mejoras de seguridad, UX y documentación |
| `v0.14.15` | `2399f89` | fix: accesibilidad, dark mode y corrección de bugs de diseño |
| `v0.14.16` | `9f86536` | fix: corrección de bugs y aumento de rate limits para testing |
| `v0.14.17` | `47deff7` | docs: actualización completa de documentación externa |
| `v0.14.18` | `8a8d135` | feat: animaciones de interfaz y mejoras de UX |
| `v0.14.19` | `72f453a` | fix: mejoras de seguridad, rendimiento, accesibilidad y SEO |
| `v0.15.0` | `00e86e7` | feat: opciones de formulario admin-manageable y correcciones |
| `v0.15.1` | `1f6ef3e` | fix: dashboard, status buttons, search icon y Chart.js local |
| `v0.15.2` | `8bbe451` | feat(phone): city-level area codes (4-digit) + correction button |
| `v0.16.0` | `fc23f5f` | feat: integrate Twilio SMS/WhatsApp for phone verification |
| `v0.16.1` | `df60a20` | feat: notification system, professional lead filtering, province/zone |
| `v0.16.2` | `7e8289d` | fix(a11y): add labels, aria-labels, and for attributes across all templates |
| `v0.16.3` | `9e6dbb1` | fix(frontend): modals outside Jinja block, XSS in 6 JS files |
| `v0.16.4` | `a0fd1c1` | feat(whatsapp): verification webhook with button template support |
| `v0.16.5` | `470180a` | feat(professional): stats export, tab refactoring, and lead improvements |
| `v0.16.6` | `029df0a` | feat(admin): phone click telemetry tracking and dark mode fixes |
| `v0.17.0` | `b092328` | feat(professional): KPI bar, period toolbar, 2-row actions, lead preview drawer |
| `v0.18.0` | `b2ba845` | feat(db): contadores de vistas y contactos en leads del usuario |
| `v0.18.1` | `c041635` | feat(frontend): accesibilidad, diseño responsive, botones y limpieza CSS |
| `v0.18.2` | `776d30a` | feat(seo): sitemap dinámico con lastmod y prioridad a ruta profesional |
| `v0.18.3` | `7a24e44` | fix(seguridad): control de acceso por roles en rutas críticas |
| `v0.18.4` | `a3978c1` | tests: cobertura de perfil de usuario con leads, avatar y preferencias |
| `v0.19.0` | `68806b6` | fix(otp): autocomplete one-time-code en inputs OTP + error handlers |
| `v0.20.0` | `2ea6210` | feat(notifications): budget matching, WhatsApp notifier, channel routing |
| `v0.20.1` | `97b4454` | fix(i18n+ux): corrección de tildes/ñ + fix scope profesional.js |
| `v0.20.2` | `60b529b` | feat(i18n): add core i18n engine with ES/EN translation dictionary |
| `v0.20.3` | `5d49f58` | feat(i18n): Fase 2 — Templates traducidos (300+ keys, 16 templates) |
| `v0.20.4` | `46e0837` | feat(i18n): Fase 3 — Backend traducido (812 keys, 14 archivos Python) |
| `v0.20.5` | `70f0f44` | feat(i18n): Fase 4 — JS dinámico traducido (~280 keys, 10 archivos JS) |
| `v0.20.6` | `42b9f1d` | docs: deploy checklist + README/AGENTS actualizados (env vars, i18n, Render) |
| `v0.20.7` | `9a2a610` | fix(i18n): recargar página al cambiar idioma en profile.js |
| `v0.21.0` | `5d17947` | fix(twilio+frontend): 19 bugs — SMS, webhook, phone update, SQLi, XSS, i18n |
| `v0.21.1` | `6cd66bb` | feat(auth): self-service password recovery flow with forgot/reset |
| `v0.21.2` | `88feac6` | feat(devops): backup script, CI/CD, Sentry, Dependabot, staging |
| `v0.22.0` | `a654093` | feat(security): CSRF protection with Flask-WTF |
| `v0.22.1` | `9f2b55a` | docs: update README (CSRF, password recovery, DevOps, Twilio fixes) |
| `v0.23.0` | `4ad4e4b` | fix: 12 security/quality fixes — webhook, XSS, N+1, CSRF, PDF, rate limiting |
| `v0.23.1` | `9abcaf0` | chore: enhance .gitignore for safe git pull |
| `v0.24.0` | `de3aadd` | feat: paginación, asignación automática de leads y notificaciones internas |
| `v0.24.1` | `4819d68` | perf: quick wins — remove sleep, print→logger, consolidate login connections |
| `v0.24.2` | `d623a65` | refactor: eliminate duplicate DB queries in auth decorators (g.user) |
| `v0.24.3` | `bd2f1b4` | perf: in-memory cache for user_preferences and form_options (TTL 60s) |
| `v0.24.4` | `978ad87` | perf: batch N+1 queries in auto_assign_lead |
| `v0.25.5` | `bb64273` | chore: teardown_appcontext safety-net hook (connection-per-request) |
| `v0.25.6` | `6837e41` | fix: remove duplicate .field-error CSS from user.css |
| `v0.25.7` | `f96f027` | feat(geo): country form option category, seed 11 countries, DB migrations |
| `v0.25.8` | `09ca267` | feat(geo): country selector to lead form with dynamic provinces |
| `v0.25.9` | `1efab5e` | feat(geo): country in professional profile, geo filters, notifications |
| `v0.25.10` | `11f9c26` | feat(notif): delete and paginated history API for notifications |
| `v0.25.11` | `2167d45` | feat(notif): expandable notification history panel with pagination/delete |
| `v0.25.12` | `3567fe2` | feat(admin): notification tab with settings toggles and send log |
| `v0.26.0` | `c27ac12` | feat(i18n): translation keys for country selector and notifications |
| `v0.26.1` | `52e173b` | feat(geo): province filter, dynamic estado/provincia label, notif page |
| `v0.26.2` | `cd9764c` | fix(phone): always prepend 9 for Argentine numbers |
| `v0.26.3` | `b300cee` | fix(phone): ensure 9 prefix in lead form and profile phone flows |
| `v0.26.4` | `e971897` | fix(phone): fix area code extraction bug in formatPhoneWithCountry |
| `v0.26.5` | `d9058ee` | feat(phone): diccionario de códigos de área argentinos |
| `v0.26.6` | `f3983cc` | fix(phone): selects dinámicos de provincia y detección de ciudad |
| `v0.26.7` | `dd44ffb` | fix(phone): atributos de accesibilidad tel al formulario de registro |
| `v0.26.8` | `0b9c6d0` | test(phone): cargar phone-areas.js en tests de sugerencia telefónica |
| `v0.26.9` | `83524a3` | feat(phone): tabla phone_area_codes, modelos CRUD y API admin |
| `v0.26.10` | `b9d3eca` | feat(phone): pestaña admin de códigos de área con buscador y CRUD |
| `v0.26.11` | `1e397d4` | feat(phone): datos de DB para selects de provincia + i18n |
| `v0.27.0` | `21379fe` | test(phone): tests CRUD para phone_area_codes (20 tests) |
| `v0.27.1` | `62beec1` | feat(notif): diferenciar notificaciones por tipo (iconos, colores, badge) |
| `v0.28.0` | `91f97d9` | fix: parsing de cookies, now_sql con formato, email sender y paths en tests |
| `v0.28.1` | `dcd4c9e` | fix: migrar autocomplete a DB, admin password, duplicate validation, seed |
| `v0.28.2` | `5c08ffb` | docs: actualizar README con phone_area_codes, admin password, test count |
| `v0.28.3` | `f86df81` | fix: no limpiar datos de prueba en producción + cache de filtros |
| `v0.28.4` | `253d4d8` | fix(i18n): traducir páginas de error 409/410/413/429 y rate limit |
| `v0.28.5` | `766fc2a` | refactor: renombrar export_helpers y consolidar allowlist profesional |
| `v0.28.6` | `284105e` | fix: eliminar deprecation datetime.utcnow, logger duplicado, logging silencioso |
| `v0.28.7` | `999c715` | test: agregar 59 tests (assignment, webhook, database, client, public, profile) |
| `v0.28.8` | `63393a9` | chore: separar requirements-dev, completar .env-example y actualizar docs |
| `v0.29.0` | `b51b3a4` | feat(ui): suite de animaciones, pulido de interfaz y autocompletado telefónico |
| `v0.29.1` | `b6d489c` | docs: actualizar tabla de tags del proyecto (118 versiones, cobertura completa) |
| `v0.30.0` | `b514ee7` | feat(phone): teléfono multi-país — módulo PhoneSuggest, 10 países y validación backend |
| `v0.30.1` | `bb20ec5` | docs: actualizar README (528 tests, multi-país, roadmap) |
| `v0.30.2` | `14ca1a1` | fix(ui): dropdown de búsqueda de ciudad sin desborde horizontal en móvil |
| `v0.31.0` | `8f02ca7` | feat(ui): motion language — tokens de movimiento, a11y reduced-motion y perf |
| `v0.31.1` | `f3ed49e` | fix(ui): tokens de movimiento auto-referenciales y forgot-password |
| `v0.31.2` | `d0c905c` | feat(ui): scroll reveal extendido, transición de tabs/paneles y micro-interacciones hover |
| `v0.31.3` | `15866a4` | fix(ui): carga de notificaciones fallaba con `pages<=1` (`querySelector('.font-serif p')` → null) |
| `v0.31.4` | `787bcae` | fix(phone): eliminación de acumulación de códigos de área y corrección de 3 códigos AR |

> **Nota:** `v0.11.4` y `v0.25.0`–`v0.25.4` no tienen commit asociado en `main` (huecos de numeración histórica). `v0.11.3`/`v0.11.4` apuntaban originalmente a la rama `arreglo-version-antigua`; `v0.11.4` fue eliminado y `v0.11.3` re-apuntado al merge de `main`.

---

## Estructura de Archivos Clave

```
/
├── app.py                    # Entry point dev (6 lines)
├── wsgi.py                   # Entry point producción (gunicorn)
├── factory.py                # Application Factory
├── config.py                 # Configuración (.env)
├── models.py                 # Capa de acceso a datos
├── middleware.py              # Middleware pipeline
├── errors.py                 # Error handlers
├── app_setup.py              # Inicialización DB + migrations
├── decorators.py             # @login_required, @admin_required, @professional_required
├── rate_limit.py             # Rate limiting file-based
├── utils.py                  # Utilidades varias
├── validators.py             # Validación de email, teléfono
├── render.yaml               # Blueprint de Render
├── requirements.txt
├── .env-example              # Template de variables de entorno
├── design.md                 # Design tokens
├── AGENTS.md                 # Guía para agentes AI
├── .contexto-proyecto.md     # ← Este archivo
├── routes/
│   ├── auth_bp.py            # Login, registro
│   ├── public_bp.py          # Landing, sitemap, robots
│   ├── client_bp.py          # Cliente (formulario leads)
│   ├── professional_bp.py    # Dashboard profesional
│   ├── admin_bp.py           # Panel admin
│   ├── phone_bp.py           # Verificación telefónica
│   ├── lead_bp.py            # Acciones sobre leads (contacto)
│   ├── form_options_bp.py    # CRUD opciones de formulario
│   └── whatsapp_bp.py        # Webhook WhatsApp
├── routes_profile.py         # Perfil de usuario (blueprint separado)
├── services/
│   ├── database.py           # Abstracción de base de datos (SQLite + PostgreSQL)
│   ├── verifier.py           # Verificación OTP (SMS/WhatsApp)
│   ├── email.py              # Envío de emails
│   └── notifications.py      # Notificaciones transaccionales
├── templates/                # Jinja2 templates (28 archivos)
├── static/
│   ├── css/                  # 8 CSS files
│   ├── js/                   # 13 JS files
│   └── uploads/              # Uploads de usuarios
├── tests/                    # 528 tests pytest + 12 tests JS (node:test)
└── .plans/                   # Planes de implementación anteriores
```
