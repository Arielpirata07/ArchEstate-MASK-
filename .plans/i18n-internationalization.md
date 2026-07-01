# Plan de Internacionalización (i18n) — ArchEstate

## Arquitectura del Sistema

### Infraestructura existente (NO necesita cambios)
- `user_preferences.language` column (default `'es'`)
- `PUT /api/profile/settings` accept `('es', 'en')`
- Profile UI language selector
- `inject_theme()` context processor (se replica para `inject_language()`)

### Componentes nuevos a crear

---

## Fase 1: Motor de traducción (Core)

### 1.1 — `i18n/translations.py` (nuevo archivo)
Diccionario maestro con todas las traducciones:

```python
TRANSLATIONS = {
    'es': {
        'nav.home': 'Inicio',
        'nav.leads': 'Solicitudes',
        'nav.professional': 'Profesional',
        'nav.admin': 'Admin',
        'nav.profile': 'Mi Perfil',
        'nav.logout': 'Cerrar Sesión',
        'nav.login': 'Iniciar Sesión',
        # ... ~500+ keys
    },
    'en': {
        'nav.home': 'Home',
        'nav.leads': 'Leads',
        'nav.professional': 'Professional',
        'nav.admin': 'Admin',
        'nav.profile': 'My Profile',
        'nav.logout': 'Log Out',
        'nav.login': 'Log In',
        # ... ~500+ keys
    }
}
```

Funciones:
- `t(key, lang='es', **kwargs)` — retorna string traducido con soporte para interpolation `t('greeting', name='Juan')` → `"Hola, Juan"` / `"Hello, Juan"`
- `get_browser_language(request)` — parsea `Accept-Language` header, retorna `'es'` o `'en'`
- `get_language()` — función helper que:
  1. Si hay `user_id` en sesión → lee `user_preferences.language`
  2. Si no → usa `get_browser_language(request)`
  3. Fallback → `'es'`

### 1.2 — `i18n/__init__.py` (nuevo paquete)
Expose las funciones públicas: `t`, `get_language`, `get_browser_language`

### 1.3 — Context processor en `middleware.py`
```python
@app.context_processor
def inject_language():
    return {'lang': get_language(), 't': t}
```

Esto hace disponible `{{ t('key') }}` en TODOS los templates.

### 1.4 — Filter de Jinja2
```python
app.jinja_env.filters['t'] = lambda key, **kwargs: t(key, get_language(), **kwargs)
```

Uso en templates: `{{ 'nav.logout' | t }}` o `{{ t('greeting', name=user.username) }}`

---

## Fase 2: Strings del frontend (Templates)

### Archivos a modificar (11 templates + 1 partial):

| Archivo | Strings estimados | Notas |
|---------|-------------------|-------|
| `base.html` | ~25 | Navbar, footer, flash messages, notificaciones |
| `landing.html` | ~30 | Hero, FAQ, features, JSON-LD |
| `login.html` | ~10 | Form labels, button text |
| `register.html` | ~15 | Form labels, account types |
| `user.html` | ~50 | Lead form: all labels, placeholders, sections |
| `professional.html` | ~40 | Dashboard: tabs, KPIs, table headers, stats |
| `admin.html` | ~50 | Dashboard: tabs, stats, sections |
| `user_management.html` | ~20 | User table, modals |
| `lead_detail.html` | ~25 | Lead detail labels |
| `edit_lead.html` | ~30 | Edit form labels |
| `profile.html` | ~60 | All tabs: account, appearance, notifications, security, etc. |
| `partials/contact_buttons.html` | ~5 | Button labels, aria-labels |
| `errors/*.html` (11) | ~3 each | Error titles and messages |

**Total estimado: ~400+ keys de traducción**

### Estrategia de migración
Reemplazar en cada template:
- `Texto hardcodeado` → `{{ 'key.path' | t }}`
- `Texto con variables` → `{{ t('key', variable=value) }}`
- `<html lang="es-AR">` → `<html lang="{{ lang }}">`
- JSON-LD `"inLanguage": "es-AR"` → `"inLanguage": "{{ lang }}"` (con fallback a `'es-AR'`/`'en-US'`)

---

## Fase 3: Strings del backend (Python)

### 3.1 — Flash messages (`flash()`)
Archivos a modificar:

| Archivo | Flash messages estimados |
|---------|------------------------|
| `routes/auth_bp.py` | ~12 (login, register, logout errors) |
| `routes/client_bp.py` | ~5 (lead submission success/error) |
| `routes/professional_bp.py` | ~8 (upload, report, status) |
| `routes/admin_bp.py` | ~15 (professional status, user management) |
| `routes/phone_bp.py` | ~6 (verification codes) |
| `routes/form_options_bp.py` | ~4 (CRUD options) |
| `routes_profile.py` | ~10 (profile updates, password, avatar) |

**Total: ~60 flash messages**

Estrategia: usar `flash(t('key.flash.login_success', lang=get_language()))` o wrapper:
```python
def flash_t(key, **kwargs):
    flash(t(key, get_language(), **kwargs))
```

### 3.2 — Validators (`validators.py`)
Retornar tuplas `(is_valid, translated_message)` o usar key de error:
```python
return False, t('error.password_too_short', lang=lang)
```

### 3.3 — Error handlers (`errors.py`)
Mensajes JSON y HTML de errores 400/403/404/429/500.

### 3.4 — API responses
Todos los `jsonify({'error': '...'}), jsonify({'message': '...'})` en routes.

### 3.5 — Email subjects + bodies
`services/notifications.py` — 4 funciones con subjects hardcodeados:
- `notify_lead_created()` → subject
- `notify_lead_status_change()` → subject
- `notify_professional_status_change()` → subject
- `notify_report_deleted()` → subject

`templates/email/*.html` — 5 templates con contenido hardcodeado.

**Solución**: pasar `lang` del professional/user al contexto de renderizado de emails, usar `t()` en los templates de email.

### 3.6 — Export labels (CSV/XLSX/PDF)
Headers de columnas en CSV y XLSX exports, labels en PDF.

---

## Fase 4: Strings del frontend (JavaScript)

### 4.1 — `static/js/i18n.js` (nuevo archivo)
Objeto global con traducciones JS:

```javascript
window.I18N = {
    es: {
        'toast.error_network': 'Error de conexión',
        'toast.success': 'Operación exitosa',
        'confirm.cancel': 'Cancelar',
        'confirm.accept': 'Confirmar',
        // ... ~80 keys
    },
    en: {
        'toast.error_network': 'Network error',
        'toast.success': 'Operation successful',
        'confirm.cancel': 'Cancel',
        'confirm.accept': 'Confirm',
        // ... ~80 keys
    }
};

window.__LANG = document.documentElement.lang || 'es';
window.t = function(key, params) {
    var dict = window.I18N[window.__LANG] || window.I18N.es;
    var val = dict[key] || key;
    if (params) Object.keys(params).forEach(function(k) {
        val = val.replace('{' + k + '}', params[k]);
    });
    return val;
};
```

### 4.2 — Inyectar `lang` en `<html>` desde `base.html`
```html
<html lang="{{ lang }}">
```
Esto permite que JS lea `document.documentElement.lang`.

### 4.3 — Archivos JS a modificar (8):

| Archivo | Strings estimados |
|---------|-------------------|
| `main.js` | ~15 (toast, confirm, validation) |
| `profile.js` | ~10 (success/error messages) |
| `professional.js` | ~8 (error messages, stats labels) |
| `admin.js` | ~20 (form options CRUD, toasts) |
| `user.js` | ~5 (phone saved, validation) |
| `usermgmt.js` | ~5 (error messages) |
| `landing.js` | ~5 (typing text) |
| `edit_lead.js` | ~3 (validation) |

**Total: ~70 keys JS**

### 4.4 — Cambios en `showToast()`, `showConfirm()`
```javascript
// Antes
showToast('Error de conexión', 'error');
// Después
showToast(t('toast.error_network'), 'error');
```

---

## Fase 5: Lógica de detección de idioma

### 5.1 — En `middleware.py` o `get_language()`:
```python
def get_language():
    if session.get('user_id'):
        prefs = models.get_user_preferences(session['user_id'])
        return prefs.get('language', 'es')
    return get_browser_language(request)
```

### 5.2 — En `auth_bp.py` (login):
Al hacer login, guardar `language` en sesión:
```python
prefs = models.get_user_preferences(user['id'])
session['language'] = prefs.get('language', 'es')
```

### 5.3 — En `GET/PUT /api/profile/settings`:
Al actualizar language, también actualizar `session['language']`.

---

## Fase 6: Archivos de traducción organizados

### Estructura propuesta:
```
archestate/
├── i18n/
│   ├── __init__.py          # Expose t(), get_language()
│   ├── translations.py      # Dict maestro es/en (~500 keys)
│   └── browser.py           # get_browser_language()
├── static/js/
│   └── i18n.js              # Dict JS es/en (~80 keys)
└── ...existing structure...
```

### Categorías de keys:
```
nav.*          — Navbar (home, leads, professional, admin, profile, login, logout)
hero.*         — Landing hero section
faq.*          — FAQ questions/answers
features.*     — Feature cards
auth.*         — Login/register forms
lead.*         — Lead form (client)
professional.* — Professional dashboard
admin.*        — Admin dashboard
profile.*      — Profile tabs and settings
error.*        — Error pages (400-504)
flash.*        — Flash messages
toast.*        — Toast notifications
confirm.*      — Confirmation dialogs
email.*        — Email subjects and body text
export.*       — CSV/XLSX/PDF headers
validator.*    — Validation error messages
```

---

## Fase 7: Testing

### 7.1 — Tests unitarios del motor i18n
- `test_t_returns_es_by_default()`
- `test_t_returns_en_when_lang_en()`
- `test_t_interpolates_variables()`
- `test_get_browser_language_returns_es()`
- `test_get_browser_language_returns_en()`
- `test_get_language_uses_session_when_logged_in()`
- `test_get_language_falls_back_to_browser()`

### 7.2 — Tests de integración
- `test_profile_settings_updates_language()`
- `test_flash_messages_are_translated()`
- `test_templates_render_in_english()`

### 7.3 — Tests existentes
Verificar que los 420 tests actuales siguen pasando con el sistema i18n.

---

## Orden de ejecución recomendado

| Paso | Fase | Dependencias | Tiempo est. |
|------|------|-------------|-------------|
| 1 | Fase 1: Motor i18n core | Ninguna | 1-2h |
| 2 | Fase 5: Detección de idioma | Fase 1 | 30min |
| 3 | Fase 4.1-4.2: i18n.js + lang in HTML | Fase 1 | 30min |
| 4 | Fase 2: Templates (empezar por base.html, luego los demás) | Fase 1+2 | 3-4h |
| 5 | Fase 4.3-4.4: JS strings | Fase 4.1 | 1-2h |
| 6 | Fase 3.1-3.2: Flash messages + validators | Fase 1 | 1-2h |
| 7 | Fase 3.3-3.6: Errores, API, emails, exports | Fase 1 | 2-3h |
| 8 | Fase 6: Tests i18n | Fase 1 | 1h |
| 9 | Fase 7: Tests existentes | Todo | 30min |

**Tiempo total estimado: 10-14 horas de desarrollo**
