# Plan: API de Teléfono — Twilio SMS + WhatsApp Real + UX Completo

## Estado: COMPLETADO ✓

## Resultado
- **351 tests pasaron** (0 fallos)
- Twilio SMS real integrado con fallback a simulado
- Twilio WhatsApp real integrado con plantillas Meta (content_sid)
- Badge de verificación muestra canal (SMS/WhatsApp)
- Selector de canal preferido en perfil
- Verificación disponible en user.html
- Admin muestra estado de verificación

## Credenciales Twilio
- Account SID: ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
- Número verificado: +543541388368
- WhatsApp from: +14155238886 (sandbox)
- Content SID: HXb5b62575e6e4ff6129ad7c8efe1f983e

## Archivos modificados
- `requirements.txt` — +twilio>=9.0.0
- `config.py` — +TWILIO_* vars (SMS + WhatsApp)
- `.env` — +credenciales Twilio
- `services/verifier.py` — +TwilioSmsVerifier + TwilioWhatsAppVerifier + router update
- `app_setup.py` — +verification_channel column
- `routes/phone_bp.py` — canal en send/verify + preferred_channel explícito
- `routes/client_bp.py` — phone_verified en query + user al template
- `routes/admin_bp.py` — phone_verified en query
- `models.py` — verification_channel en get_user_profile
- `templates/profile.html` — badge con ícono + selector de canal
- `templates/user.html` — badge + modal OTP + profile.js
- `static/js/profile.js` — auto-send + badge dinámico + savePreferredChannel
- `static/js/usermgmt.js` — badge de verificación en tabla admin
- `tests/test_verifier.py` — tests para TwilioSmsVerifier + TwilioWhatsAppVerifier
- `tests/test_routes_phone.py` — mock de config Twilio para tests

## Objetivo
Integrar Twilio SMS real para verificación de teléfono, mejorar la UI para que muestre qué tecnología se usa, y agregar verificación en user.html y admin.

## Fases

### Fase 1: Config + Twilio
- [x] `requirements.txt` — agregar `twilio>=9.0.0`
- [x] `config.py` — agregar TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_PHONE_NUMBER
- [x] `.env` — agregar credenciales Twilio

### Fase 2: TwilioSmsVerifier
- [x] `services/verifier.py` — nueva clase TwilioSmsVerifier(OTPChannel)
- [x] `services/verifier.py` — actualizar get_default_router() para usar Twilio si hay credenciales

### Fase 3: DB Schema
- [x] `app_setup.py` — agregar columna verification_channel a users

### Fase 4: Backend
- [x] `routes/phone_bp.py` — guardar verification_channel en send_code, leer en verify
- [x] `routes/phone_bp.py` — soportar preferred_channel explícito en body
- [x] `routes/client_bp.py` — seleccionar phone_verified en query, pasar user al template
- [x] `routes/admin_bp.py` — seleccionar phone_verified en query de get_all_users

### Fase 5: Profile — Badge + Selector Canal
- [x] `templates/profile.html` — badge con ícono de canal (SMS/WhatsApp)
- [x] `templates/profile.html` — selector de canal preferido
- [x] `static/js/profile.js` — auto-send OTP al abrir modal
- [x] `static/js/profile.js` — badge dinámico con canal en respuesta
- [x] `static/js/profile.js` — savePreferredChannel()

### Fase 6: user.html — Verificación
- [x] `templates/user.html` — badge + botón verificación
- [x] `templates/user.html` — modal OTP (copiar de profile.html)
- [x] `templates/user.html` — incluir profile.js para funciones de verificación

### Fase 7: Admin — Badge Verificación
- [x] `templates/user_management.html` — (no cambia, es JS-rendered)
- [x] `static/js/usermgmt.js` — badge de verificación en columna teléfono

### Fase 8: Tests
- [x] `tests/test_verifier.py` — tests para TwilioSmsVerifier
- [x] `tests/test_routes_phone.py` — tests de auto-send y canal

### Fase 9: Validación
- [x] Ejecutar `python -m pytest tests/ -q`
- [x] Verificar que no hay tests rotos

## Archivos modificados
- `requirements.txt`
- `config.py`
- `.env`
- `services/verifier.py`
- `app_setup.py`
- `routes/phone_bp.py`
- `routes/client_bp.py`
- `routes/admin_bp.py`
- `templates/profile.html`
- `templates/user.html`
- `static/js/profile.js`
- `static/js/usermgmt.js`
- `tests/test_verifier.py`
- `tests/test_routes_phone.py`
