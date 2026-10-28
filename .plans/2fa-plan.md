# Plan — Verificación en dos pasos (2FA) para ArchEstate

> Estado: **borrador — sin implementar**. Plan técnico para agregar 2FA a cuentas existentes.
> Base: commit `7120975` (post-revisión). Rama: `main`.

## 1. Objetivo

Agregar autenticación de segundo factor (2FA) a las cuentas de ArchEstate, de forma
opcional por usuario, con soporte para apps autenticadoras (TOTP, RFC 6238) y
códigos de recuperación, reutilizando la infraestructura existente (Twilio SMS/WhatsApp)
como canal alternativo. Debe convivir con remember-me, email verification y el
flujo de reset de contraseña sin romper la sesión actual.

## 2. Alcance y decisiones

| Decisión | Propuesta | Alternativa descartada |
|---|---|---|
| Factor primario | TOTP (Google Authenticator / Authy / 1Password) | SMS-only (depende de Twilio y es menos seguro) |
| Canal alterno | SMS/WhatsApp vía `services/verifier.py` ya existente | — |
| Obligatoriedad | **Opcional** por usuario (toggle en `/mi-perfil`); admin puede forzar 2FA para rol `admin` | Obligatorio para todos (fricción alta en onboarding) |
| Recuperación | 10 códigos de un solo uso generados al activar | Email mágico (menos seguro) |
| Sesión | 2FA se verifica **una vez por sesión**; remember-me no salta el 2FA en dispositivos nuevos | Recordar dispositivo por 30 días (más complejo, diferido) |
| Alcance de roles | `admin`, `professional`, `client` (todos) | Solo admin (insuficiente) |

## 3. Modelo de datos

Nueva tabla `user_two_factor` (1:1 con `users`):

```sql
CREATE TABLE user_two_factor (
    user_id            INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    enabled            INTEGER NOT NULL DEFAULT 0,        -- 0/1
    method             TEXT NOT NULL DEFAULT 'totp',       -- 'totp' | 'sms' | 'whatsapp'
    totp_secret        TEXT,                              -- base32, cifrado at-rest (ver §7)
    phone_e164         TEXT,                              -- canal alterno verificado
    created_at         DATETIME DEFAULT CURRENT_TIMESTAMP,
    enabled_at         DATETIME,
    last_used_at       DATETIME,
    failed_attempts    INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE user_recovery_codes (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id   INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    code_hash TEXT NOT NULL,          -- sha256 del código (nunca en claro)
    used      INTEGER NOT NULL DEFAULT 0,
    used_at   DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_recovery_codes_user ON user_recovery_codes(user_id);
```

Migración: nueva versión en `db_migrations.py` (v9), idempotente (`CREATE TABLE IF NOT EXISTS`),
con backfill `enabled=0` para todos los usuarios existentes. Registrar versión solo si ambas
tablas se crean (patrón v8).

## 4. Dependencias

- `pyotp` (TOTP/HOTP, RFC 6238) — agregar a `requirements.txt` y `requirements-dev.txt`.
- `qrcode[pil]` para generar el QR de enrolamiento (PNG en memoria, servido como data-URI o
  guardado en `static/uploads/2fa/`); alternativa: generar el URI `otpauth://` y renderizar con
  librería JS (`qrcode.js`) para evitar dependencia server-side. **Recomendado: JS** (menos peso).
- Reutilizar `services/verifier.py` para el canal SMS/WhatsApp.

## 5. Flujo de enrolamiento (activación)

1. Usuario entra a `/mi-perfil` → sección "Seguridad" → "Activar 2FA".
2. `POST /api/profile/2fa/setup`:
   - Genera `totp_secret` (base32, 20 bytes) con `pyotp.random_base32()`.
   - Guarda fila `user_two_factor` con `enabled=0` y el secret.
   - Devuelve `{ otpauth_uri, qr_data, secret }` (secret solo para entrada manual).
3. Frontend muestra QR + secret + input de confirmación.
4. Usuario escanea y escribe el código de 6 dígitos.
5. `POST /api/profile/2fa/confirm` con `{ code }`:
   - Valida TOTP contra el secret (ventana ±1 período).
   - Si OK: `enabled=1`, `enabled_at=now`, genera 10 recovery codes (mostrar **una sola vez**),
     hashea y guarda. Revoca remember-me tokens (forzar re-login con 2FA).
   - Si falla: 400 `2fa.invalid_code`.
6. Mostrar recovery codes con botón "Copié los códigos" (no se vuelven a mostrar).

## 6. Flujo de login con 2FA

En `auth_bp.login()`, tras validar contraseña y `is_active`:

- Consultar `user_two_factor.enabled` para el usuario.
- Si `enabled=0`: flujo actual (sin cambios).
- Si `enabled=1`:
  - **No** crear sesión completa todavía. Guardar en `session` un estado intermedio
    `session['2fa_pending_user_id'] = user.id` (sin `user_id`/`role`).
  - Redirigir a `/2fa/verify` (nueva ruta `auth_bp.two_factor_verify`).
- En `/2fa/verify` (GET): renderiza template con input de 6 dígitos + link "Usar código de recuperación"
  + opción "Enviar por SMS/WhatsApp" (si `method != 'totp'` o canal configurado).
- `POST /api/auth/2fa/verify` con `{ code }`:
  - Rate limit 5/min (reutilizar `rate_limit.check_rate_limit`).
  - Valida TOTP o recovery code (marcar `used=1` si recovery).
  - Brute-force: tras 5 fallos, invalidar el pending y forzar re-login con password.
  - Si OK: completar sesión (`user_id`, `username`, `email`, `role`, `phone`), limpiar
    `2fa_pending_user_id`, insertar `user_login_history`, emitir remember cookie si se pidió,
    redirigir por rol. Actualizar `last_used_at`.
  - Si recovery code: mostrar aviso "Te quedan N códigos".
- `POST /api/auth/2fa/resend` (solo canal SMS/WhatsApp): envía OTP vía `VerifierRouter`.

Middleware (`middleware.py`): si existe `2fa_pending_user_id` en sesión y el request no es a
`/2fa/verify` ni a assets, redirigir a `/2fa/verify` (evita bypass).

## 7. Seguridad

- **Secrets at-rest**: cifrar `totp_secret` con una clave derivada de `SECRET_KEY` (Fernet o AES-GCM)
  en una nueva utilidad `utils.encrypt_2fa_secret` / `decrypt`. Si no hay clave dedicada, derivar
  con PBKDF2-HMAC-SHA256. Documentar `TWO_FACTOR_ENCRYPTION_KEY` (opcional) en `.env-example`.
- **Recovery codes**: generar con `secrets.token_hex(4)` formateado `XXXX-XXXX` (8 hex = 32 bits),
  hashear con SHA-256 antes de guardar; mostrar en claro una sola vez.
- **Brute-force**: `failed_attempts` en `user_two_factor`; lockout a 5 intentos → deshabilitar
  pending y notificar al usuario por email (`notify_2fa_lockout`).
- **Revocación**: cambiar/resetear contraseña debe **no** deshabilitar 2FA, pero debe revocar
  remember tokens (ya existe `revoke_user_remember_tokens`). Deshabilitar 2FA requiere código
  válido (o recovery code) + contraseña actual.
- **Admin forzado**: si `user.role == 'admin'` y 2FA deshabilitado, mostrar banner en `/admin`
  obligando a activarlo; opcionalmente bloquear acciones mutantes hasta activar.
- **Audit log**: registrar `2fa_enabled`, `2fa_disabled`, `2fa_verified`, `2fa_failed`,
  `2fa_recovery_used` en `audit_log` (reutilizar `utils.log_action`).
- **Rate limit**: 5/min verify, 3/min setup, 10/min resend.

## 8. Desactivación y gestión

- `DELETE /api/profile/2fa` (requiere contraseña actual + código 2FA o recovery):
  - `enabled=0`, borrar secret y recovery codes.
- `POST /api/profile/2fa/regenerate-recovery`: genera 10 nuevos códigos (invalida los anteriores),
  requiere código 2FA válido.
- `PUT /api/profile/2fa/method`: cambiar método (totp/sms/whatsapp) con verificación previa.
- UI en `/mi-perfil` sección "Seguridad": estado, método, fecha de activación, botones
  activar/desactivar/regenerar códigos, contador de códigos restantes.

## 9. i18n

Nuevas keys (ES/EN, en `i18n/translations.py` y `static/js/i18n.js`):

```
auth.2fa_title, auth.2fa_subtitle, auth.2fa_code_label, auth.2fa_verify,
auth.2fa_invalid, auth.2fa_locked, auth.2fa_use_recovery, auth.2fa_resend_sms,
profile.2fa_section, profile.2fa_status_enabled/disabled, profile.2fa_activate,
profile.2fa_deactivate, profile.2fa_scan_qr, profile.2fa_manual_secret,
profile.2fa_confirm_code, profile.2fa_recovery_title, profile.2fa_recovery_warning,
profile.2fa_recovery_remaining, profile.2fa_regenerate, error.2fa_required
```

## 10. Frontend

- Template nuevo `templates/two_factor_verify.html` (input 6 dígitos, mismo estilo que OTP).
- Sección en `templates/profile.html` para gestión.
- JS en `static/js/profile.js` (enrolamiento, gestión) y `static/js/auth.js` (verify).
- Reutilizar componentes: `showToast`, modales, `escapeHtml`.

## 11. Tests

Nuevos archivos:
- `tests/test_two_factor.py`:
  - setup/confirm con código válido e inválido
  - login con 2FA redirige a `/2fa/verify`
  - verify con TOTP válido completa sesión; inválido no
  - recovery code de un solo uso (segundo uso falla)
  - brute-force lockout a 5 intentos
  - desactivación requiere código
  - regeneración invalida códigos anteriores
  - admin con 2FA deshabilitado → banner
  - middleware bloquea bypass a `/usuario` con pending
- Extensiones a `tests/test_auth_bp.py` (si existe) y `tests/test_profile.py`.

Objetivo de cobertura: ≥ 25 tests nuevos, suite total ≥ 930.

## 12. Migración y compatibilidad

- Usuarios existentes: `enabled=0` (opt-in), sin cambios de comportamiento.
- `email_verified` y `phone_verified` no se tocan.
- Remember-me tokens emitidos antes de activar 2FA siguen válidos hasta expirar; al activar
  se revocan (ver §6).
- Si un usuario pierde el autenticador y los recovery codes: flujo de soporte manual por
  admin (`admin_bp` endpoint `POST /api/admin/user/<id>/disable-2fa` con audit log).

## 13. Riesgos y mitigaciones

| Riesgo | Mitigación |
|---|---|
| Secret TOTP en claro en DB | Cifrado at-rest con clave derivada (§7) |
| Replay de código TOTP | `last_used_at` + rechazo de códigos ya usados en la misma ventana |
| Phishing del QR | Mostrar secret solo en enrolamiento; no permitir re-display |
| Usuario bloqueado | Recovery codes + desactivación por admin auditada |
| Clock skew | Ventana ±1 período (30 s) en validación |
| Tests frágiles por tiempo | Usar `freezegun` + secret fijo en tests |

## 14. Hitos sugeridos

1. **M1 — Schema + modelos** (v9 migration, `models/two_factor.py`, helpers de cifrado). Sin UI.
2. **M2 — Enrolamiento + gestión** (endpoints + UI en `/mi-perfil` + i18n). Tests de setup.
3. **M3 — Login con 2FA** (flujo pending, middleware, verify, SMS fallback). Tests de login.
4. **M4 — Recovery codes + desactivación + admin override**. Tests de edge cases.
5. **M5 — Hardening** (cifrado, brute-force, audit, documentación, README/RUNBOOK).

Cada hito debe dejar la suite verde (≥ 905) y `verify_coherence.py` 96/96.

## 15. Archivos a tocar (estimación)

| Archivo | Cambio |
|---|---|
| `db_migrations.py` | +v9 (tablas 2FA + recovery) |
| `models/users.py` o nuevo `models/two_factor.py` | CRUD 2FA |
| `utils.py` | cifrado de secret, helpers TOTP |
| `routes/auth_bp.py` | login con pending, `/2fa/verify`, endpoints verify/resend |
| `middleware.py` | guard de pending 2FA |
| `routes/profile/` (nuevo `two_factor.py` o en `core.py`) | setup/confirm/disable/regenerate/method |
| `routes/admin_bp.py` | disable-2fa por admin |
| `templates/two_factor_verify.html` | nuevo |
| `templates/profile.html` | sección seguridad |
| `static/js/profile.js`, `static/js/auth.js` | UI |
| `i18n/translations.py`, `static/js/i18n.js` | keys nuevas |
| `requirements.txt` | pyotp, qrcode (si server-side) |
| `tests/test_two_factor.py` | nuevo |
| `README.md`, `RUNBOOK.md`, `AGENTS.md`, `CHANGELOG.md` | documentación |

## 16. Fuera de alcance (futuro)

- WebAuthn / llaves de seguridad (FIDO2).
- Recordar dispositivo por 30 días (device trust).
- 2FA obligatorio global por política de la org.
- Backup de secret en password manager (export cifrado).

---

*Plan generado como borrador. No implementar sin revisión del usuario.*