"""Envoi du digest par SMTP (multipart texte + HTML)."""
import os
import smtplib
from email.message import EmailMessage
from email.utils import formatdate, make_msgid


def _env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(
            f"Variable d'environnement requise absente ou vide : {name}"
        )
    return value


def _send(config: dict, subject: str, text: str, html: str) -> None:
    sender = _env("EMAIL_SENDER")
    receiver = _env("EMAIL_RECEIVER")
    password = _env("EMAIL_PASSWORD")

    transport_cfg = config.get("transport", {})
    host = transport_cfg.get("smtp_host", "smtp.gmail.com")
    port = int(transport_cfg.get("smtp_port", 465))
    sender_domain = sender.split("@")[-1] if "@" in sender else "gmail.com"

    # Assainit le HTML : retire tout caractère de contrôle (dont \x00) qui
    # ferait échouer la sérialisation multipart de la stdlib.
    html = "".join(ch for ch in html if ch == "\n" or ch == "\t" or ord(ch) >= 32)
    text = "".join(ch for ch in text if ch == "\n" or ch == "\t" or ord(ch) >= 32)

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = receiver
    msg["Date"] = formatdate(localtime=True)
    msg["Message-ID"] = make_msgid(domain=sender_domain)

    msg.set_content(text)
    msg.add_alternative(html, subtype="html")

    with smtplib.SMTP_SSL(host, port) as smtp:
        smtp.login(sender, password)
        smtp.send_message(msg)


def send_digest(config: dict, html_body: str) -> None:
    """Envoie le digest normal."""
    from datetime import datetime

    prefix = config.get("output", {}).get("subject_prefix", "📚 Veille")
    date_str = datetime.now().strftime("%d/%m/%Y")
    subject = f"{prefix} — {date_str}"

    text = (
        "Une nouvelle sélection est disponible. "
        "Ouvrez ce mail sur un client compatible HTML."
    )
    _send(config, subject, text, html_body)


def send_empty(config: dict, reason: str) -> None:
    """Envoie le mail 'aucune nouveauté'."""
    from datetime import datetime

    prefix = config.get("output", {}).get("subject_prefix", "📭 Veille")
    date_str = datetime.now().strftime("%d/%m/%Y")
    subject = f"{prefix} — {date_str} (aucune nouveauté)"

    text = f"Aucune nouveauté pertinente sur la période ({reason})."
    html = (
        '<div style="font-family:Arial,sans-serif; font-size:14px; '
        f'color:#1f2937;">Aucune nouveauté retenue ({reason}).</div>'
    )
    _send(config, subject, text, html)
