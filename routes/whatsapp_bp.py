from flask import Blueprint, request

import config
import models

whatsapp_bp = Blueprint('whatsapp', __name__, url_prefix='')


@whatsapp_bp.route('/api/whatsapp/webhook', methods=['POST'])
def whatsapp_webhook():
    from twilio.request_validator import RequestValidator
    from twilio.twiml.messaging_response import MessagingResponse

    validator = RequestValidator(config.TWILIO_AUTH_TOKEN)
    signature = request.headers.get('X-Twilio-Signature', '')
    params = request.form.to_dict()
    url = request.url

    if config.TWILIO_AUTH_TOKEN and not validator.validate(url, params, signature):
        print(f'[WHATSAPP WEBHOOK] Invalid signature from {request.remote_addr}')
        resp = MessagingResponse()
        return str(resp), 403

    from_number = (params.get('From') or '').strip()
    body = (params.get('Body') or '').strip()

    if not from_number:
        resp = MessagingResponse()
        return str(resp), 200

    if body != 'VERIFICAR':
        resp = MessagingResponse()
        return str(resp), 200

    phone_e164 = from_number.replace('whatsapp:', '', 1).replace(' ', '')
    print(f'[WHATSAPP WEBHOOK] Verify request from {phone_e164}')

    conn = None
    try:
        conn = models.get_db_connection()
        user = conn.execute(
            'SELECT id, username, phone_verified FROM users WHERE phone_e164 = ?',
            (phone_e164,)
        ).fetchone()

        resp = MessagingResponse()
        if user and user['phone_verified'] == 0:
            conn.execute('UPDATE users SET phone_verified = 1 WHERE id = ?', (user['id'],))
            conn.commit()
            msg = f'✅ Teléfono verificado correctamente. Gracias, {user["username"]}.'
            print(f'[WHATSAPP WEBHOOK] Verified user {user["username"]} (id={user["id"]})')
            resp.message(msg)
        elif user and user['phone_verified'] == 1:
            resp.message('✅ Tu teléfono ya estaba verificado.')
        else:
            resp.message('No se encontró un usuario con este número en ArchEstate.')
        return str(resp), 200

    except Exception as e:
        print(f'[WHATSAPP WEBHOOK] Error: {e}')
        resp = MessagingResponse()
        resp.message('Ocurrió un error al verificar tu teléfono. Intentá de nuevo.')
        return str(resp), 200
    finally:
        if conn:
            conn.close()
