# 🏛️ ArchEstate - The Private Ledger

<div align="center">

![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=flat&logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-3.0.0-000000?style=flat&logo=flask&logoColor=white)
![SQLite](https://img.shields.io/badge/SQLite-3.x-003B57?style=flat&logo=sqlite&logoColor=white)
![Tailwind](https://img.shields.io/badge/Tailwind_CSS-3.4-06B6D4?style=flat&logo=tailwind-css&logoColor=white)
![License](https://img.shields.io/badge/License-Private-blue?style=flat)

**Estado del Proyecto:** 🎯 MVP en Desarrollo  
**Última Actualización:** Mayo 2026

</div>

---

## 📖 Sobre el Proyecto

**ArchEstate** es una plataforma privada diseñada para conectar clientes de alto nivel adquisitivo (que buscan comprar, construir o remodelar propiedades) con profesionales verificados del sector inmobiliario y arquitectónico.

Este MVP (Producto Mínimo Viable) se centra en la captura limpia de oportunidades de negocio (leads), protegiendo la privacidad de los clientes mediante un sistema de revelación de datos bajo demanda y trazabilidad absoluta.

### 🎯 Problema que Resuelve

| Problema | Solución ArchEstate |
|----------|---------------------|
| Exposición innecesaria de datos de clientes | Revelación bajo demanda (on-demand reveal) |
| Falta de trazabilidad en ventas | Registro de auditoría en tiempo real |
| Profesionales no verificados | Directorio con verificación admin |
| Conversión baja en formularios | Portal minimalista optimizado |

---

## ✨ Características del MVP

### 🔹 Portal de Clientes
- ✅ Formulario minimalista de alta conversión
- ✅ Captura de requerimientos (tipo propiedad, presupuesto, ubicación)
- ✅ Validación de datos en tiempo real
- ✅ Confirmación visual de envío

### 🔹 Dashboard de Profesionales
- ✅ Panel seguro con protección de datos
- ✅ Los teléfonos de los clientes se revelan individualmente mediante consultas a la API
- ✅ Lista de leads asignados
- ✅ Estado de cada oportunidad (nuevo, contactado, cerrado)

### 🔹 Panel de Administración
- ✅ Directorio de profesionales (alta, edición, eliminación)
- ✅ Registro de auditoría en tiempo real (logs de acceso, revelaciones de datos)
- ✅ Métricas básicas de leads

### 🔹 Seguridad
- ✅ Autenticación por sesiones seguras
- ✅ Protección de rutas (middleware de verificación)
- ✅ Hash de contraseñas (werkzeug)
- ✅ Validación de ingresos

---

## 🛠️ Stack Tecnológico

| Capa | Tecnología | Versión |
|------|------------|---------|
| **Backend** | Python 3 | 3.10+ |
| **Framework** | Flask | 3.0.0 |
| **Base de Datos** | SQLite3 (raw) | stdlib |
| **Frontend** | HTML5 + JavaScript (Vanilla) | - |
| **Estilos** | Tailwind CSS | 3.4 (CDN) |
| **Icons** | Lucide Icons | - |
| **UI Design** | Figma | - |

---

## 📁 Estructura del Proyecto

```
archestate/
├── app.py                 # Punto de entrada (~2100 líneas)
├── config.py              # Constantes centralizadas
├── models.py              # Funciones de base de datos
├── utils.py               # Helpers (timezone, safe_text)
├── validators.py          # Validaciones server-side
├── decorators.py          # @login_required, @admin_required
├── rate_limit.py          # Rate limiting
├── routes_profile.py      # Blueprint de perfil de usuario
├── verify_coherence.py    # Script de verificación de integridad
├── init_db.py             # Inicialización de base de datos
├── requirements.txt       # Dependencias Python
├── .env                   # Variables de entorno
├── AGENTS.md              # Guía para asistentes AI
├── design.md              # Sistema de diseño
├── static/
│   ├── css/
│   │   ├── base.css       # Tokens, tipografía, animaciones
│   │   ├── landing.css    # Estilos de landing page
│   │   ├── user.css       # Estilos de formularios
│   │   ├── professional.css # Panel profesional
│   │   ├── admin.css      # Panel admin
│   │   ├── profile.css    # Perfil de usuario
│   │   └── spa.css        # Legacy SPA
│   └── js/
│       └── tailwind-config.js # Config inline de Tailwind
└── templates/
    ├── base.html          # Layout principal
    ├── index.html         # Landing page / Portal clientes
    ├── landing.html       # Landing alternativo
    ├── login.html         # Inicio de sesión
    ├── register.html      # Registro
    ├── user.html          # Formulario de lead
    ├── professional.html  # Panel de profesionales
    ├── admin.html         # Panel de administración
    ├── profile.html       # Perfil/ajustes
    ├── lead_detail.html   # Detalle de lead
    └── user_management.html # Gestión de usuarios
```

---

## 🚀 Guía de Instalación para el Equipo

### Prerrequisitos
- Python 3.10 o superior
- Git
- Navegador web moderno (Chrome, Firefox, Edge)

### 1. Clonar el repositorio

```bash
git clone <repo-url>
cd archestate
```

### 2. Crear y activar entorno virtual

```bash
# Crear entorno
python -m venv venv

# Activar en Windows:
venv\Scripts\activate

# Activar en Mac/Linux:
source venv/bin/activate
```

### 3. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 4. Inicializar la base de datos

```bash
python init_db.py
```

Esto creará:
- Archivo `database.db` en la raíz del proyecto
- Tablas: `users`, `leads`, `audit_logs`, `professionals`, `user_profiles`, `professional_profiles`, `lead_versions`
- Usuario admin por defecto (si está configurado)

### 5. Iniciar el servidor

```bash
python app.py
```

### 6. Acceder a la aplicación

| Ambiente | URL |
|----------|-----|
| **Local** | `http://127.0.0.1:5000` |
| **Portal Clientes** | `http://127.0.0.1:5000/` |
| **Login** | `http://127.0.0.1:5000/login` |
| **Dashboard** | `http://127.0.0.1:5000/dashboard` (requiere auth) |
| **Admin** | `http://127.0.0.1:5000/admin` (requiere auth) |

---

## ⚙️ Configuración de Variables de Entorno

Crea un archivo `.env` en la raíz del proyecto:

```env
# Configuración de Flask
FLASK_APP=app.py
FLASK_ENV=development
SECRET_KEY=tu-clave-secreta-aqui-minimo-32-caracteres

# Configuración de Base de Datos
DATABASE_URL=sqlite:///database.db
```

> ⚠️ **Nota:** Para producción, cambia `FLASK_ENV=production` y usa una clave secreta segura.

---

## 🔌 Endpoints de la API

| Método | Endpoint | Descripción | Auth |
|--------|----------|-------------|------|
| `GET` | `/api/leads` | Listar todos los leads | ✅ |
| `GET` | `/api/leads/<id>` | Obtener detalle de un lead | ✅ |
| `POST` | `/api/leads/reveal/<id>` | Revelar datos de contacto de un lead | ✅ |
| `POST` | `/api/leads` | Crear nuevo lead (público) | ❌ |
| `GET` | `/api/professionals` | Listar profesionales | ✅ Admin |
| `POST` | `/api/professionals` | Crear profesional | ✅ Admin |
| `GET` | `/api/audit` | Ver logs de auditoría | ✅ Admin |
| `GET` | `/api/profile/leads` | Leads del profesional autenticado | ✅ |
| `GET` | `/api/profile/lead/<id>` | Detalle de lead propio | ✅ |
| `PUT` | `/api/profile/lead/<id>` | Actualizar estado de lead | ✅ |
| `GET` | `/api/profile/user` | Perfil del usuario autenticado | ✅ |
| `PUT` | `/api/profile/user` | Actualizar perfil propio | ✅ |
| `PUT` | `/api/profile/user/password` | Cambiar contraseña | ✅ |
| `GET` | `/api/profile/professional` | Perfil profesional | ✅ |
| `PUT` | `/api/profile/professional` | Actualizar perfil profesional | ✅ |

---

## 👤 Usuarios de Prueba (Default)

| Rol | Usuario | Contraseña |
|-----|---------|------------|
| **Admin** | `admin` | `admin123` |
| **Profesional** | `pro` | `pro123` |

> ⚠️ **Cambiar contraseñas en producción**

---

## 📊 Flujo de Usuario

```
┌──────────────────┐     ┌──────────────────┐     ┌──────────────────┐
│   Cliente        │     │  Profesional     │     │     Admin        │
│   (Público)      │     │   (Auth)         │     │    (Auth)        │
└────────┬─────────┘     └────────┬─────────┘     └────────┬─────────┘
         │                         │                         │
    Envía lead               Ver leads (sin            Gestiona profesionales
    (formulario)            datos de contacto)          y audit logs
         │                         │                         │
         ▼                         ▼                         ▼
    Lead creado            Solicita revelación         Monitoriza actividad
    (privado)              de datos (API)              (trazabilidad total)
```

---

## 🛡️ Características de Seguridad Implementadas

- 🔐 **Autenticación:** Sesiones personalizadas con decoradores
- 🔒 **Protección de rutas:** Decoradores `@login_required` y `@admin_required`
- 🛡️ **Sanitización:** Escape de entradas para prevenir XSS
- 📝 **Auditoría:** Logging de todas las acciones sensibles
- 🔑 **Hashing:** Contraseñas hasheadas con werkzeug.security

---

## 📈 Roadmap (Próximas Iteraciones)

- [ ] Implementación de sistema de notificaciones
- [ ] Integración con WhatsApp Business API
- [ ] Panel de métricas avanzadas (gráficos)
- [ ] Sistema de asignación automática de leads
- [ ] Exportación de leads (CSV/Excel)
- [ ] Multi-idioma (ES/EN)
- [ ] Dashboard móvil responsivo

---

## 🤝 Contributing

1. Fork el repositorio
2. Crear una rama (`git checkout -b feature/nueva-caracteristica`)
3. Commit tus cambios (`git commit -m 'Add nueva caracteristica'`)
4. Push a la rama (`git push origin feature/nueva-caracteristica`)
5. Abrir un Pull Request

---

## 📄 Licencia

**Licencia:** Proprietaria - Todos los derechos reservados

---

## 📧 Contacto

Para consultas técnicas o de negocio, contacta al equipo de desarrollo.

---

<div align="center">

🏛️ **ArchEstate - Conectando propiedades con profesionales de confianza**

*Built with ❤️ for the real estate & architecture community*

</div>