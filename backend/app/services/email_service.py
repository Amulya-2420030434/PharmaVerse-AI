"""Gmail SMTP delivery for PharmaVerse AI authentication links and OTPs.

Uses standard Python smtplib with STARTTLS/SSL support. Never exposes OTP codes
or authentication links in application logs.
"""

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import logging
import smtplib
from typing import Optional

from app.core.config import settings

logger = logging.getLogger(__name__)


class EmailService:
    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        user: Optional[str] = None,
        password: Optional[str] = None,
        from_email: Optional[str] = None,
        from_name: Optional[str] = None,
        use_tls: Optional[bool] = None,
    ):
        self.host = host if host is not None else settings.smtp_host
        self.port = port if port is not None else settings.smtp_port
        self.user = user if user is not None else settings.smtp_user
        self.password = password if password is not None else settings.smtp_password
        self.from_email = from_email or settings.smtp_from_email or self.user or "no-reply@pharmaverse.local"
        self.from_name = from_name or settings.smtp_from_name or "PharmaVerse AI Security"
        self.use_tls = use_tls if use_tls is not None else settings.smtp_tls

    @property
    def is_configured(self) -> bool:
        return bool(
            self.host
            and self.host.strip()
            and self.user
            and self.user.strip()
            and self.password
            and self.password.strip()
        )

    def send_auth_link_email(
        self, recipient_email: str, token: str, purpose: str
    ) -> bool:
        action, route = (
            ("verify your email address", "verify-email")
            if purpose == "email_verification"
            else ("reset your password", "reset-password")
        )
        link = f"{settings.frontend_base_url.rstrip('/')}/{route}/{token}"
        subject = f"[{settings.app_name}] {action.title()}"
        ttl = settings.auth_link_ttl_minutes
        text_content = (
            f"Use this secure link to {action}:\n\n{link}\n\n"
            f"This one-time link expires in {ttl} minutes. "
            "If you did not request it, you can ignore this email."
        )
        html_content = (
            f'<p>Use this secure link to {action}:</p><p><a href="{link}">'
            f"{link}</a></p><p>This one-time link expires in {ttl} minutes. "
            "If you did not request it, you can ignore this email.</p>"
        )
        return self._send_message(
            recipient_email,
            subject,
            text_content,
            html_content,
        )

    def send_otp_email(
        self,
        recipient_email: str,
        otp: str,
        purpose: str = "registration",
    ) -> bool:
        """Deliver a one-time verification code over configured SMTP."""
        subject_action = {
            "registration": "Registration Verification Code",
            "password_reset": "Password Reset Code",
            "login_2fa": "Sign-In Verification Code",
        }.get(purpose, "Verification Code")
        subject = f"[{settings.app_name}] {subject_action}"

        text_content = (
            f"Hello,\n\n"
            f"Your verification code for {settings.app_name} is: {otp}\n\n"
            f"This code will expire in {settings.otp_ttl_minutes} minutes. "
            f"If you did not request this code, please ignore this email.\n\n"
            f"— PharmaVerse AI Security Team"
        )

        html_content = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>{subject}</title>
</head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #f7f8fa; margin: 0; padding: 24px; color: #102a43;">
  <div style="max-width: 520px; margin: 0 auto; background-color: #ffffff; border-radius: 12px; border: 1px solid #e2e8f0; padding: 32px; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);">
    <div style="display: inline-block; padding: 6px 12px; border-radius: 6px; background-color: #5a1725; color: #ffffff; font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.15em; margin-bottom: 20px;">
      {settings.app_name}
    </div>
    <h2 style="margin: 0 0 12px 0; color: #102a43; font-size: 22px; font-weight: 700;">{subject_action}</h2>
    <p style="margin: 0 0 24px 0; color: #475569; font-size: 14px; line-height: 22px;">
      Use the following single-use verification code to complete your request. Never share this code with anyone.
    </p>
    <div style="background-color: #f8fafc; border: 1px dashed #cbd5e1; border-radius: 8px; padding: 20px; text-align: center; margin-bottom: 24px;">
      <span style="font-family: 'Courier New', Courier, monospace; font-size: 32px; font-weight: 800; letter-spacing: 8px; color: #5a1725;">{otp}</span>
    </div>
    <p style="margin: 0 0 8px 0; color: #64748b; font-size: 13px;">
      This code expires in <strong>{settings.otp_ttl_minutes} minutes</strong> and can only be used once.
    </p>
    <p style="margin: 0; color: #94a3b8; font-size: 12px; line-height: 18px;">
      If you did not initiate this request, no further action is required.
    </p>
  </div>
</body>
</html>
"""

        return self._send_message(
            recipient_email,
            subject,
            text_content,
            html_content,
        )

    def _send_message(
        self,
        recipient_email: str,
        subject: str,
        text_content: str,
        html_content: str,
    ) -> bool:
        if not self.is_configured:
            logger.error("SMTP credentials are not configured; email delivery unavailable")
            return False

        message = MIMEMultipart("alternative")
        message["Subject"] = subject
        message["From"] = f"{self.from_name} <{self.from_email}>"
        message["To"] = recipient_email
        message.attach(MIMEText(text_content, "plain", "utf-8"))
        message.attach(MIMEText(html_content, "html", "utf-8"))
        try:
            if self.port == 465:
                # SSL
                with smtplib.SMTP_SSL(self.host, self.port, timeout=10.0) as server:
                    if self.user and self.password:
                        server.login(self.user, self.password)
                    server.send_message(message)
            else:
                # STARTTLS or plain SMTP
                with smtplib.SMTP(self.host, self.port, timeout=10.0) as server:
                    if self.use_tls:
                        server.starttls()
                    if self.user and self.password:
                        server.login(self.user, self.password)
                    server.send_message(message)

            logger.info("Successfully delivered authentication email to %s", recipient_email)
            return True
        except (smtplib.SMTPException, OSError) as exc:
            logger.error(
                "Failed to deliver SMTP email to %s: %s",
                recipient_email,
                exc.__class__.__name__,
            )
            return False


email_service = EmailService()
