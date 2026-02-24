"""
Generic email opt-out handler.
Used by any broker with method='email' in registry.json.
Requires SMTP_USER and SMTP_PASS in .env to automate.
Without SMTP, returns manual_required with the opt-out email address.
"""
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from brokers.handlers.base import BaseHandler
from config import SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS, SMTP_CONFIGURED


class Handler(BaseHandler):
    def submit(self) -> dict:
        opt_out_email = self.broker.get("email_address")
        if not opt_out_email:
            return {"status": "error", "notes": "No opt-out email configured for this broker."}

        if not SMTP_CONFIGURED:
            return {
                "status": "manual_required",
                "notes": (
                    f"Send opt-out email to {opt_out_email}. "
                    "Configure SMTP_USER and SMTP_PASS in .env to automate this."
                ),
            }

        subject = self.broker.get("email_subject", f"Opt-Out Request — {self.full_name}")
        template = self.broker.get("email_template", self._default_template())
        body = template.format(
            full_name=self.full_name,
            email=self.email,
            phone=self.phone,
            address=self.address,
            city=self.city,
            state=self.state,
            zip=self.zip_code,
            dob=self.dob,
        )

        try:
            msg = MIMEMultipart()
            msg["From"] = SMTP_USER
            msg["To"] = opt_out_email
            msg["Subject"] = subject
            msg.attach(MIMEText(body, "plain"))

            with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=30) as server:
                server.starttls()
                server.login(SMTP_USER, SMTP_PASS)
                server.send_message(msg)

            return {"status": "submitted", "notes": f"Opt-out email sent to {opt_out_email}"}
        except Exception as exc:
            return {"status": "error", "notes": f"SMTP error: {exc}"}

    def _default_template(self) -> str:
        return (
            "Hello,\n\n"
            "I am requesting the removal of my personal information from your database "
            "under applicable privacy regulations (CCPA / GDPR).\n\n"
            "Name: {full_name}\n"
            "Email: {email}\n"
            "Phone: {phone}\n"
            "Address: {address}, {city}, {state} {zip}\n"
            "Date of Birth: {dob}\n\n"
            "Please confirm the removal of my data at your earliest convenience.\n\n"
            "Thank you."
        )
