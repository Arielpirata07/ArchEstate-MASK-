"""
Servicio de notificaciones por email y SMS.

Lee las preferencias del usuario (email_notifications, sms_notifications,
lead_alerts) y envía notificaciones cuando los toggles están activados.
"""

from typing import Optional

import models
import utils
from services.email import get_email_sender
from services.verifier import get_default_router

try:
    from flask import render_template
except ImportError:
    render_template = None


def _send_email_notification(user_id: int, subject: str, html_body: str, text_body: str = '') -> bool:
    """Envía email si el usuario tiene email_notifications activado."""
    prefs = models.get_user_preferences(user_id)
    if not prefs.get('email_notifications'):
        return False

    user = models.get_user_by_id(user_id)
    if not user or not user.get('email'):
        return False

    sender = get_email_sender()
    return sender.send(user['email'], subject, html_body, text_body)


def _send_sms_notification(user_id: int, message: str) -> bool:
    """Envía SMS si el usuario tiene sms_notifications activado."""
    prefs = models.get_user_preferences(user_id)
    if not prefs.get('sms_notifications'):
        return False

    user = models.get_user_by_id(user_id)
    if not user or not user.get('phone'):
        return False

    router = get_default_router()
    phone_e164 = user.get('phone_e164') or user['phone']
    result = router.send_otp(phone_e164, message[:6], preferred_channel='sms', ttl_minutes=5)
    return result.ok


def _render_email(template_name: str, **kwargs) -> tuple:
    """Renderiza template de email. Retorna (html, text)."""
    if render_template:
        try:
            html = render_template(f'email/{template_name}.html', **kwargs)
            return html, ''
        except Exception:
            pass

    html = f"""
    <html>
    <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <h2 style="color: #735A3A;">ArchEstate</h2>
        {''.join(f'<p><b>{k}:</b> {v}</p>' for k, v in kwargs.items())}
        <hr style="border: 1px solid #735A3A;">
        <p style="font-size: 12px; color: #666;">Este es un correo automático de ArchEstate.</p>
    </body>
    </html>
    """
    return html, ''


def _lead_to_dict(lead) -> dict:
    """Convierte un lead row de SQLite a un diccionario limpio."""
    if not lead:
        return {}
    d = dict(lead)
    # Limpiar valores None y 0 para no mostrar campos vacíos
    return {k: v for k, v in d.items() if v is not None and v != '' and v != 0}


def notify_lead_created(lead_id: int) -> None:
    """
    Notifica a profesionales cuando se crea un lead nuevo.
    Filtra por provincia y zona de cobertura del profesional.
    Si el profesional no tiene provincia/zona configurada, recibe todos los leads.
    """
    conn = None
    try:
        conn = models.get_db_connection()
        lead = conn.execute('SELECT * FROM leads WHERE id = ?', (lead_id,)).fetchone()
        if not lead:
            return

        lead_province = (lead['province'] or '').strip()
        lead_zone = (lead['zone'] or '').strip()

        professionals = conn.execute('''
            SELECT u.id, u.email, u.phone, u.phone_e164, p.name, p.specialty, p.province, p.zone
            FROM professionals p
            JOIN users u ON p.user_id = u.id
            WHERE p.status = 'approved' AND u.is_active = 1
        ''').fetchall()
    finally:
        if conn:
            conn.close()

    lead_data = _lead_to_dict(lead)

    for pro in professionals:
        prefs = models.get_user_preferences(pro['id'])
        if not prefs.get('lead_alerts'):
            continue

        pro_province = (pro['province'] or '').strip()
        pro_zone = (pro['zone'] or '').strip()

        if pro_province and lead_province and pro_province != lead_province:
            continue
        if pro_zone and lead_zone and pro_zone.lower() not in lead_zone.lower():
            continue

        subject = f'Nuevo lead disponible: {lead["type"]} en {lead["zone"]}'
        html, _ = _render_email('lead_assigned',
            lead_type=lead['type'],
            zone=lead['zone'],
            budget=lead['budget'],
            currency=lead['currency'],
            property_type=lead['property_type'],
            professional_name=pro['name'],
            province=lead_data.get('province', ''),
            bedrooms=lead_data.get('bedrooms', 0),
            bathrooms=lead_data.get('bathrooms', 0),
            ambientes=lead_data.get('ambientes', 0),
            total_area=lead_data.get('total_area', 0),
            usable_m2=lead_data.get('usable_m2', 0),
            land_area=lead_data.get('land_area', 0),
            built_area=lead_data.get('built_area', 0),
            parking=lead_data.get('parking', ''),
            orientation=lead_data.get('orientation', ''),
            property_condition=lead_data.get('property_condition', ''),
            property_age=lead_data.get('property_age', ''),
            architectural_style=lead_data.get('architectural_style', ''),
            elevator=lead_data.get('elevator', ''),
            pool=lead_data.get('pool', ''),
            community_pool=lead_data.get('community_pool', ''),
            floor_block=lead_data.get('floor_block', ''),
            amenities=lead_data.get('amenities', ''),
            additional_features=lead_data.get('additional_features', ''),
        )
        _send_email_notification(pro['id'], subject, html)

        utils.log_action(
            'Notificación lead asignado',
            f'Lead #{lead_id} -> {pro["name"]}',
            None
        )


def notify_lead_status_change(lead_id: int, professional_id: int, new_status: str) -> None:
    """
    Notifica al admin cuando un profesional cambia el estado de un lead.
    """
    user = models.get_user_by_id(professional_id)
    if not user:
        return

    # Obtener datos del lead para enriquecer la notificación
    lead_data = {}
    conn = None
    try:
        conn = models.get_db_connection()
        lead = conn.execute('SELECT * FROM leads WHERE id = ?', (lead_id,)).fetchone()
        if lead:
            lead_data = _lead_to_dict(lead)
    finally:
        if conn:
            conn.close()

    status_label = 'visto' if new_status == 'seen' else 'contactado'
    subject = f'Lead #{lead_id} marcado como {status_label} por {user.get("username", "profesional")}'

    admin_users = _get_admin_users()
    for admin in admin_users:
        html, _ = _render_email('status_change',
            lead_id=lead_id,
            professional_name=user.get('username', 'N/A'),
            new_status=status_label,
            lead_type=lead_data.get('type', ''),
            lead_zone=lead_data.get('zone', ''),
            lead_budget=lead_data.get('budget', ''),
            lead_currency=lead_data.get('currency', ''),
            lead_property_type=lead_data.get('property_type', ''),
            lead_timestamp=lead_data.get('timestamp', ''),
        )
        _send_email_notification(admin['id'], subject, html)

    utils.log_action(
        'Notificación cambio estado lead',
        f'Lead #{lead_id} -> {status_label} por user #{professional_id}',
        None
    )


def notify_professional_status_change(pro_id: int, new_status: str) -> None:
    """
    Notifica al profesional cuando su cuenta es aprobada o rechazada.
    """
    conn = None
    try:
        conn = models.get_db_connection()
        pro = conn.execute('''
            SELECT p.name, p.user_id, p.specialty, u.email
            FROM professionals p
            JOIN users u ON p.user_id = u.id
            WHERE p.id = ?
        ''', (pro_id,)).fetchone()
    finally:
        if conn:
            conn.close()

    if not pro or not pro['user_id']:
        return

    pro_dict = dict(pro)
    status_label = 'aprobada' if new_status == 'approved' else 'rechazada'
    subject = f'Tu cuenta ha sido {status_label}'

    html, _ = _render_email('professional_status',
        professional_name=pro_dict['name'],
        status=new_status,
        status_label=status_label,
        specialty=pro_dict.get('specialty', ''),
    )
    _send_email_notification(pro_dict['user_id'], subject, html)

    prefs = models.get_user_preferences(pro_dict['user_id'])
    if prefs.get('sms_notifications') and pro_dict.get('email'):
        _send_sms_notification(pro_dict['user_id'], f'ArchEstate: Tu cuenta ha sido {status_label}.')

    utils.log_action(
        'Notificación estado profesional',
        f'{pro["name"]} -> {status_label}',
        None
    )


def notify_report_deleted(lead_id: int, reported_by_user_id: int) -> None:
    """
    Notifica al profesional que reportó un lead cuando admin lo elimina.
    """
    user = models.get_user_by_id(reported_by_user_id)
    if not user:
        return

    # Obtener datos del lead y del reporte
    lead_data = {}
    report_reason = ''
    conn = None
    try:
        conn = models.get_db_connection()
        lead = conn.execute('SELECT * FROM leads WHERE id = ?', (lead_id,)).fetchone()
        if lead:
            lead_data = _lead_to_dict(lead)

        report = conn.execute(
            'SELECT reason FROM lead_reports WHERE lead_id = ? AND reported_by = ? ORDER BY id DESC LIMIT 1',
            (lead_id, reported_by_user_id)
        ).fetchone()
        if report:
            report_reason = report['reason'] or ''
    finally:
        if conn:
            conn.close()

    subject = f'Lead #{lead_id} eliminado tras tu reporte'
    html, _ = _render_email('report_deleted',
        lead_id=lead_id,
        professional_name=user.get('username', 'N/A'),
        lead_type=lead_data.get('type', ''),
        lead_zone=lead_data.get('zone', ''),
        lead_property_type=lead_data.get('property_type', ''),
        report_reason=report_reason,
    )
    _send_email_notification(reported_by_user_id, subject, html)

    utils.log_action(
        'Notificación lead eliminado',
        f'Lead #{lead_id} eliminado, notificado a user #{reported_by_user_id}',
        None
    )


def _get_admin_users() -> list:
    """Retorna lista de usuarios admin activos."""
    conn = None
    try:
        conn = models.get_db_connection()
        admins = conn.execute(
            'SELECT id, email FROM users WHERE role = ? AND is_active = 1',
            ('admin',)
        ).fetchall()
        return [dict(a) for a in admins]
    finally:
        if conn:
            conn.close()
