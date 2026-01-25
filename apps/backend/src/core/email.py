"""Email sending utility using Azure Communication Services.

Provides functionality to send transactional emails like verification
and password reset emails through Azure Communication Services.
"""

import logging
from typing import Any

from azure.communication.email import EmailClient
from azure.core.exceptions import HttpResponseError

from core.config import get_settings


_logger = logging.getLogger(__name__)


def _get_email_client() -> EmailClient | None:
    """Get an EmailClient instance from the connection string.

    Returns None if the connection string is not configured.
    """
    settings = get_settings()
    if not settings.AZURE_COMMUNICATION_CONNECTION_STRING:
        _logger.warning(
            "AZURE_COMMUNICATION_CONNECTION_STRING is not configured. "
            "Email sending is disabled."
        )
        return None
    return EmailClient.from_connection_string(
        settings.AZURE_COMMUNICATION_CONNECTION_STRING
    )


def send_email(
    to_email: str,
    subject: str,
    html_content: str,
    plain_text_content: str | None = None,
) -> bool:
    """Send an email using Azure Communication Services.

    Args:
        to_email: Recipient email address.
        subject: Email subject line.
        html_content: HTML body content.
        plain_text_content: Optional plain text fallback content.

    Returns:
        True if the email was sent successfully, False otherwise.
    """
    client = _get_email_client()
    if client is None:
        _logger.info("Email client not available. Email to %s not sent.", to_email)
        return False

    settings = get_settings()
    message: dict[str, Any] = {
        "senderAddress": settings.EMAIL_SENDER_ADDRESS,
        "recipients": {"to": [{"address": to_email}]},
        "content": {
            "subject": subject,
            "html": html_content,
        },
    }

    if plain_text_content:
        message["content"]["plainText"] = plain_text_content

    try:
        poller = client.begin_send(message)
        result = poller.result()
        _logger.info(
            "Email sent successfully to %s. Message ID: %s",
            to_email,
            result.get("id", "unknown"),
        )
        return True
    except HttpResponseError as err:
        _logger.error(
            "Failed to send email to %s: %s (Status: %s)",
            to_email,
            err.message,
            err.status_code,
        )
        return False
    except Exception as exc:
        _logger.exception("Unexpected error sending email to %s: %s", to_email, exc)
        return False


def send_verification_email(to_email: str, verification_token: str) -> bool:
    """Send an email verification link to a new user.

    Args:
        to_email: User's email address.
        verification_token: Token to include in the verification link.

    Returns:
        True if the email was sent successfully, False otherwise.
    """
    settings = get_settings()
    verification_link = (
        f"{settings.FRONTEND_URL}/verify-email?token={verification_token}"
    )

    subject = "Verify your PantryPilot account"
    html_content = f"""
    <html>
    <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <h1 style="color: #4CAF50;">Welcome to PantryPilot!</h1>
        <p>Thank you for signing up. Please verify your email address
        by clicking the button below:</p>
        <p style="text-align: center; margin: 30px 0;">
            <a href="{verification_link}"
               style="background-color: #4CAF50; color: white; padding: 12px 24px;
                      text-decoration: none; border-radius: 4px;">
                Verify Email Address
            </a>
        </p>
        <p>Or copy and paste this link into your browser:</p>
        <p style="word-break: break-all; color: #666;">{verification_link}</p>
        <p style="color: #999; font-size: 12px; margin-top: 30px;">
            If you didn't create an account, you can safely ignore this email.
            This link will expire in 1 hour.
        </p>
    </body>
    </html>
    """
    plain_text = f"""
Welcome to PantryPilot!

Thank you for signing up. Please verify your email address by visiting this link:

{verification_link}

If you didn't create an account, you can safely ignore this email.
This link will expire in 1 hour.
"""
    return send_email(to_email, subject, html_content, plain_text)


def send_password_reset_email(to_email: str, reset_token: str) -> bool:
    """Send a password reset link to a user.

    Args:
        to_email: User's email address.
        reset_token: Token to include in the reset link.

    Returns:
        True if the email was sent successfully, False otherwise.
    """
    settings = get_settings()
    reset_link = f"{settings.FRONTEND_URL}/reset-password?token={reset_token}"

    subject = "Reset your PantryPilot password"
    html_content = f"""
    <html>
    <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <h1 style="color: #4CAF50;">Password Reset Request</h1>
        <p>We received a request to reset your password. Click the button below
        to set a new password:</p>
        <p style="text-align: center; margin: 30px 0;">
            <a href="{reset_link}"
               style="background-color: #4CAF50; color: white; padding: 12px 24px;
                      text-decoration: none; border-radius: 4px;">
                Reset Password
            </a>
        </p>
        <p>Or copy and paste this link into your browser:</p>
        <p style="word-break: break-all; color: #666;">{reset_link}</p>
        <p style="color: #999; font-size: 12px; margin-top: 30px;">
            If you didn't request a password reset, you can safely ignore
            this email. This link will expire in 1 hour.
        </p>
    </body>
    </html>
    """
    plain_text = f"""
Password Reset Request

We received a request to reset your password. Visit this link to set a new password:

{reset_link}

If you didn't request a password reset, you can safely ignore this email.
This link will expire in 1 hour.
"""
    return send_email(to_email, subject, html_content, plain_text)
