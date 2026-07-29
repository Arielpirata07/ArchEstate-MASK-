"""
Capa de envío de emails vía SMTP.

Si SMTP_HOST no está configurado, imprime en consola (fallback dev).
"""

import logging
import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

logger = logging.getLogger(__name__)
from typing import Optional

import config


class SMTPEmailSender:
    """Envía emails transaccionales vía SMTP."""

    def __init__(
        self,
        host: str = '',
        port: int = 587,
        user: str = '',
        password: str = '',
        from_addr: str = '',
        use_tls: bool = True,
    ):
        self.host = host or config.SMTP_HOST
        self.port = port or config.SMTP_PORT
        self.user = user or config.SMTP_USER
        self.password = password or config.SMTP_PASS
        self.from_addr = from_addr or config.SMTP_FROM
        self.use_tls = use_tls

    @property
    def is_configured(self) -> bool:
        return bool(self.host and self.from_addr)

    def send(
        self,
        to: str,
        subject: str,
        html_body: str,
        text_body: Optional[str] = None,
    ) -> bool:
        """
        Envía un email HTML. Retorna True si éxito, False si error.
        Si SMTP no está configurado, imprime en consola.
        """
        if not self.is_configured:
            logger.info('[EMAIL SIMULADO] -> %s | Asunto: %s', to, subject)
            return True

        try:
            msg = MIMEMultipart('alternative')
            msg['From'] = self.from_addr
            msg['To'] = to
            msg['Subject'] = subject

            if text_body:
                msg.attach(MIMEText(text_body, 'plain', 'utf-8'))
            msg.attach(MIMEText(html_body, 'html', 'utf-8'))

            context = ssl.create_default_context()
            with smtplib.SMTP(self.host, self.port, timeout=15) as server:
                if self.use_tls:
                    server.starttls(context=context)
                if self.user and self.password:
                    server.login(self.user, self.password)
                server.sendmail(self.from_addr, [to], msg.as_string())

            logger.info('[EMAIL ENVIADO] -> %s | Asunto: %s', to, subject)
            return True

        except Exception:
            logger.exception('Error al enviar email a %s', to)
            return False


_default_sender: Optional[SMTPEmailSender] = None


def get_email_sender() -> SMTPEmailSender:
    """Singleton del email sender."""
    global _default_sender
    if _default_sender is None:
        _default_sender = SMTPEmailSender()
    return _default_sender


def reset_email_sender():
    """Útil para tests."""
    global _default_sender
    _default_sender = None
