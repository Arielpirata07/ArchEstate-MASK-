# ArchEstate - The Private Ledger

<div align="center">

![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=flat&logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-3.0-000000?style=flat&logo=flask&logoColor=white)
![SQLite](https://img.shields.io/badge/SQLite-3.x-003B57?style=flat&logo=sqlite&logoColor=white)
![Tailwind](https://img.shields.io/badge/Tailwind_CSS-3.4-06B6D4?style=flat&logo=tailwind-css&logoColor=white)
![License](https://img.shields.io/badge/License-Private-blue?style=flat)

**Estado del Proyecto:** Produccion  
**Ultima Actualizacion:** Mayo 2026

</div>

---

## Sobre el Proyecto

**ArchEstate** es una plataforma privada disenada para conectar clientes de alto nivel adquisitivo (que buscan comprar, construir o remodelar propiedades) con profesionales verificados del sector inmobiliario y arquitectonico.

### Problema que Resuelve

| Problema | Solucion ArchEstate |
|----------|---------------------|
| Exposicion innecesaria de datos de clientes | Revelacion bajo demanda (on-demand reveal) |
| Falta de trazabilidad en ventas | Registro de auditoria en tiempo real |
| Profesionales no verificados | Directorio con verificacion admin |
| Conversion baja en formularios | Portal minimalista optimizado |

---

## Caracteristicas

### Portal de Clientes
- Formulario detallado de solicitud con especificaciones tecnicas
- Captura de requerimientos (tipo propiedad, presupuesto, ubicacion, amenities)
- Validacion de datos en tiempo real con feedback visual
- Autocompletado de zonas y estilos arquitectonicos
- Selector de rango de presupuesto interactivo

### Dashboard de Profesionales
- Panel seguro con proteccion de datos
- Telefonos revelados individualmente via API (auditado)
- Filtros avanzados (zona, tipo, presupuesto, rango)
- Exportacion de leads a CSV y XLSX
- Descarga de fichas individuales en PDF
- Metricas en tiempo real (total, nuevos, contactados, convertidos)

### Panel de Administracion
- Dashboard con graficos interactivos (Chart.js)
- Directorio de profesionales con aprobacion/rechazo
- Gestion de usuarios con reset de contraseas
- Baja/reactivacion de cuentas
- Log de auditoria estilo timeline
- Estadisticas cacheadas para rendimiento

### SEO y Accesibilidad
- Meta tags dinamicos (title, description, Open Graph)
- Structured Data (JSON-LD: Organization + FAQPage)
- Sitemap XML generado automaticamente
- Robots.txt configurado
- Lang attribute (es-AR)
- Canonical URLs

### Interactividad
- Animaciones de scroll (Intersection Observer)
- FAQ accordion con expand/collapse suave
- Testimonios carousel con autoplay
- Contadores animados al ser visibles
- Toast notifications con barra de progreso
- Drag & drop para subida de documentos
- Validacion de formularios en tiempo real

### Rendimiento
- Indices en columnas de consulta frecuente
- Paginacion en API de leads
- Cache de estadisticas admin (5 min TTL)
- Lazy loading de imagenes
- Scripts con atributo defer

---

## Stack Tecnologico

| Capa | Tecnologia | Version |
|------|------------|---------|
| **Backend** | Python 3 | 3.10+ |
| **Framework** | Flask | 3.0 |
| **Base de Datos** | SQLite | 3.x |
| **Frontend** | HTML5 + JavaScript (Vanilla) | - |
| **Estilos** | Tailwind CSS | 3.4 (CDN) |
| **Icons** | Lucide Icons | latest |
| **Graficos** | Chart.js | 4.4 |

---

## Arquitectura del Proyecto

```
┌─────────────────────────────────────────────────────────┐
│                     Navegador Web                        │
│  (HTML5 + Tailwind CSS + Vanilla JS + Chart.js)         │
└──────────────────────┬──────────────────────────────────┘
                       │ HTTP Requests
┌──────────────────────▼──────────────────────────────────┐
│                    Flask Application                     │
│  ┌────────────┐  ┌────────────┐  ┌──────────────────┐  │
│  │  app.py    │  │ decorators │  │   rate_limit.py  │  │
│  │  (Routes)  │  │  (Auth)    │  │  (Rate Limiting) │  │
│  └─────┬──────┘  └────────────┘  └──────────────────┘  │
│        │                                                │
│  ┌─────▼──────┐  ┌────────────┐  ┌──────────────────┐  │
│  │ models.py  │  │validators  │  │    utils.py      │  │
│  │  (DB Ops)  │  │  (Input)   │  │   (Helpers)      │  │
│  └─────┬──────┘  └────────────┘  └──────────────────┘  │
└────────┼────────────────────────────────────────────────┘
         │ sqlite3
┌────────▼────────────────────────────────────────────────┐
│                    SQLite Database                       │
│  Tables: users, leads, professionals, audit_log          │
│  Indexes: idx_leads_type, idx_leads_timestamp, etc.      │
└─────────────────────────────────────────────────────────┘
```

### Modulos del Proyecto

| Archivo | Proposito |
|---------|-----------|
| `app.py` | Aplicacion principal Flask (rutas, logica) |
| `models.py` | Funciones de acceso a base de datos |
| `config.py` | Constantes y configuracion centralizada |
| `utils.py` | Helpers (timezone, safe_text, file validation) |
| `decorators.py` | @login_required, @admin_required, @professional_required |
| `validators.py` | Validaciones server-side (email, phone, budget, zone) |
| `rate_limit.py` | Rate limiting con headers HTTP |
| `init_db.py` | Inicializacion de schema + indices |

---

## Guia de Instalacion

### Prerrequisitos
- Python 3.10+
- Git
- Navegador web moderno

### 1. Clonar el repositorio
```bash
git clone https://github.com/Arielpirata07/ArchEstate-MASK-.git
cd archestate
```

### 2. Crear entorno virtual
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows
```

### 3. Instalar dependencias
```bash
pip install -r requirements.txt
```

### 4. Configurar variables de entorno
Crear archivo `.env` en la raiz:
```env
SECRET_KEY=tu-clave-secreta-aqui-minimo-32-caracteres
```

### 5. Inicializar la base de datos
```bash
python init_db.py
```

### 6. Iniciar el servidor
```bash
python app.py
```

Acceder a `http://127.0.0.1:5000`

### Usuarios de Prueba
| Rol | Usuario | Contrasena |
|-----|---------|------------|
| Admin | `admin` | `admin123` |
| Profesional | `pro` | `pro123` |

---

## Guia de Despliegue (Produccion)

### 1. Usar Gunicorn como servidor WSGI
```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

### 2. Configurar HTTPS con Nginx
```nginx
server {
    listen 443 ssl;
    server_name archestate.com;

    ssl_certificate /etc/letsencrypt/live/archestate.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/archestate.com/privkey.pem;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /static/ {
        alias /path/to/archestate/static/;
        expires 30d;
    }
}
```

### 3. Variables de entorno para produccion
```env
SECRET_KEY=<generar-con: python -c "import secrets; print(secrets.token_hex(32))">
FLASK_ENV=production
```

### 4. Servicio systemd
```ini
[Unit]
Description=ArchEstate Flask App
After=network.target

[Service]
User=www-data
WorkingDirectory=/var/www/archestate
Environment="PATH=/var/www/archestate/venv/bin"
ExecStart=/var/www/archestate/venv/bin/gunicorn -w 4 -b 127.0.0.1:5000 app:app
Restart=always

[Install]
WantedBy=multi-user.target
```

---

## Endpoints de la API

| Metodo | Endpoint | Descripcion | Auth |
|--------|----------|-------------|------|
| `GET` | `/` | Landing page | Publico |
| `GET` | `/sitemap.xml` | Sitemap XML | Publico |
| `POST` | `/api/submit` | Enviar solicitud de propiedad | Auth |
| `GET` | `/api/leads` | Listar leads (con paginacion) | Profesional |
| `GET` | `/api/leads/filter-options` | Opciones de filtros | Profesional |
| `GET` | `/api/leads/export` | Exportar leads CSV | Profesional |
| `GET` | `/api/leads/export/xlsx` | Exportar leads XLSX | Profesional |
| `GET` | `/api/lead/<id>/phone` | Revelar telefono (auditado) | Profesional |
| `GET` | `/api/lead/<id>/download` | Descargar PDF del lead | Profesional |
| `GET` | `/api/professionals` | Listar profesionales | Admin |
| `POST` | `/api/admin/professional/<id>/status` | Aprobar/rechazar profesional | Admin |
| `GET` | `/api/admin/stats` | Estadisticas del dashboard | Auth |
| `GET` | `/api/admin/users` | Listar usuarios | Admin |
| `POST` | `/api/admin/user/<id>/reset-password` | Reset contrasena | Admin |
| `POST` | `/api/admin/user/<id>/set-active` | Baja/reactivar cuenta | Admin |
| `GET` | `/api/professional/doc-status` | Estado de documentacion | Profesional |
| `POST` | `/api/professional/upload` | Subir documentacion | Profesional |

---

## Capturas de Pantalla

Para agregar capturas al README, incluir las siguientes imagenes en una carpeta `screenshots/`:

| Archivo | Descripcion |
|---------|-------------|
| `landing.png` | Pagina principal con hero, como funciona, testimonios y FAQ |
| `user-form.png` | Formulario de solicitud de propiedad con especificaciones tecnicas |
| `professional-dashboard.png` | Panel profesional con metricas, filtros y tabla de leads |
| `admin-dashboard.png` | Dashboard admin con graficos y KPIs |
| `admin-management.png` | Gestion de profesionales con timeline de auditoria |
| `user-management.png` | Gestion de usuarios con modal de reset de contrasena |

---

## Contribuir

1. Crear una rama desde `main` (`git checkout -b feature/nombre`)
2. Seguir las convenciones del proyecto (indentacion 4 espacios, nombres en snake_case)
3. No agregar nuevos frameworks - usar solo el stack existente
4. Todas las rutas deben tener proteccion server-side
5. Validar inputs tanto en cliente como en servidor
6. Usar `try/finally` para cerrar conexiones de DB
7. Commit con mensajes descriptivos (`git commit -m 'feat: agregar paginacion a leads'`)
8. Abrir Pull Request con descripcion de cambios

### Reglas de Seguridad
- Nunca commitear `database.db` o `.env`
- Usar `secure_filename()` para uploads
- Parametrizar todas las consultas SQL
- Usar `generate_password_hash()` para contrasenas

---

## Changelog

### v2.0 - Mayo 2026
- SEO: Meta tags dinamicos, Open Graph, JSON-LD, sitemap, robots.txt
- Interactividad: Scroll animations, FAQ accordion, testimonios carousel
- Rendimiento: Indices DB, paginacion API, cache de estadisticas
- UI: Metric cards, timeline audit log, hover effects mejorados
- UX: Drag & drop uploads, validacion en tiempo real, toast con progress bar

### v1.0 - MVP Inicial
- Sistema de autenticacion con 3 roles
- Formulario de solicitud de leads
- Dashboard profesional con revelacion de datos
- Panel admin con gestion de profesionales
- Log de auditoria

---

## Licencia

**Licencia:** Propietaria - Todos los derechos reservados

---

## Contacto

Para consultas tecnicas o de negocio, contacta al equipo de desarrollo.

---

<div align="center">

**ArchEstate - Conectando propiedades con profesionales de confianza**

*Built with Flask, Tailwind CSS y mucho cafe*

</div>
