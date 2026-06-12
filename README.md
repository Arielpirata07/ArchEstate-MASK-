# 🏛️ ArchEstate - The Private Ledger

<div align="center">

![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=flat&logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-3.x-000000?style=flat&logo=flask&logoColor=white)
![SQLite](https://img.shields.io/badge/SQLite-3.x-003B57?style=flat&logo=sqlite&logoColor=white)
![Tailwind](https://img.shields.io/badge/Tailwind_CSS-3.4-06B6D4?style=flat&logo=tailwind-css&logoColor=white)
![License](https://img.shields.io/badge/License-Private-blue?style=flat)

**Estado del Proyecto:** 🚀 MVP Avanzado  
**Última Actualización:** Junio 2026

</div>

---

## 📖 Sobre el Proyecto

**ArchEstate** es una plataforma privada que conecta clientes de alto nivel adquisitivo con profesionales verificados del sector inmobiliario y arquitectónico.

Foco del MVP: captura limpia de oportunidades (leads) con especificaciones técnicas detalladas, privacidad de datos bajo demanda, trazabilidad absoluta y gestión administrativa completa.

### 🎯 Problema que Resuelve

| Problema | Solución ArchEstate |
|----------|---------------------|
| Exposición innecesaria de datos de clientes | Revelación bajo demanda con auditoría |
| Profesionales no verificados | Directorio con validación documental |
| Leads sin contexto técnico suficiente | Formulario con 20+ especificaciones |
| Falta de trazabilidad en operaciones | Log de auditoría en tiempo real |
| Gestión manual de cuentas | Panel admin con baja/reactivación |

---

## ✨ Características Implementadas

### 🔹 Portal de Clientes (`/usuario`)
- Formulario multi-sección con especificaciones técnicas completas
- 5 tipos de propiedad: Departamento, Casa, Dúplex, Penthouse, Local Comercial
- Toggle contextual con paneles específicos por tipo
- Steppers +/− para ambientes, habitaciones y baños
- Chips de selección para cochera, orientación, estado y antigüedad
- Coherencia automática estado↔antigüedad ("A estrenar" fuerza "Hasta 5 años")
- Barrio privado con sub-opciones (Club House, seguridad, canchas, lagunas)
- Piscina Infinity condicional (solo Casa + Piscina checkeada)
- Validación de email en tiempo real (cliente + servidor)
- Guardado de teléfono predeterminado en perfil

### 🔹 Edición de Leads (`/mi-perfil/lead/<id>/editar`)
- Formulario de edición con datos precargados
- Chips y steppers duplicados (prefijo `edit-`) para no colisionar con el formulario de creación
- Guardado parcial vía PUT (solo campos permitidos en `ALLOWED_LEAD_EDIT_FIELDS`)
- Versionado de cambios con snapshot en `lead_versions`

### 🔹 Verificación Telefónica
- Validación de formato con libphonenumber (internacional)
- Normalización a E.164 (`phone_e164`)
- OTP por SMS/WhatsApp (simulado en desarrollo)
- Brute-force protection: lockout tras 5 intentos fallidos (`failed_attempts`)
- Consent logging en `consent_log`

### 🔹 Dashboard de Profesionales (`/profesional`)
- Panel de estado pendiente con tracker de pasos
- Upload de documentación con drag & drop, preview, barra de progreso
- Validación de tipo (PDF/JPG/PNG) y tamaño (máx 10 MB) en cliente y servidor
- Tabla de leads con badges: tipo de vivienda, cochera, orientación, estado, antigüedad
- Specs compactas por lead: ambientes · habitaciones · baños · m²
- Filtros avanzados: tipo de operación, tipo de vivienda, zona, rango de inversión
- Tags de filtros activos con X individual para quitar
- Toggle Visto/Contactado con persistencia en DB
- Botón WhatsApp (server-side redirect a wa.me) con fallback SMS
- Reporte de teléfonos inválidos con modal y rate limiting
- Exportación CSV y XLSX
- Panel colapsable de actualización documental para aprobados

### 🔹 Perfil Profesional Extendido (`/mi-perfil`)
- Foto de perfil con upload y preview
- Bio profesional, años de experiencia, servicios ofrecidos
- Portfolio con gestión de items
- Disponibilidad horaria
- Links sociales
- Rango de honorarios

### 🔹 Panel de Administración (`/admin`)
- **Tab Dashboard** — KPIs animados con contadores, tooltips y subtextos contextuales
- Selector de período (7d / 30d / 90d / 1a) para gráfico de actividad
- Toggle Doughnut ↔ Barra en gráfico de tipos
- Filtro de zonas inline en gráfico
- Toggle Línea ↔ Barras en gráfico mensual
- Exportar PNG de cualquier gráfico
- Botón de refresh global con animación
- **Tab Profesionales** — Aprobación/rechazo/desaprobación por fila
- Baja y reactivación de cuenta con modal confirmatorio y log de auditoría
- Descarga de documentación de cada profesional
- Filtros de búsqueda, estado y especialidad con orden configurable
- **Tab Usuarios** → `/admin/usuarios` — vista separada

### 🔹 Gestión de Usuarios (`/admin/usuarios`)
- Tabla con búsqueda en tiempo real y filtro por rol
- Badge de estado (Activo / Baja) por fila
- Reset de contraseña con modal, validación de fortaleza y confirmación
- Baja / reactivación de cuenta con campo de motivo
- Protección: no se puede operar sobre otros admins ni sobre uno mismo
- Todo registrado en log de auditoría

### 🔹 Seguridad
- Sesiones Flask con roles (`admin`, `professional`, `client`)
- Decoradores `@login_required`, `@admin_required`, `@professional_required` — todos verifican `is_active`
- Cuentas deshabilitadas pierden sesión activa inmediatamente
- Hash de contraseñas con werkzeug
- Rate limiting file-backed (JSON + atomic writes) — sobrevive reinicios
- Brute-force protection en OTP (5 intentos, lockout)
- SQL allowlist para updates de perfil y leads
- Auditoría de: teléfonos revelados, uploads, aprobaciones, bajas, resets, reportes

---

## 🛠️ Stack Tecnológico

| Capa | Tecnología | Versión |
|------|------------|---------|
| **Backend** | Python 3 + Flask | 3.10+ / 3.x |
| **Base de Datos** | SQLite3 (raw, WAL mode) | stdlib |
| **Frontend** | HTML5 + Vanilla JS | - |
| **Estilos** | Tailwind CSS (CDN) | 3.4 |
| **Gráficas** | Chart.js | 4.4.0 (CDN) |
| **Icons** | Lucide Icons | 0.468.0 (CDN) |
| **Phone validation** | phonenumbers (libphonenumber) | 8.13+ |

---

## 📁 Estructura del Proyecto

```
archestate/
├── app.py                    # Entry point (6 líneas)
├── factory.py                # Application Factory: config + middleware + errors + blueprints
├── config.py                 # Reads .env, constants (UPLOAD_FOLDER, OTP settings, etc.)
├── models.py                 # DB access, user CRUD, lead CRUD, preferences
├── app_setup.py              # Schema init + migrations (ALTER TABLE), FilterOptionsCache
├── decorators.py             # @login_required, @admin_required, @professional_required
├── rate_limit.py             # File-backed rate limiting (JSON + atomic writes)
├── middleware.py              # Security headers, remember-cookie restore, theme inject
├── errors.py                 # Error handlers
├── utils.py                  # Phone normalization (E.164), logging, remember tokens
├── validators.py             # Email, phone, password, budget, zone validation
├── routes/
│   ├── auth_bp.py            # Login, register, logout
│   ├── public_bp.py          # Landing page, lead detail public
│   ├── client_bp.py          # /usuario, /api/submit
│   ├── professional_bp.py    # /profesional, leads, docs, reports, WhatsApp
│   ├── admin_bp.py           # /admin, stats, user management, reports
│   ├── phone_bp.py           # Phone update, OTP send/verify, brute-force
│   └── lead_bp.py            # WhatsApp redirect, telemetry, lead reports
├── routes_profile.py         # Profile, lead editing, avatar, settings, sessions
├── services/
│   └── verifier.py           # OTP verifier router (WhatsApp/SMS)
├── static/
│   ├── css/                  # base, landing, user, professional, admin, profile
│   ├── js/                   # main, user, professional, admin, profile, edit_lead,
│   │                         # usermgmt, auth, landing, dark-mode, tailwind-config
│   └── uploads/docs/         # Professional document uploads
├── templates/                # 11 Jinja2 templates (base, landing, login, register,
│                             #   user, professional, admin, user_management,
│                             #   edit_lead, lead_detail, profile)
├── tests/                    # 286 tests (pytest + freezegun + monkeypatch)
├── design.md                 # Design system tokens and patterns
├── AGENTS.md                 # AI agent guide
└── requirements.txt
```

---

## 🗄️ Esquema de Base de Datos

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

### `leads`
| Columna | Tipo | Notas |
|---------|------|-------|
| `id` | INTEGER PK | |
| `type` | TEXT | Comprar / Construir / Remodelar |
| `property_type` | TEXT | `departamento` / `casa` / `duplex` / `penthouse` / `local_comercial` |
| `zone` | TEXT | |
| `province` | TEXT | Provincia argentina |
| `budget` | TEXT | Valor numérico como string |
| `currency` | TEXT | `ARG` / `USD` / `EUR` |
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
| `parking` | TEXT | simple_cubierta / garage / etc. |
| `orientation` | TEXT | Norte / Sur / NE / etc. |
| `property_condition` | TEXT | A estrenar / Usado / etc. |
| `property_age` | TEXT | Hasta 5 años / 5 a 15 / etc. |
| `amenities` | TEXT | Comma-separated |
| `architectural_style` | TEXT | |
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

## 🔌 Endpoints de la API

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

## 👤 Usuarios de Prueba

| Rol | Usuario | Contraseña |
|-----|---------|------------|
| **Admin** | `admin` | `admin123` |
| **Profesional** | `pro` | `pro123` |

> ⚠️ Cambiar en producción

---

## 🚀 Guía de Instalación

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
python -m pytest tests/ -q            # Todos (286)
python -m pytest tests/ -x -v         # Parar en primera falla, verbose
python -m pytest tests/test_file.py   # Archivo individual
```

---

## 📈 Roadmap

- [x] Tests automatizados (286 tests)
- [x] Verificación telefónica con OTP
- [x] Edición de leads con versionado
- [x] Tracking Visto/Contactado
- [x] Integración WhatsApp (server-side redirect)
- [x] Perfil profesional extendido
- [x] Baja/reactivación de usuarios
- [ ] Notificaciones internas entre admin y profesional
- [ ] Integración WhatsApp Business API (producción)
- [ ] Asignación automática de leads por especialidad y zona
- [ ] Paginación en tabla de leads
- [ ] Vista móvil responsiva completa
- [ ] CSRF protection en formularios
