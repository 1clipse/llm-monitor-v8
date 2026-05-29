import os
import smtplib
from email.message import EmailMessage

import httpx


async def notify_if_configured(event: dict) -> None:
    webhook_url = os.getenv("ALERT_WEBHOOK_URL")
    if webhook_url:
        async with httpx.AsyncClient(timeout=10) as client:
            await client.post(webhook_url, json=event)

    smtp_host = os.getenv("ALERT_SMTP_HOST")
    smtp_to = os.getenv("ALERT_EMAIL_TO")
    if smtp_host and smtp_to:
        message = EmailMessage()
        message["Subject"] = f"LLM Monitor alert: {event.get('analysis', {}).get('risk_label', 'UNKNOWN')}"
        message["From"] = os.getenv("ALERT_EMAIL_FROM", "llm-monitor@localhost")
        message["To"] = smtp_to
        message.set_content(str(event))
        with smtplib.SMTP(smtp_host, int(os.getenv("ALERT_SMTP_PORT", "25"))) as smtp:
            smtp.send_message(message)
