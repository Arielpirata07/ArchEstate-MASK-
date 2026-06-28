# Phone Access Audit — Historial de Acceso a Teléfonos

**User Story (V3 Avanzado):** Como administrador, quiero ver un historial de qué profesional accedió a qué número de teléfono, para auditar el uso de la plataforma y evitar abusos de privacidad.

## Implementation

### Backend: `routes/admin_bp.py`

**New endpoint:** `GET /api/admin/phone-audit`

Filters:
- `profesional` — username filter (exact match)
- `evento` — event type filter (`phone_revealed`, `wa_link_generated`)
- `desde` — start date (YYYY-MM-DD)
- `hasta` — end date (YYYY-MM-DD)
- `page` — page number (default 1)
- `per_page` — items per page (default 25, max 100)

Query joins `events` → `users` → `professionals` → `leads`, returning professional name, lead info, phone number, event type, and timestamp. Only tracks `phone_revealed` and `wa_link_generated` events (successful reveals only).

Returns `{ success, data: [...], total, page, per_page }`.

### Frontend: `templates/admin.html`

New card **"Historial de Acceso a Teléfonos"** in the Dashboard tab, below the Telemetría panel:
- Filter bar: professional select (populated from `/api/professionals`), event type select, date range inputs
- Table: Profesional | Lead | Teléfono | Evento | Fecha
- Pagination: prev/next buttons with page indicator + total count badge
- Empty state with `phone-off` icon
- Uses same design tokens as existing admin: `bg-paper-dark` header, `text-gold` headers, `table-header-border`, stagger animations

### Frontend: `static/js/admin.js`

New functions:
- `initPhoneAudit()` — fetches professional list, populates select, loads page 1
- `loadPhoneAudit()` — reads filter values, resets to page 1, fetches data
- `loadPhoneAuditPage(page)` — changes page with same filters
- `clearPhoneAuditFilters()` — resets all filters and reloads
- `_fetchPhoneAudit()` — shared fetch with loading/empty/data states
- `renderPhoneAudit(data)` — renders rows + pagination
- `renderPhoneAuditRow(entry)` — single row HTML with event badge (emerald for revealed, gold for WhatsApp)
- `updatePaPagination(total, page, perPage)` — pagination controls

Auto-initializes on DOMContentLoaded with a 100ms delay (after telemetry loads).

### Tests: `tests/test_admin_form_options.py`

Class `TestPhoneAudit` with 8 tests:
- `test_phone_audit_empty` — no data returns empty list
- `test_phone_audit_returns_events` — both event types returned
- `test_phone_audit_filter_by_profesional` — filter by username
- `test_phone_audit_filter_by_evento` — filter by event type
- `test_phone_audit_pagination` — page/per_page behavior
- `test_phone_audit_forbidden_client` — non-admin gets 302 redirect
- `test_phone_audit_invalid_dates` — bad date format returns 400
- `test_phone_audit_invalid_pagination` — invalid page returns 400; negative per_page clamped to default

Uses `phone_audit_data` fixture to create a professional + lead + 2 events, and `_clean_events` autouse fixture to isolate tests.

### Files Changed

| File | Change |
|---|---|
| `routes/admin_bp.py` | New endpoint `GET /api/admin/phone-audit` (~70 lines) |
| `templates/admin.html` | New card section in Dashboard tab (~90 lines) |
| `static/js/admin.js` | ~130 new lines (init, fetch, render, pagination, event handlers) |
| `tests/test_admin_form_options.py` | 8 new tests (~120 lines) |

### Design Decisions

- **Events tracked:** Only `phone_revealed` (actual phone number revealed) and `wa_link_generated` (WhatsApp link generated). Excludes intent events like `tel_clicked` and `phone_button_clicked` — the audit focuses on successful accesses, not intents.
- **Leads table columns:** uses `l.type` (operation type) and `l.zone` (neighborhood) for lead info since `leads` has no `name` or `address` columns.
- **Dark mode:** fully compatible — all classes (`bg-white`, `text-gold`, `text-midnight/N`, `shadow-xl`, `table-header-border`, status colors) already have dark mode overrides in `base.css` and `admin.css`.
- **Test isolation:** `DELETE FROM events` runs before each test via autouse fixture to prevent cross-test data leakage.
