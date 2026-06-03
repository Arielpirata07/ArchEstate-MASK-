# ArchEstate — Agent Guide

## Architecture

- **Flask app** built with Application Factory pattern via `factory.py:create_app()`.
- **8 blueprints** registered: `auth`, `public`, `client`, `professional`, `admin`, `phone`, `lead`, `profile`.
- Entry point: `app.py` (6 lines) — just `from factory import create_app; app = create_app()`.
- Middleware in `middleware.py`, error handlers in `errors.py`, DB init in `app_setup.py`.
- Endpoint naming: blueprint-prefixed (`public.index`, `auth.login`, `professional.professional_view`, etc.).
- Templates use `url_for('public.index')`, `url_for('auth.login')`, etc. — do NOT use bare endpoints.
- DB: raw SQLite via `models.get_db_connection()`. Schema auto-created/migrated on startup via `app_setup.init_db(app)`.

## Key files

| File | Role |
|---|---|
| `factory.py` | Wires app: config + middleware + errors + blueprints |
| `config.py` | Reads `.env`, defines constants |
| `models.py` | `get_db_connection()`, `get_user_by_id()` |
| `app_setup.py` | `init_db(app)`, `FilterOptionsCache`, `get_budget_stats_from_db()` |
| `decorators.py` | `@login_required`, `@admin_required`, `@professional_required` |
| `routes/` | 6 blueprints; `routes_profile.py` also at root |
| `services/` | OTP verifier router (WhatsApp/SMS) |

## Commands

```bash
python app.py                          # Run dev server (reads .env DEBUG)
FLASK_DEBUG=true python app.py         # Dev mode with debug
python -m pytest tests/ -q            # Run all tests (263 total)
python -m pytest tests/ -x -v         # Stop on first failure, verbose
python -m pytest tests/test_file.py   # Single file
```

## Conventions

- **No `alert()`/`confirm()`** — use `showToast()` from `main.js`.
- **No `className.replace()`** on Tailwind classes with `/` — rebuild full string instead.
- **Tailwind custom colors** (`midnight`, `gold`, `paper`, etc.) defined in `static/js/tailwind-config.js` — use class names, never raw hex in templates.
- **Design tokens** in `design.md` — follow button/card/modal patterns from there.
- **Single quotes** for all strings in Python code.

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
| `/mi-perfil` | `profile.profile_view` |
| `/api/phone/send-code` | `phone.send_verification_code` |
| `/api/phone/verify` | `phone.verify_phone_code` |
