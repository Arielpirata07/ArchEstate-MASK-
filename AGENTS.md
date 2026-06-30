# ArchEstate — Agent Guide

## Architecture

- **Flask app** built with Application Factory pattern via `factory.py:create_app()`.
- **10 blueprints** registered: `auth`, `public`, `client`, `professional`, `admin`, `phone`, `lead`, `form_options`, `whatsapp`, `profile` (9 in `routes/` + `profile` in `routes_profile.py`).
- Entry point: `app.py` (6 lines) — just `from factory import create_app; app = create_app()`.
- Middleware in `middleware.py`, error handlers in `errors.py`, DB init in `app_setup.py`.
- Endpoint naming: blueprint-prefixed (`public.index`, `auth.login`, `professional.professional_view`, etc.).
- Templates use `url_for('public.index')`, `url_for('auth.login')`, etc. — do NOT use bare endpoints.
- DB: raw SQLite via `models.get_db_connection()` (PostgreSQL via `services.database` when `DATABASE_URL` is set). Schema auto-created/migrated on startup via `app_setup.init_db(app)`. Schema versioning via `schema_version` table.
- All decorators (`@login_required`, `@admin_required`, `@professional_required`) check `is_active` — disabled users get session cleared and redirected.
- Error handlers: 400, 403, 404, 409, 410, 413, 429, 500, 502, 503, 504 (all with HTML + JSON fallback).
- Structured logging via `logging` module (no `print()` in except blocks). Config in `factory.py`.

## Key files

| File | Role |
|---|---|
| `factory.py` | Wires app: config + middleware + errors + blueprints + `/health` endpoint |
| `config.py` | Reads `.env`, defines constants; `DATABASE_URL`, `SITE_URL`, Twilio config, SMTP config |
| `models.py` | `get_db_connection()` (SQLite/PostgreSQL via `services.database`), `DatabaseError`, `get_user_by_id()`, `update_user_credentials()`, `update_user_profile()`, `FORM_OPTION_CATEGORIES`, `ALLOWED_PROFILE_FIELDS` |
| `services/database.py` | DB abstraction layer: `DBConnection`, `_DBCursor`, `CompatRow`, `get_db_connection()`, `table_columns()`, `date_format_sql()`, `now_sql()`, `is_integrity_error()` |
| `app_setup.py` | `init_db(app)`, `FilterOptionsCache`, schema migrations, `schema_version` table |
| `decorators.py` | `@login_required`, `@admin_required`, `@professional_required` — all enforce `is_active` |
| `rate_limit.py` | File-backed rate limiting (JSON + atomic writes). Pendiente migrar a Redis. |
| `routes_profile.py` | Profile, lead editing, avatar upload (at root, not in `routes/`), `ALLOWED_LEAD_EDIT_FIELDS` |
| `routes/` | 9 blueprints: `auth_bp`, `public_bp`, `client_bp`, `professional_bp`, `admin_bp`, `phone_bp`, `lead_bp`, `form_options_bp`, `whatsapp_bp` |
| `services/verifier.py` | OTP verification layer: `SmsSimulatedVerifier`, `WhatsAppSimulatedVerifier`, `TwilioSmsVerifier`, `TwilioWhatsAppVerifier`, `VerifierRouter`, `get_default_router()` |
| `services/email.py` | `SMTPEmailSender` — SMTP email sender with console fallback |
| `services/notifications.py` | `notify_lead_created()`, `notify_lead_status_change()`, `notify_professional_status_change()`, `notify_report_deleted()` — reads `user_preferences` toggles |
| `wsgi.py` | Gunicorn entry point: `gunicorn wsgi:app` |
| `render.yaml` | Render deployment blueprint |

## Commands

```bash
python app.py                          # Run dev server
FLASK_DEBUG=true python app.py         # Dev mode with debug
gunicorn wsgi:app                      # Run with gunicorn (production)
python -m pytest tests/ -q            # Run all tests (392 total)
python -m pytest tests/ -x -v         # Stop on first failure, verbose
python -m pytest tests/test_file.py   # Single file
python verify_coherence.py            # Cross-checks schema/routes/templates
```

## Deploy (Render)

- **Service type**: Web Service (Python)
- **Build**: `pip install -r requirements.txt`
- **Start**: `gunicorn wsgi:app --workers 4 --timeout 120 --access-logfile -`
- **Database**: SQLite por defecto (disco persistente de Render). Listo para migrar a Neon PostgreSQL vía `DATABASE_URL`.
- **Redis**: Pendiente migrar rate limiting de archivos a Redis (Render KV).
- **Env vars**: `SECRET_KEY` (requerido), `DATABASE_URL`, `REDIS_URL`, `SITE_URL`, `TWILIO_*`, `SMTP_*`, `PREFER_SECURE_COOKIES=true`

## Conventions

- **No `alert()`/`confirm()`** — use `showToast()` from `main.js`.
- **No `className.replace()`** on Tailwind classes with `/` — rebuild full string instead.
- **Tailwind custom colors** (`midnight`, `gold`, `paper`, etc.) defined in `static/js/tailwind-config.js` — use class names, never raw hex in templates.
- **Design tokens** in `design.md` — follow button/card/modal patterns from there.
- **Tabla hierarchy**: `<th>` siempre `font-extrabold text-[11px] text-gold px-4 py-4` con `<tr>` thead `table-header-border`. `<td>` siempre `text-[13px] text-midnight/50`. Los headers deben dominar visualmente a los datos.
- **Single quotes** for all strings in Python code.
- **SQL allowlist** for profile updates: `ALLOWED_PROFILE_FIELDS` in `models.py`, `ALLOWED_LEAD_EDIT_FIELDS` in `routes_profile.py`.
- **Auto-completar email en formulario de solicitud (`/usuario`)**: el email del usuario autenticado (sin importar su rol) debe auto-completarse del registro en DB. Prioridad en template: `user.email` (DB) → `session.get('email')`. El servidor (`client_bp.py:submit_lead`) siempre usa `session.get('email')` ignorando `data.get('email')`. Si no hay email en DB ni en sesión, el campo queda editable. Para cambiar el email, el usuario debe ir a `/mi-perfil`.

## Test notes

- `conftest.py` sets `config.DATABASE` to a temp file, resets rate limits per test.
- Use `auth_client` fixture for authenticated requests.
- `freezegun` is a dependency — tests use `monkeypatch` extensively.

## Routes (common)

| Path | Blueprint endpoint |
|---|---|
| `/` | `public.index` |
| `/login` | `auth.login` |
| `/register` | `auth.register` |
| `/usuario` | `client.user_view` |
| `/profesional` | `professional.professional_view` |
| `/admin` | `admin.admin_view` |
| `/admin/usuarios` | `admin.user_management_view` |
| `/mi-perfil` | `profile.profile_view` |
| `/api/phone/send-code` | `phone.send_verification_code` |
| `/api/phone/verify` | `phone.verify_phone_code` |
| `/api/admin/user/<id>/set-active` | `admin.admin_set_user_active` |
| `/api/admin/user/<id>/reset-password` | `admin.admin_reset_password` |
| `/api/whatsapp/webhook` | `whatsapp.whatsapp_webhook` |
| `/health` | `factory.health` |
| `/robots.txt` | `public.robots` |
| `/sitemap.xml` | `public.sitemap` |

## Phone Verification Architecture

- **Verifier abstraction** (`services/verifier.py`): `OTPChannel` ABC with `SmsSimulatedVerifier`, `WhatsAppSimulatedVerifier`, `TwilioSmsVerifier`, `TwilioWhatsAppVerifier`.
- **Router** (`VerifierRouter`): routes `sms`/`whatsapp` channels to correct provider.
- **Config** (`config.py`): `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_PHONE_NUMBER`, `TWILIO_WHATSAPP_FROM`, `TWILIO_WHATSAPP_CONTENT_SID`, `TWILIO_WHATSAPP_BUTTON_CONTENT_SID`, `TWILIO_SIMULATE`.
- **`TWILIO_SIMULATE` flag**: when `true`, forces simulated verifiers even if Twilio credentials are set (avoids trial rate limits).
- **WhatsApp button template** (`TWILIO_WHATSAPP_BUTTON_CONTENT_SID`): template con botón "✅ Verificar" que al tocarlo envía un POST al webhook con `Body=VERIFICAR`.
- **Webhook** (`routes/whatsapp_bp.py`): `POST /api/whatsapp/webhook` — valida firma de Twilio, recibe el mensaje, busca usuario por `phone_e164` y setea `phone_verified=1`.
- **DB**: `users.phone_verified` (0/1), `users.verification_channel` ('sms'/'whatsapp'/''), `consent_log` records OTP sends.
- **API endpoints**: `POST /api/phone/send-code`, `POST /api/phone/verify`, `POST /api/user/update-phone`, `POST /api/whatsapp/webhook`.
- **UX**: Auto-sends OTP on modal open; channel selector in profile; verification badges show channel icon (smartphone/message-circle).

## Notification System (V3 Avanzado)

- **Email notifications** (`services/notifications.py:notify_lead_created()`): when a new lead is created, `notify_lead_created` sends email to all approved+active professionals who have `lead_alerts=1`. Filters by `province`/`zone` from `professionals` table, plus `notification_filters` JSON from `user_preferences` (operation type & property type matching).
- **In-app notifications**: `notifications` table stores per-user notification records. Created automatically inside `notify_lead_created()` via `_create_notification()`. Badge with unread count in navbar (via `inject_notifications` context processor in `middleware.py`). Dropdown panel with load/mark-read/mark-all-read.
- **Email templates**: all in `templates/email/`. `lead_assigned.html` receives `site_url` from config for absolute CTA links.
- **Notification filter configuration**: professionals can set preferred operation types and property types in `/mi-perfil` (Panel Notificaciones > Filtros de notificaciones). Empty = receive all. Saves via `PUT /api/profile/notification-filters` → stored as JSON in `user_preferences.notification_filters`.
- **DB schema**: `notifications` table (auto-created in `app_setup.py`): `id`, `user_id`, `lead_id`, `type`, `title`, `body`, `is_read`, `created_at`. `user_preferences.notification_filters` column added via migration.
- **API endpoints** (all in `routes_profile.py`):
  - `GET /api/profile/notifications` → list (20 newest)
  - `POST /api/profile/notifications/read` → mark single as read
  - `POST /api/profile/notifications/read-all` → mark all as read
  - `GET /api/profile/notification-filters` → get professional's filters
  - `PUT /api/profile/notification-filters` → save professional's filters (body: `{types: [...], property_types: [...]}`)
