"""Transactional email through Google SMTP (use a Gmail App Password).

Emails are sent from FastAPI BackgroundTasks so a slow SMTP server never
blocks an API response. A failure is logged but never breaks the workflow.
"""
import html
import logging
import smtplib
from email.message import EmailMessage

from ..config import get_settings

log = logging.getLogger("emails")


def send_email(to: str, subject: str, heading: str, body_lines: list[str],
               button_text: str | None = None, button_url: str | None = None) -> None:
    s = get_settings()
    if not (s.smtp_user and s.smtp_password):
        log.warning("SMTP not configured; skipping email to %s (%s)", to, subject)
        return

    # html.escape on every dynamic value prevents HTML/script injection in emails
    paragraphs = "".join(f"<p style='margin:0 0 12px'>{html.escape(line)}</p>" for line in body_lines)
    button = ""
    if button_text and button_url:
        button = (f"<p><a href='{html.escape(button_url, quote=True)}' style='background:#4f46e5;color:#fff;"
                  f"padding:10px 18px;border-radius:6px;text-decoration:none'>{html.escape(button_text)}</a></p>")
    html_body = (f"<div style='font-family:Arial,sans-serif;max-width:520px;margin:auto'>"
                 f"<h2 style='color:#4f46e5'>{html.escape(heading)}</h2>{paragraphs}{button}"
                 f"<hr><small>{html.escape(s.smtp_from_name)} - IT 109 academic project (sandbox)</small></div>")

    msg = EmailMessage()
    msg["Subject"] = subject.replace("\n", " ")[:150]
    msg["From"] = f"{s.smtp_from_name} <{s.smtp_user}>"
    msg["To"] = to
    msg.set_content("\n".join(body_lines))
    msg.add_alternative(html_body, subtype="html")

    try:
        with smtplib.SMTP(s.smtp_host, s.smtp_port, timeout=15) as server:
            server.starttls()
            server.login(s.smtp_user, s.smtp_password)
            server.send_message(msg)
    except Exception as exc:  # noqa: BLE001
        log.error("Email to %s failed: %s", to, exc)


def link(path: str) -> str:
    return f"{get_settings().frontend_url.rstrip('/')}{path}"
