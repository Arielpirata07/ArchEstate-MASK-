# WhatsApp Webhook — Botón de verificación con confirmación

## Estado
✅ Código implementado — falta configurar template en Twilio Console y exponer webhook

## Pendiente (usuario)

1. **Crear Content Template en Twilio Console**
   - Ir a: https://console.twilio.com/ > Content > Templates
   - Tipo: WhatsApp
   - Nombre: `archstate_verify`
   - Body: `Hola {{3}}, tu código de verificación de ArchEstate es: {{1}} (válido {{2}} min)`
   - Botón Quick Reply: texto `✅ Verificar` — reply `VERIFICAR`
   - Enviar a aprobación de Meta (puede tardar horas)
   - Una vez aprobado, copiar Content SID (ej: `HX...`)

2. **Configurar SID en `.env`**
   ```bash
   TWILIO_WHATSAPP_BUTTON_CONTENT_SID=HX...
   ```

3. **Configurar webhook URL en Twilio Console**
   - Ir a: https://console.twilio.com/ > WhatsApp > Sandbox
   - "When a message comes in": `https://tudominio.com/api/whatsapp/webhook`
   - Method: `HTTP POST`

4. **Exponer servidor para development (opcional)**
   ```bash
   # Con bore (simple, sin registro)
   cargo install bore-cli
   bore local 5000 --to bore.pub
   # Te da una URL como https://xxxx.bore.pub
   
   # Con serveo (SSH, sin instalar nada)
   ssh -R 80:localhost:5000 serveo.net
   ```

## Funcionamiento

```
Usuario toca "✅ Verificar" en WhatsApp
        │
        ▼
Twilio → POST /api/whatsapp/webhook
        │  Headers: X-Twilio-Signature
        │  Body: From=whatsapp:+5493541388368
        │        Body=VERIFICAR
        ▼
whatsapp_bp.py valida firma con RequestValidator
        │
        ▼
Busca usuario por phone_e164 en users.phone_e164
        │
        ▼
Setea phone_verified = 1
        │
        ▼
Responde TwiML: "✅ Teléfono verificado. Gracias, {username}."
```

## Archivos creados/modificados

| Archivo | Cambio |
|---|---|
| `routes/whatsapp_bp.py` | Nuevo blueprint con webhook |
| `factory.py:45,53` | Import y registro del blueprint |
| `services/verifier.py:160` | `send()` acepta `username` como `{{3}}` |
| `services/verifier.py:207` | `send_otp()` pasa `username` a WhatsApp |
| `services/verifier.py:256` | Usa `BUTTON_CONTENT_SID` si está configurado |
| `routes/phone_bp.py:136` | Pasa `username` a `send_otp()` |
| `config.py:43` | Nueva variable `TWILIO_WHATSAPP_BUTTON_CONTENT_SID` |
| `.env-example:23-28` | Documentación del nuevo template |
| `AGENTS.md` | Blueprint count, routes, phone verification docs |

## Notas

- En localhost el webhook **no funciona** porque Twilio no puede alcanzar la máquina
- El botón en WhatsApp aparece siempre que el template esté aprobado
- Si no hay template aprobado, Twilio cae al template default del Sandbox
- La verificación manual con código OTP de 6 dígitos sigue funcionando en paralelo
