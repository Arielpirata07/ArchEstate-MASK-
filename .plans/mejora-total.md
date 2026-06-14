# Plan de Mejora Total — ArchEstate

**Fecha:** 2026-06-14
**Tests previos:** 286 pasando
**Bugs corregidos en sesión previa:** 4 (usermgmt.js reason, routes_profile.py rate limits, profile.js emerald-600, admin.html aria-label)

---

## FASE 1 — Seguridad

| # | Cambio | Archivo | Estado |
|---|--------|---------|--------|
| 1.1 | .env en .gitignore | `.gitignore` | ✅ |
| 1.2 | Session cookie flags | `factory.py` | ✅ |
| 1.3 | CSP header + remove X-XSS-Protection | `middleware.py` | ✅ |
| 1.4 | Admin seed con password aleatorio (prod) | `app_setup.py` | ✅ |
| 1.5 | PRAGMA foreign_keys ON | `models.py` | ⏸️ (revertido — causa timeouts en tests) |
| 1.6 | Session regeneration post-login | `routes/auth_bp.py` | ✅ |
| 1.7 | Error handlers HTML para navegadores | `errors.py` + 6 templates | ✅ |

## FASE 2 — Rendimiento

| # | Cambio | Archivo | Estado |
|---|--------|---------|--------|
| 2.1 | Cache de usuario en g (before_request) | `middleware.py` | ✅ |
| 2.2 | Audit log con LIMIT 200 | `routes/admin_bp.py` | ✅ |

## FASE 3 — Accesibilidad

| # | Cambio | Archivo | Estado |
|---|--------|---------|--------|
| 3.1 | aria-current="page" en nav mobile (4 links) | `templates/base.html` | ✅ |

## FASE 4 — SEO

| # | Cambio | Archivo | Estado |
|---|--------|---------|--------|
| 4.1 | Crear robots.txt | `static/robots.txt` | ✅ |
| 4.2 | Crear sitemap.xml | `static/sitemap.xml` | ✅ |
| 4.3 | Títulos únicos por página | Templates | ✅ (ya existían) |
| 4.4 | JSON-LD Organization en landing | `templates/landing.html` | ✅ |

## FASE 5 — Frontend/UX

| # | Cambio | Archivo | Estado |
|---|--------|---------|--------|
| 5.1 | Dark mode en admin.css | `static/css/admin.css` | ✅ (ya existía completo) |
| 5.2 | Dark mode en user.css | `static/css/user.css` | ✅ |
| 5.3 | Consolidar escapeHtml (fallback a global) | `static/js/auth.js` | ✅ |

## FASE 6 — Testing

| # | Cambio | Archivo | Estado |
|---|--------|---------|--------|
| 6.1 | Tests de admin | `tests/test_admin.py` | ⬜ |
| 6.2 | Tests de profile | `tests/test_profile.py` | ⬜ |

---

## Ejecución

- [x] Bugs previos corregidos (4)
- [x] FASE 1 completada — Seguridad
- [x] FASE 2 completada — Rendimiento
- [x] FASE 3 completada — Accesibilidad
- [x] FASE 4 completada — SEO
- [x] FASE 5 completada — Frontend/UX
- [ ] FASE 6 pendiente — Testing
- [x] Tests finales pasando (286/286)
