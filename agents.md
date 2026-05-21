# ArchEstate - Developer & AI Agent Guide

## Quick Start
```bash
python app.py        # Servidor en http://127.0.0.1:5000 (inicializa BD automáticamente)
```
**Test users:** `admin`/`admin123`, `pro`/`pro123`

---

## Tech Stack (no agregar nuevos frameworks sin consenso)
- Python 3.10+ + Flask 3.0
- SQLite 3 con `row_factory = sqlite3.Row`
- Tailwind CSS 3.4 (CDN) + Vanilla JS
- Jinja2 templates + Lucide Icons + Chart.js 4.4 (solo en admin.html)

---

## Arquitectura del Proyecto

Todo el backend vive en `app.py`. Antes de agregar código, verificar si ya existe un endpoint similar.

### Decoradores de protección de rutas
```python
@login_required          # Cualquier usuario autenticado
@admin_required          # Solo role == 'admin'
@professional_required   # Solo role == 'professional'
```

### Conexión a BD (patrón obligatorio)
```python
conn = None
try:
    conn = get_db_connection()
    result = conn.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
    conn.commit()  # Solo si hubo escrituras
finally:
    if conn:
        conn.close()
```

### Respuestas JSON
- Éxito: `jsonify({"status": "success", "message": "..."})` + código 200
- Error: `jsonify({"error": "..."})` + código 400/403/404/413/415

---

## Reglas Críticas de Seguridad

1. **Todas las rutas protegidas server-side** — nunca confiar en el frontend
2. **Queries parametrizadas siempre** — `execute("... WHERE id = ?", (id,))` — nunca f-strings
3. **Passwords**: `generate_password_hash()` y `check_password_hash()` de werkzeug
4. **Archivos**: siempre `secure_filename()` + `os.path.join(app.root_path, ...)` — nunca paths hardcodeados
5. **No se puede operar sobre admins**: ningún endpoint debe permitir que un admin modifique a otro admin (excepto a sí mismo)
6. **`is_active`**: verificar en login — usuarios con `is_active = 0` no pueden autenticarse

---

## Migraciones de BD

El esquema vive en `init_db()` dentro de `app.py`. Cuando se agrega una columna nueva:

```python
# Patrón de migración automática (no rompe BDs existentes)
cursor.execute('PRAGMA table_info(tabla)')
cols = [row[1] for row in cursor.fetchall()]
if 'nueva_columna' not in cols:
    cursor.execute("ALTER TABLE tabla ADD COLUMN nueva_columna TEXT DEFAULT ''")
```

**Nunca usar `DROP TABLE` o `CREATE TABLE` sin `IF NOT EXISTS`.**

---

## Convenciones de Código

### Python
- Logging de acciones sensibles: `log_action("Descripción", f"Target: {nombre}")`
- Timestamps en UTC en la BD, convertir a UTC-3 (Argentina) al mostrar con `convert_to_argentina_time()`
- Validar email server-side con `is_valid_email(email)` (ya definida)
- Nombres de archivos subidos: `user_{session_id}_{secure_filename}`

### JavaScript (Vanilla)
- Toast de feedback: `showToast(message, 'success'|'error'|'info')` — definida en `main.js`
- Revelar teléfono: `togglePhone(btn, leadId)` — definida en `main.js`
- **Nunca usar `alert()` o `confirm()`** — usar modales o toasts
- Iconos Lucide: siempre llamar `lucide.createIcons()` después de insertar HTML con `data-lucide`
- Los `<i data-lucide="...">` se convierten a `<svg>` al inicializar — no intentar mutar el `<i>` después

### Chips / Selectores visuales (patrón establecido)
```javascript
// Siempre reconstruir className desde base — no mutar con replace()
function selectChip(group, value) {
    document.getElementById(hiddenInputId).value = value;
    document.querySelectorAll('.chip-class').forEach(btn => {
        const active = btn.dataset.value === value;
        btn.className = BASE_CLASS + ' ' + (active
            ? 'border-midnight bg-midnight text-white'
            : 'border-midnight/20 text-midnight hover:border-gold');
    });
}
```

### Modales con Lucide
```javascript
// Cuando el modal cambia íconos dinámicamente, reconstruir innerHTML completo
// (querySelector('i') falla porque Lucide ya convirtió los <i> a <svg>)
btn.innerHTML = '<i data-lucide="user-x" class="w-3 h-3"></i><span>Texto</span>';
if (window.lucide) lucide.createIcons();
```

---

## Tabla de professionals — FK a users

La tabla `professionals` tiene `user_id` FK a `users.id`. El JOIN correcto:

```sql
SELECT p.*, u.doc_path, u.id AS user_id, u.is_active
FROM professionals p
LEFT JOIN users u ON (
    (p.user_id IS NOT NULL AND p.user_id = u.id)
    OR
    (p.user_id IS NULL AND p.name = u.username)  -- fallback para datos legacy
)
```

Al registrar un profesional nuevo, guardar `cursor.lastrowid` como `user_id`:
```python
cursor = conn.execute('INSERT INTO users ...', (...))
new_user_id = cursor.lastrowid
conn.execute('INSERT INTO professionals (user_id, ...) VALUES (?, ...)', (new_user_id, ...))
```

---

## is_active — Estado de cuenta

- `1` = activo (default)
- `0` = dado de baja
- `NULL` = campo no migrado aún → tratar como activo en el frontend

En JS, para evaluar correctamente:
```javascript
const isActive = (rawActive === null || rawActive === undefined) ? true : rawActive !== 0;
```

---

## Upload de Documentos

- Endpoint: `POST /api/professional/upload`
- Campo del form: `document`
- Tipos permitidos: PDF, JPG, JPEG, PNG
- Límite: 10 MB (`MAX_UPLOAD_BYTES = 10 * 1024 * 1024`)
- Destino: `static/uploads/docs/user_{id}_{filename}`
- Al subir un nuevo doc, el anterior se elimina del disco automáticamente
- El estado del doc se consulta en: `GET /api/professional/doc-status`

---

## Filtros de Leads — Rangos de Presupuesto

El campo `budget` en la BD es TEXT. Los rangos predefinidos se mapean a valores numéricos en el backend:

```python
BUDGET_RANGES = {
    'hasta_200k':  (0,       200000),
    '200k_500k':   (200000,  500000),
    '500k_1m':     (500000,  1000000),
    '1m_2m':       (1000000, 2000000),
    'mas_2m':      (2000000, None),
}
```

La comparación usa `CAST(REPLACE(REPLACE(budget, '.', ''), ',', '') AS REAL)`.

---

## Coherencia Estado ↔ Antigüedad (user.html)

| Estado seleccionado | Efecto en Antigüedad |
|--------------------|-----------------------|
| A estrenar | Fuerza "Hasta 5 años", bloquea el resto |
| En construcción | Oculta la sección (no aplica) |
| A reciclar | Sugiere "Más de 30 años", sin bloquear |
| Sin preferencia / Usado | Todo habilitado |

---

## Issues Conocidos (no empeorar)

| Issue | Estado |
|-------|--------|
| Sin tests automatizados | Verificar manualmente antes de commit |
| Sin CSRF protection | No agregar formularios públicos sin considerar esto |
| `app.py` monolítico (~1400 líneas) | Crear nuevas rutas en el archivo pero considerar blueprints |
| Tailwind CDN | No apto para producción; configurar PostCSS antes de deploy |
| `budget` como TEXT en BD | No cambiar el tipo sin migración de datos |

---

## Checklist antes de hacer un cambio

- [ ] ¿El endpoint tiene decorador de protección correcto?
- [ ] ¿Todas las queries usan parámetros (`?`)?
- [ ] ¿La conexión a BD se cierra en `finally`?
- [ ] ¿Las columnas nuevas tienen migración automática?
- [ ] ¿El JS no usa `alert()`/`confirm()`?
- [ ] ¿Se llama `lucide.createIcons()` tras insertar HTML con íconos?
- [ ] ¿Los chips reconstruyen `className` completo en vez de usar `replace()`?
- [ ] ¿La acción queda registrada en `audit_log` si es sensible?