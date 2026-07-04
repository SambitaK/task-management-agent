"""
tasks/email_task.py

EMAIL TASK — composes and sends real emails via Gmail's SMTP server.

Uses Python's built-in smtplib — no extra package needed beyond what's
already in the standard library.
"""

import os
import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

load_dotenv()

GMAIL_ADDRESS = os.environ.get("GMAIL_ADDRESS")
GMAIL_APP_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD")

SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587


def send_email(to_address: str, subject: str, body: str) -> str:
    """Composes and sends a real email via Gmail SMTP.

    Args:
        to_address: The recipient's email address.
        subject: The email subject line.
        body: The plain-text body content of the email.

    Returns:
        A JSON string describing whether the email was sent successfully.
    """
    if not GMAIL_ADDRESS or not GMAIL_APP_PASSWORD:
        return json.dumps({
            "error": "GMAIL_ADDRESS or GMAIL_APP_PASSWORD is not configured in .env"
        })

    try:
        msg = MIMEMultipart()
        msg["From"] = GMAIL_ADDRESS
        msg["To"] = to_address
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))

        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=15) as server:
            server.starttls()
            server.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
            server.sendmail(GMAIL_ADDRESS, to_address, msg.as_string())

        return json.dumps({
            "success": True,
            "action": "email_sent",
            "to": to_address,
            "subject": subject
        })

    except smtplib.SMTPAuthenticationError:
        return json.dumps({
            "error": "Gmail authentication failed. Check GMAIL_ADDRESS and GMAIL_APP_PASSWORD."
        })
    except Exception as e:
        return json.dumps({"error": f"Failed to send email: {str(e)}"})