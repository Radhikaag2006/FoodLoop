import logging
import smtplib
import threading
from email.message import EmailMessage

from . import config as C

log = logging.getLogger("foodloop")


def _send(to, subject, body):
    try:
        m = EmailMessage()
        m["From"], m["To"], m["Subject"] = C.SMTP_FROM, to, subject
        m.set_content(body)
        with smtplib.SMTP(C.SMTP_HOST, C.SMTP_PORT, timeout=15) as s:
            s.starttls()
            if C.SMTP_USER:
                s.login(C.SMTP_USER, C.SMTP_PASS)
            s.send_message(m)
    except Exception:
        log.exception("email send failed")


def send_mail(to, subject, body) -> bool:
    """Returns True if an email was queued. Without SMTP settings the
    message is only logged (development)."""
    if not C.SMTP_HOST:
        if not C.IS_PROD:
            log.warning("MAIL to=%s subject=%s body=%s", to, subject, body)
        return False
    threading.Thread(target=_send, args=(to, subject, body),
                     daemon=True).start()
    return True
