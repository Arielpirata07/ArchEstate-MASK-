# Runbook — ArchEstate

Manual operativo del día a día: correr, desplegar, respaldar, monitorear y recuperar la aplicación. Para usarlo sin adivinar: seguí las secciones en orden según lo que necesites.

> **Complementos:** checklist de deploy completo en `.plans/deploy-checklist.md`. Estado de fixes pendientes en `.plans/fixes-pendientes.md`.

---

## 1. Arranque local (dev)

```bash
# Requisito: SECRET_KEY en .env (config.py lo exige, línea 15-19)
python app.py                  # dev server
FLASK_DEBUG=true python app.py # modo debug
```

### Env vars requeridas
```bash
SECRET_KEY=<largo y secreto>   # Obligatoria
```
Opcionales: `DATABASE_URL`, `SITE_URL`, `TWILIO_*`, `SMTP_*`, `PREFER_SECURE_COOKIES`, `SENTRY_DSN`, `BACKUP_S3_*`. Ver `.plans/deploy-checklist.md`.

## 2. Producción (gunicorn)

```bash
gunicorn wsgi:app --workers 4 --timeout 120 --access-logfile -
```

## 3. Tests

```bash
python -m pytest tests/ -q          # Suite completa (542 tests)
python -m pytest tests/test_file.py # Archivo individual
node --test tests/*.test.js         # Tests JS (phone suggestion)
python verify_coherence.py          # Cross-check schema/rutas/templates (94/94)
```

## 4. Base de datos

- **Default:** SQLite `database.db` en la raíz (`config.py:12`).
- **PostgreSQL:** setear `DATABASE_URL`; el schema se crea/migra automáticamente en `app_setup.init_db()`.
- **Versión de schema:** tabla `schema_version` — las migraciones corren al arrancar.
- **Archivos runtime:** `data/` (rate limits) y `static/uploads/` (avatars, docs).

## 5. Backups

```bash
python scripts/backup_db.py
```

- Genera `database/backups/archestate_<timestamp>.db.gz` (backup online de SQLite, comprimido).
- Conserva los últimos **7** (`_cleanup_old_backups`, `scripts/backup_db.py:84-92`).
- Si está configurado `BACKUP_S3_*`, sube a `s3://<bucket>/db-backups/` (requiere `boto3`).

### Restauración manual
1. Detener la app.
2. Reemplazar `database.db` por el backup: `gunzip -k database/backups/archestate_<timestamp>.db.gz -c > database.db`.
3. Verificar: `python scripts/manage_admin.py info`.
4. Reiniciar la app y chequear `/health`.

## 6. Administración

```bash
python scripts/manage_admin.py info               # Info del admin actual
python scripts/manage_admin.py reset-password     # Genera y setea contraseña nueva
python scripts/manage_admin.py set-password X     # Setea contraseña a X
python scripts/manage_admin.py create-if-missing  # Crea admin si no existe
```

> Opera directo sobre la DB, sin servidor ni `FLASK_DEBUG`. Prioriza `DB_PATH` y luego rutas comunes (`instance/database.db`, `database.db`, `app.db`).

- **Reset de contraseña de un usuario:** panel admin (`/admin`) o el flujo self-service de forgot.
- **Reenvío de OTP:** el flujo de verificación telefónica reenvía el código (limitado por rate limit).

## 7. Operaciones comunes

| Tarea | Cómo |
|---|---|
| Health check | `GET /health` → `{"status": "ok"}` (`factory.py:74`) |
| Limpiar rate limits | Borrar `data/rate_limit_*.json` (y los del `tempdir`: `archestate_rate_limits.json`, `archestate_lead_rate_limits.json`) y reiniciar workers |
| Invalidar caché de filtros | `POST /api/leads/filter-options/invalidate` (con sesión de profesional, `professional_bp.py:664`) |
| Robots/sitemap | `GET /robots.txt`, `GET /sitemap.xml` (blueprint public) |
| Cambiar idioma | `/mi-perfil` → toggle ES/EN (persistido en `user_preferences.language`) |

## 8. Troubleshooting

| Síntoma | Causa probable | Acción |
|---|---|---|
| HTTP 400 al guardar teléfono | Número E.164 inválido (bug conocido de duplicación de área, ver `.plans/fixes-pendientes.md` ítem 1) | Corregir formato; validar con `phonenumbers` |
| HTTP 429 | Rate limit alcanzado (file-backed, por-worker) | Esperar ventana; si es falso positivo en multi-worker, migrar a Redis |
| HTTP 401/redirect a login | Sesión expirada o usuario deshabilitado | Re-login; verificar `is_active` |
| Notificaciones no cargan | Bug `pages<=1` (ya fixeado en v0.31.3) | Actualizar a ≥ v0.31.3 |
| 500 | Error no manejado | Revisar logs (gunicorn) y Sentry (`SENTRY_DSN`) |

### Logs y monitoreo
- Logging estructurado vía `logging`; cada request tiene `request_id` (`middleware.py:49-50`) para correlación.
- Sentry opcional (`factory.py:9-10`).

## 9. CI/CD

- **CI:** `.github/workflows/tests.yml` — corre pytest + node tests en cada push.
- **Dependabot:** `.github/dependabot.yml` — alertas/PRs de dependencias.
- **Deploy:** Render Web Service (ver `.plans/deploy-checklist.md`). Start: `gunicorn wsgi:app --workers 4 --timeout 120 --access-logfile -`.

## 10. Checklist on-call (incidente)

1. `GET /health` — ¿la app responde?
2. Revisar logs de gunicorn + Sentry.
3. ¿Error relacionado con rate limit? → limpiar stores o esperar.
4. ¿DB corrupta/llena? → restaurar último backup válido (`scripts/backup_db.py`).
5. ¿Cambio de esquema? → verificar `schema_version` y reiniciar para correr migraciones.
6. Documentar en `fixes-changelog.md` y actualizar `CHANGELOG.md`.
