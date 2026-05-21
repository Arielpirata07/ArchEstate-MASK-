# 🏛️ ArchEstate - The Private Ledger

<div align="center">

![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=flat&logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-3.0.0-000000?style=flat&logo=flask&logoColor=white)
![SQLite](https://img.shields.io/badge/SQLite-3.x-003B57?style=flat&logo=sqlite&logoColor=white)
![Tailwind](https://img.shields.io/badge/Tailwind_CSS-3.4-06B6D4?style=flat&logo=tailwind-css&logoColor=white)
![License](https://img.shields.io/badge/License-Private-blue?style=flat)

**Estado del Proyecto:** 🚀 MVP Avanzado  
**Última Actualización:** Mayo 2026

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
- Toggle Departamento ↔ Casa con paneles contextuales
- Steppers +/− para ambientes, habitaciones y baños
- Chips de selección para cochera, orientación, estado y antigüedad
- Coherencia automática estado↔antigüedad ("A estrenar" fuerza "Hasta 5 años")
- Barrio privado con sub-opciones (Club House, seguridad, canchas, lagunas)
- Validación de email en tiempo real (cliente + servidor)
- Guardado de teléfono predeterminado en perfil

### 🔹 Dashboard de Profesionales (`/profesional`)
- Panel de estado pendiente con tracker de pasos
- Upload de documentación con drag & drop, preview, barra de progreso
- Validación de tipo (PDF/JPG/PNG) y tamaño (máx 10 MB) en cliente y servidor
- Tabla de leads con 7 columnas bien alineadas
- Filtros avanzados: tipo de operación, tipo de vivienda, zona, rango de inversión
- Chips de rango ($200k / $200k–$500k / $500k–$1M / $1M–$2M / +$2M)
- Tags de filtros activos con X individual para quitar
- Badges en tabla: tipo de vivienda con ícono, cochera, orientación, estado, antigüedad
- Specs compactas por lead: ambientes · habitaciones · baños · m²
- Exportación CSV y XLSX
- Panel colapsable de actualización documental para aprobados

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
- Reset de contraseña con modal, validación de fortaleza y confirmación
- Baja / reactivación de cuenta con campo de motivo
- Protección: no se puede operar sobre otros admins
- Todo registrado en log de auditoría

### 🔹 Seguridad
- Sesiones Flask con roles (`admin`, `professional`, `client`)
- Decoradores `@login_required`, `@admin_required`, `@professional_required`
- Hash de contraseñas con werkzeug
- Cuentas inactivas bloqueadas en login con mensaje claro
- Validación server-side en todos los endpoints
- Auditoría de: teléfonos revelados, uploads, aprobaciones, bajas, resets

---

## 🛠️ Stack Tecnológico

| Capa | Tecnología | Versión |
|------|------------|---------|
| **Backend** | Python 3 + Flask | 3.10+ / 3.0.0 |
| **Base de Datos** | SQLite3 (raw) | stdlib |
| **Frontend** | HTML5 + Vanilla JS | - |
| **Estilos** | Tailwind CSS (CDN) | 3.4 |
| **Gráficas** | Chart.js | 4.4.0 (CDN) |
| **Icons** | Lucide Icons | latest (CDN) |

---

## 📁 Estructura del Proyecto

```
archestate/
├── app.py                    # Servidor principal (~1400 líneas)
├── init_db.py                # Inicialización y migraciones de BD
├── requirements.txt
├── .env
├── database.db
├── AGENTS.md                 # Guía para asistentes AI
├── design.md                 # Sistema de diseño
├── static/
│   ├── css/
│   │   ├── base.css          # Tokens, tipografía, animaciones globales
│   │   ├── landing.css       # Animaciones de landing
│   │   ├── user.css          # Formulario de lead (budget popup, etc.)
│   │   ├── professional.css  # Panel profesional
│   │   └── admin.css         # Panel admin (scroll de audit log)
│   ├── js/
│   │   ├── tailwind-config.js  # Colores y fuentes custom de Tailwind
│   │   └── main.js             # togglePhone(), showToast(), etc.
│   └── uploads/
│       └── docs/             # Documentación subida por profesionales
└── templates/
    ├── base.html             # Layout: nav, flash messages, footer
    ├── landing.html          # Home con animaciones y contadores
    ├── login.html
    ├── register.html
    ├── user.html             # Formulario de lead (multi-sección)
    ├── professional.html     # Panel de leads + upload
    ├── admin.html            # Dashboard + gestión de profesionales
    ├── user_management.html  # Gestión de usuarios (solo admin)
    ├── lead_detail.html      # Detalle de lead para profesional
    └── index.html            # Legacy SPA (no usar)
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

### `leads`
| Columna | Tipo | Notas |
|---------|------|-------|
| `id` | INTEGER PK | |
| `type` | TEXT | Comprar / Construir / Remodelar |
| `property_type` | TEXT | `departamento` / `casa` / etc. |
| `zone` | TEXT | |
| `budget` | TEXT | Valor numérico como string |
| `currency` | TEXT | `ARG` / `USD` / `EUR` |
| `phone` | TEXT | |
| `email` | TEXT | |
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
| `parking` | TEXT | simple_cubierta / garage / etc. |
| `orientation` | TEXT | Norte / Sur / NE / etc. |
| `property_condition` | TEXT | A estrenar / Usado / etc. |
| `property_age` | TEXT | Hasta 5 años / 5 a 15 / etc. |
| `amenities` | TEXT | Comma-separated |
| `architectural_style` | TEXT | |
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

### `audit_log`
| Columna | Tipo | Notas |
|---------|------|-------|
| `id` | INTEGER PK | |
| `timestamp` | DATETIME | |
| `action` | TEXT | Descripción de la acción |
| `target` | TEXT | Objeto afectado |
| `admin` | TEXT | Username del operador |

---

## 🔌 Endpoints de la API

### Leads (Profesionales)
| Método | Endpoint | Descripción |
|--------|----------|-------------|
| `GET` | `/api/leads` | Lista con filtros: `search`, `type`, `property_type`, `zone`, `budget_range`, `sort`, `order` |
| `POST` | `/api/submit` | Crear lead (público) |
| `GET` | `/api/lead/<id>/phone` | Revelar teléfono (auditado) |
| `GET` | `/api/leads/export` | Exportar CSV |
| `GET` | `/api/leads/export/xlsx` | Exportar XLSX |
| `GET` | `/api/lead/<id>/download` | PDF del lead |
| `GET` | `/api/leads/filter-options` | Valores distintos para filtros |

### Profesionales (Admin)
| Método | Endpoint | Descripción |
|--------|----------|-------------|
| `GET` | `/api/admin/professionals` | Lista con filtros de estado/especialidad |
| `POST` | `/api/admin/professional/<id>/status` | Aprobar / Rechazar |

### Usuarios (Admin)
| Método | Endpoint | Descripción |
|--------|----------|-------------|
| `GET` | `/api/admin/users` | Lista con filtros `search`, `role`, `active` |
| `POST` | `/api/admin/user/<id>/reset-password` | Reset de contraseña |
| `POST` | `/api/admin/user/<id>/set-active` | Dar de baja / Reactivar |

### Perfil
| Método | Endpoint | Descripción |
|--------|----------|-------------|
| `GET` | `/api/user/profile` | Datos del usuario autenticado |
| `POST` | `/api/user/update-phone` | Actualizar teléfono |
| `GET` | `/api/professional/doc-status` | Estado del documento subido |
| `POST` | `/api/professional/upload` | Subir documentación |
| `GET` | `/profesional/download_doc` | Descargar propio documento |

### Dashboard (Admin)
| Método | Endpoint | Descripción |
|--------|----------|-------------|
| `GET` | `/api/admin/stats` | Estadísticas para gráficas |

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
python app.py                  # La BD se inicializa automáticamente al arrancar
```

Acceder en `http://127.0.0.1:5000`

---

## 📈 Roadmap

- [ ] Notificaciones internas entre admin y profesional
- [ ] Integración WhatsApp Business API
- [ ] Asignación automática de leads por especialidad y zona
- [ ] Paginación en tabla de leads
- [ ] Vista móvil responsiva completa
- [ ] CSRF protection en formularios
- [ ] Tests automatizados