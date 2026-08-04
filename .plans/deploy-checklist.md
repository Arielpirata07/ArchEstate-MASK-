# Checklist de Deploy — ArchEstate

> Última actualización: v0.20.5 (i18n completo)

## Estado actual

| Componente | Estado | Notas |
|---|---|---|
| Flask app | ✅ Listo | Application Factory, 10 blueprints |
| SQLite/PostgreSQL | ✅ Listo | SQLite default, PostgreSQL vía `DATABASE_URL` |
| i18n ES/EN | ✅ Completo | 1100+ keys, 40+ archivos |
| Phone verification | ✅ Listo | OTP simulated + Twilio |
| WhatsApp webhook | ✅ Listo | Twilio WhatsApp button template |
| Email (SMTP) | ✅ Listo | Console fallback si no hay SMTP |
| Rate limiting | ⚠️ Pendiente | File-backed (migrar a Redis) |
| Tests | ✅ 444/444 | Todos pasando |

---

## Variables de entorno requeridas

### Obligatorias
```bash
SECRET_KEY=<tu-secret-key-largo>          # Obligatorio para Flask sessions
```

### Opcionales (con valores por defecto)
```bash
# Base de datos
DATABASE_URL=                             # Si no se setea, usa SQLite en disco

# Site
SITE_URL=http://localhost:5000            # URL base para emails y links

# Twilio (phone verification + WhatsApp)
TWILIO_ACCOUNT_SID=
TWILIO_AUTH_TOKEN=
TWILIO_PHONE_NUMBER=                      # Para SMS
TWILIO_WHATSAPP_FROM=                     # Para WhatsApp (formato: whatsapp:+14155238886)
TWILIO_WHATSAPP_CONTENT_SID=              # Template de WhatsApp con botón
TWILIO_WHATSAPP_BUTTON_CONTENT_SID=       # Template con botón "✅ Verificar"
TWILIO_SIMULATE=true                      # true = simulado (dev), false = Twilio real

# SMTP (emails)
SMTP_HOST=
SMTP_PORT=587
SMTP_USER=
SMTP_PASS=
SMTP_FROM=noreply@archestate.com

# Cookies
PREFER_SECURE_COOKIES=true                # En producción con HTTPS
```

---

## Deploy en Render

### Service
- **Type**: Web Service (Python)
- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `gunicorn wsgi:app --workers 4 --timeout 120 --access-logfile -`
- **Environment**: Python 3.11+

### Database
- **Opción 1 (recomendado para empezar)**: SQLite en disco persistente de Render
- **Opción 2 (producción)**: Neon PostgreSQL vía `DATABASE_URL`
  - Crear base en Neon, copiar connection string
  - Setear `DATABASE_URL=postgresql://user:pass@ep-xxx.us-east-2.aws.neon.tech/dbname`
  - El schema se crea/migra automáticamente vía `app_setup.init_db()`

### Env vars en Render
Ir a Dashboard → Service → Environment → Add Environment Variable:
```
SECRET_KEY = (generar con: python -c "import secrets; print(secrets.token_hex(32))")
SITE_URL = https://tu-app.onrender.com
TWILIO_SIMULATE = true
```

### Redis (pendiente)
- Render no tiene Redis built-in como variable
- Opciones: Upstash (free tier), Redis Cloud, o mantener file-backed rate limiting
- Para migrar: reemplazar `rate_limit.py` (JSON + atomic writes) con Redis calls
- `REDIS_URL` se setearía automáticamente si se agrega un Redis add-on

---

## Archivos que se crean en runtime

```
data/                          # Rate limiting (file-backed)
├── rate_limit_*.json          # Bloqueados por gitignore
uploads/avatars/               # Avatares de usuario
uploads/professional_docs/     # Documentos de profesionales
```

---

## After deploy — verificar

1. **Health check**: `GET /health` → `{"status": "ok"}`
2. **Registro**: Crear usuario admin manualmente en DB o vía script
3. **Phone verification**: Con `TWILIO_SIMULATE=true`, los códigos se loguean en consola
4. **WhatsApp webhook**: Configurar URL `https://tu-app.onrender.com/api/whatsapp/webhook` en Twilio Console
5. **SMTP**: Si no se configura, los emails se loguean en consola (console fallback)

---

## Known issues / Pendiente

| Issue | Prioridad | Descripción |
|---|---|---|
| Rate limiting file-backed | Media | Migrar a Redis para multi-worker. Actualmente funciona pero no es perfecto entre workers. |
| `STATIC_URL` para CDN | Baja | Actualmente sirve `/static/` desde Flask. Considerar CDN (CloudFront, etc.) |
| Error templates 409/410/413/429 | Baja | Textos hardcoded en HTML (no usan i18n keys) |
| Email templates HTML | Baja | Solo `lead_assigned.html` tiene `site_url`. Otros emails pueden tener links rotos. |
| SQLite concurrencia | Baja | Para alta concurrencia, migrar a PostgreSQL. SQLite funciona para tráfico bajo. |

---

## Commands post-deploy

```bash
# Verificar que todo carga
curl https://tu-app.onrender.com/health

# Logs en Render
# Dashboard → Service → Logs

# Tests (local)
python -m pytest tests/ -x -q

# Verificar coherencia schema/routes
python verify_coherence.py
```
