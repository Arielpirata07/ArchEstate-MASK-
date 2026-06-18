# ArchEstate — Agent Guide

## Architecture

- **Flask app** built with Application Factory pattern via `factory.py:create_app()`.
- **9 blueprints** registered: `auth`, `public`, `client`, `professional`, `admin`, `phone`, `lead`, `form_options`, `profile` (8 in `routes/` + `profile` in `routes_profile.py`).
- Entry point: `app.py` (6 lines) — just `from factory import create_app; app = create_app()`.
- Middleware in `middleware.py`, error handlers in `errors.py`, DB init in `app_setup.py`.
- Endpoint naming: blueprint-prefixed (`public.index`, `auth.login`, `professional.professional_view`, etc.).
- Templates use `url_for('public.index')`, `url_for('auth.login')`, etc. — do NOT use bare endpoints.
- DB: raw SQLite via `models.get_db_connection()`. Schema auto-created/migrated on startup via `app_setup.init_db(app)`.
- All decorators (`@login_required`, `@admin_required`, `@professional_required`) check `is_active` — disabled users get session cleared and redirected.

## Key files

| File | Role |
|---|---|
| `factory.py` | Wires app: config + middleware + errors + blueprints |
| `config.py` | Reads `.env`, defines constants |
| `models.py` | `get_db_connection()`, `get_user_by_id()`, `update_user_credentials()`, `update_user_profile()`, `FORM_OPTION_CATEGORIES`, `ALLOWED_PROFILE_FIELDS` |
| `app_setup.py` | `init_db(app)`, `FilterOptionsCache`, schema migrations (ALTER TABLE) |
| `decorators.py` | `@login_required`, `@admin_required`, `@professional_required` — all enforce `is_active` |
| `rate_limit.py` | File-backed rate limiting (JSON + atomic writes) |
| `routes_profile.py` | Profile, lead editing, avatar upload (at root, not in `routes/`), `ALLOWED_LEAD_EDIT_FIELDS` |
| `routes/` | 8 blueprints: `auth_bp`, `public_bp`, `client_bp`, `professional_bp`, `admin_bp`, `phone_bp`, `lead_bp`, `form_options_bp` |
| `services/` | OTP verifier router (WhatsApp/SMS) |

## Commands

```bash
python app.py                          # Run dev server (reads .env DEBUG)
FLASK_DEBUG=true python app.py         # Dev mode with debug
python -m pytest tests/ -q            # Run all tests (302 total)
python -m pytest tests/ -x -v         # Stop on first failure, verbose
python -m pytest tests/test_file.py   # Single file
python verify_coherence.py            # Cross-checks schema/routes/templates
```

## Conventions

- **No `alert()`/`confirm()`** — use `showToast()` from `main.js`.
- **No `className.replace()`** on Tailwind classes with `/` — rebuild full string instead.
- **Tailwind custom colors** (`midnight`, `gold`, `paper`, etc.) defined in `static/js/tailwind-config.js` — use class names, never raw hex in templates.
- **Design tokens** in `design.md` — follow button/card/modal patterns from there.
- **Single quotes** for all strings in Python code.
- **SQL allowlist** for profile updates: `ALLOWED_PROFILE_FIELDS` in `models.py`, `ALLOWED_LEAD_EDIT_FIELDS` in `routes_profile.py`.

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
