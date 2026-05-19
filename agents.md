# ArchEstate - Developer Guide

## Quick Start
```bash
python app.py                # Run server at http://127.0.0.1:5000
python init_db.py           # Initialize SQLite database
```

**Test users:** `admin`/`admin123`, `pro`/`pro123`

## Tech Stack (no agregar nuevos frameworks)
- Python 3.10+ + Flask 3.0
- SQLite 3 with `row_factory = sqlite3.Row`
- Tailwind CSS 3.4 (CDN) + Vanilla JS
- Jinja2 templates + Lucide Icons

## Módulos del Proyecto
| Archivo | Propósito |
|---------|-----------|
| `config.py` | Constantes centralizadas |
| `models.py` | Funciones de DB |
| `utils.py` | Helpers (timezone, safe_text) |
| `decorators.py` | @login_required, @admin_required |
| `validators.py` | Validaciones server-side |
| `rate_limit.py` | Rate limiting |
| `routes_profile.py` | Blueprint de perfil de usuario |
| `verify_coherence.py` | Script de verificación de integridad |

## Critical Rules

### Security
- All routes must be protected server-side with `@login_required` or explicit `if 'user_id' not in session`
- Validate input server-side - never trust frontend
- Use `werkzeug.security.generate_password_hash()` and `check_password_hash()`
- Never hardcode secrets - use `.env` for SECRET_KEY

### File Uploads (mandatory)
- ALWAYS use `secure_filename()` from `werkzeug.utils`
- Use `os.path.join(app.root_path, ...)` for paths - NEVER hardcode `/` or `\`
- Store uploads in `static/uploads/docs/`

### Database
- Always use parameterized queries: `cursor.execute("SELECT * FROM users WHERE id = ?", (id,))`
- Close connections in `finally` block:
  ```python
  try:
      conn = get_db_connection()
      # ... operations
  finally:
      if conn:
          conn.close()
  ```

## Known Issues (avoid making worse)
- No automated tests - verify manually
- No CSRF protection on forms
- `app.py` has ~2,100 lines - create new modules instead of adding more