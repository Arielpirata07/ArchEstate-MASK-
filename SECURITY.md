# Seguridad — ArchEstate

Referencia central de los controles de seguridad implementados en el proyecto. Sirve para auditorías, onboarding, pruebas de penetración y cumplimiento.

> **Fuente profunda:** detalles de arquitectura en `.contexto-proyecto.md` (sección "Seguridad"). Esta guía referencia código real con `archivo:línea`; si un control no aparece aquí, no está implementado.

---

## 1. Propósito y alcance

ArchEstate es una aplicación Flask con SQLite (default) o PostgreSQL vía `DATABASE_URL`. Expone APIs web + webhook de WhatsApp (Twilio) y envía emails vía SMTP.

**Superficie de ataque:** autenticación y sesiones, APIs de leads/profesionales/admin, verificación OTP (SMS/WhatsApp), upload de archivos, webhook de Twilio, exportaciones PDF/XLSX, y la capa de notificaciones.

---

## 2. Autenticación y sesiones

- **Hashing de contraseñas:** `werkzeug.security.generate_password_hash` / `check_password_hash` (PBKDF2). Uso: `routes/auth_bp.py:7,89,127,299`; `routes_profile.py:12,196,206`.
- **Sesiones:** cookie de sesión de Flask con `SECRET_KEY` (requerido en `config.py:15-19`). `SESSION_TIMEOUT = 3600` (`config.py:28`).
- **Remember me (30 días):** token con selector + validador firmado, cookie `remember_token`. Restauración en `middleware.py:62-106`; validador revocado si el usuario está inactivo. `PERMANENT_SESSION_LIFETIME` alineado con `REMEMBER_TOKEN_DAYS` (`config.py:32-39`).
- **Usuarios deshabilitados:** `login_required`/`admin_required`/`professional_required` limpian la sesión y redirigen al login si `is_active` es falso (`decorators.py:26-29,40-43,57-60`).
- **Recuperación de contraseña:** flujo self-service forgot/reset con token (`routes/auth_bp.py`, rate limited a 20/min en línea 246).

## 3. Autorización por roles

- Decoradores `@login_required`, `@admin_required`, `@professional_required` (`decorators.py`). Verifican sesión, `is_active` y rol.
- Usuario en caché por request vía `g.user` (`middleware.py:53-59`) — sin re-query en cada decorador.
- Acceso a `/usuario` bloqueado para profesionales (`routes/client_bp.py:30-32`).

## 4. CSRF

- Protección con **Flask-WTF** (introducida en v0.22.0). Inputs `csrf_token` en los formularios.
- **Ojo:** la suite de tests corre con `WTF_CSRF_ENABLED=False` (ver `tests/conftest.py`) — los tests no validan CSRF.

## 5. Inyección SQL

- Consultas **parametrizadas** (`?` placeholders) a lo largo de `models.py` y los blueprints.
- Allowlists para actualizaciones dinámicas: `ALLOWED_PROFILE_FIELDS` (`models.py`) y `ALLOWED_LEAD_EDIT_FIELDS` (`routes_profile.py`). Solo se construyen `SET` con columnas de la allowlist.
- **Riesgo remanente:** cualquier construcción dinámica de nombres de columna/filtro debe validarse contra una allowlist antes de concatenarse.

## 6. XSS y CSP

- Escape en templates Jinja (autoescaping) + filtro `safe_text()` (`utils.py:105`) para datos libres.
- Escape en JS: helper `escapeHtml` en los scripts dinámicos (templates).
- **CSP** por entorno en `middleware.py:26-44` (script-src limita a `'self'` + CDNs específicas; `frame-ancestors 'none'`).

## 7. Headers HTTP

`middleware.py:16-46` (excepto `/static/`):

| Header | Valor |
|---|---|
| `X-Content-Type-Options` | `nosniff` |
| `X-Frame-Options` | `DENY` |
| `Strict-Transport-Security` | `max-age=31536000; includeSubDomains` |
| `Referrer-Policy` | `strict-origin-when-cross-origin` |
| `Permissions-Policy` | `camera=(), microphone=(), geolocation=()` |
| `Content-Security-Policy` | dev vs prod (ver `middleware.py`) |

Headers de rate limit (`X-RateLimit-*`) agregados en `rate_limit.add_rate_limit_headers`.

## 8. Rate limiting

Respaldado en archivos JSON con escritura atómica (`rate_limit.py:2-21`, store en `tempfile`).

**⚠️ Limitación conocida:** con `gunicorn --workers N` el lock es por-worker — el límite efectivo se multiplica por N y puede haber carreras. **Pendiente migrar a Redis.**

Límites por endpoint (ejemplos verificados):

| Endpoint | Límite | Fuente |
|---|---|---|
| Login / Register / Forgot | 100/min | `routes/auth_bp.py:20,115,224` |
| Reset password | 20/min | `routes/auth_bp.py:246` |
| Phone send-code / verify | 100/min | `routes/phone_bp.py:24,71,169` |
| Perfil (mayoría) | 100/min | `routes_profile.py` |
| Perfil (acciones sensibles) | 30/min | `routes_profile.py:261` |
| Admin | 100/min; 30/min (acciones sensibles) | `routes/admin_bp.py:118,...;834` |
| WhatsApp share / reveal | límites por hora (por user y por IP) | `routes/lead_bp.py:53-84,166` |

## 9. Verificación telefónica (OTP)

- **Parámetros:** TTL 10 min, máx. 5 intentos (`config.py:41-42`, `OTP_TTL_MINUTES`/`OTP_MAX_ATTEMPTS`).
- **Abstracción de canales:** `services/verifier.py` — simulado (dev) o Twilio SMS/WhatsApp.
- **`TWILIO_SIMULATE=true`** fuerza verificadores simulados aunque haya credenciales (evita consumir el plan trial de Twilio).
- **Registro de consentimiento:** `consent_log` registra envíos de OTP (`routes/phone_bp.py:137`).
- **Webhook WhatsApp:** `POST /api/whatsapp/webhook` valida la firma de Twilio antes de marcar `phone_verified` (`routes/whatsapp_bp.py`).

## 10. Cookies

- `REMEMBER_COOKIE_SECURE` controlada por `PREFER_SECURE_COOKIES=true` en producción (`config.py:34`).
- Uso de flags Secure/HttpOnly en cookies de sesión según entorno.

## 11. Uploads

- Extensiones permitidas: `ALLOWED_EXTENSIONS` (`config.py:24`).
- Tamaño máximo: `MAX_UPLOAD_SIZE = 16 MB` (`config.py:26`).
- Validación MIME en uploads de profesionales → 415 (`routes/professional_bp.py:1146`).

## 12. Datos personales (PII) y logs

- `users.phone_verified` y `consent_log` trackean consentimiento y verificación.
- Logging estructurado con `logging` — **prohibido `print()` en bloques `except`** (convención del proyecto).
- `request_id` por request (`middleware.py:49-50`) para correlacionar logs sin PII innecesaria.

## 13. Dependencias y monitoreo

- **Dependabot** activo para alertas de dependencias (`.github/dependabot.yml`).
- **Sentry** opcional vía `SENTRY_DSN` (`config.py:59`, init en `factory.py:9-10`).
- CI en `.github/workflows/tests.yml` corre la suite en cada push.

## 14. Limitaciones conocidas

| # | Limitación | Prioridad |
|---|---|---|
| 1 | Rate limiting por-worker (gunicorn) — migrar a Redis | Alta |
| 2 | CSP usa `'unsafe-inline'` en `script-src` (JS inline) — requiere refactor a nonces/hash para endurecer | Media |
| 3 | Validación de teléfonos depende de datos de `phonenumbers` (rangos de algunos países pueden marcar inválidos) | Baja |
| 4 | Flask dev server no recomendado en producción (usar gunicorn) | Media |

## 15. Contacto para reportes de seguridad

Reportar vulnerabilidades creando un issue privado en el repositorio o contactando al mantenedor directamente. No exponer datos sensibles en issues públicos.
