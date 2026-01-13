"""Unit tests for core/email.py to cover email sending functionality."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from core.email import send_email, send_password_reset_email, send_verification_email


class TestGetEmailClient:
    """Tests for email client initialization."""

    def test_no_connection_string_returns_none(self):
        """When connection string is not configured, client should be None."""
        with patch("core.email.get_settings") as mock_settings:
            mock_settings.return_value.AZURE_COMMUNICATION_CONNECTION_STRING = None
            from core.email import _get_email_client

            result = _get_email_client()
            assert result is None


class TestSendEmail:
    """Tests for the generic send_email function."""

    def test_send_email_no_client(self):
        """When client is not available, should return False."""
        with patch("core.email._get_email_client", return_value=None):
            result = send_email(
                to_email="test@example.com",
                subject="Test",
                html_content="<p>Test</p>",
            )
            assert result is False

    def test_send_email_success(self):
        """Successful email sending should return True."""
        mock_client = MagicMock()
        mock_poller = MagicMock()
        mock_poller.result.return_value = {"id": "msg-123"}
        mock_client.begin_send.return_value = mock_poller

        with (
            patch("core.email._get_email_client", return_value=mock_client),
            patch("core.email.get_settings") as mock_settings,
        ):
            mock_settings.return_value.EMAIL_SENDER_ADDRESS = "sender@example.com"
            result = send_email(
                to_email="test@example.com",
                subject="Test Subject",
                html_content="<p>Test HTML</p>",
            )
            assert result is True
            mock_client.begin_send.assert_called_once()

    def test_send_email_with_plain_text(self):
        """Email with plain text content should include it in the message."""
        mock_client = MagicMock()
        mock_poller = MagicMock()
        mock_poller.result.return_value = {"id": "msg-123"}
        mock_client.begin_send.return_value = mock_poller

        with (
            patch("core.email._get_email_client", return_value=mock_client),
            patch("core.email.get_settings") as mock_settings,
        ):
            mock_settings.return_value.EMAIL_SENDER_ADDRESS = "sender@example.com"
            result = send_email(
                to_email="test@example.com",
                subject="Test Subject",
                html_content="<p>Test HTML</p>",
                plain_text_content="Test plain text",
            )
            assert result is True
            # Verify the message includes plainText
            call_args = mock_client.begin_send.call_args[0][0]
            assert "plainText" in call_args["content"]
            assert call_args["content"]["plainText"] == "Test plain text"

    def test_send_email_http_error(self):
        """HTTP error during send should return False."""
        from azure.core.exceptions import HttpResponseError

        mock_client = MagicMock()
        error = HttpResponseError(message="Server error")
        error.status_code = 500
        mock_client.begin_send.side_effect = error

        with (
            patch("core.email._get_email_client", return_value=mock_client),
            patch("core.email.get_settings") as mock_settings,
        ):
            mock_settings.return_value.EMAIL_SENDER_ADDRESS = "sender@example.com"
            result = send_email(
                to_email="test@example.com",
                subject="Test",
                html_content="<p>Test</p>",
            )
            assert result is False

    def test_send_email_unexpected_error(self):
        """Unexpected error during send should return False."""
        mock_client = MagicMock()
        mock_client.begin_send.side_effect = RuntimeError("Unexpected")

        with (
            patch("core.email._get_email_client", return_value=mock_client),
            patch("core.email.get_settings") as mock_settings,
        ):
            mock_settings.return_value.EMAIL_SENDER_ADDRESS = "sender@example.com"
            result = send_email(
                to_email="test@example.com",
                subject="Test",
                html_content="<p>Test</p>",
            )
            assert result is False


class TestSendVerificationEmail:
    """Tests for the send_verification_email function."""

    def test_send_verification_email_success(self):
        """Successful verification email should return True."""
        with (
            patch("core.email.send_email", return_value=True) as mock_send,
            patch("core.email.get_settings") as mock_settings,
        ):
            mock_settings.return_value.FRONTEND_URL = "https://example.com"
            result = send_verification_email("user@example.com", "test-token-123")
            assert result is True
            mock_send.assert_called_once()
            call_args = mock_send.call_args
            assert call_args[0][0] == "user@example.com"
            assert "Verify your PantryPilot account" in call_args[0][1]
            # Check token is in HTML content
            assert "test-token-123" in call_args[0][2]

    def test_send_verification_email_failure(self):
        """Failed verification email should return False."""
        with (
            patch("core.email.send_email", return_value=False),
            patch("core.email.get_settings") as mock_settings,
        ):
            mock_settings.return_value.FRONTEND_URL = "https://example.com"
            result = send_verification_email("user@example.com", "test-token")
            assert result is False

    def test_send_verification_email_link_format(self):
        """Verification link should be correctly formatted."""
        with (
            patch("core.email.send_email", return_value=True) as mock_send,
            patch("core.email.get_settings") as mock_settings,
        ):
            mock_settings.return_value.FRONTEND_URL = "https://pantrypilot.com"
            send_verification_email("user@example.com", "my-verification-token")
            call_args = mock_send.call_args
            html_content = call_args[0][2]
            expected_link = (
                "https://pantrypilot.com/verify-email?token=my-verification-token"
            )
            assert expected_link in html_content

    def test_send_verification_email_includes_expiry_warning(self):
        """Verification email should mention 1 hour expiry."""
        with (
            patch("core.email.send_email", return_value=True) as mock_send,
            patch("core.email.get_settings") as mock_settings,
        ):
            mock_settings.return_value.FRONTEND_URL = "https://example.com"
            send_verification_email("user@example.com", "verification-token")
            call_args = mock_send.call_args
            html_content = call_args[0][2]
            assert "1 hour" in html_content


class TestSendPasswordResetEmail:
    """Tests for the send_password_reset_email function."""

    def test_send_password_reset_email_success(self):
        """Successful password reset email should return True."""
        with (
            patch("core.email.send_email", return_value=True) as mock_send,
            patch("core.email.get_settings") as mock_settings,
        ):
            mock_settings.return_value.FRONTEND_URL = "https://example.com"
            result = send_password_reset_email("user@example.com", "reset-token-456")
            assert result is True
            mock_send.assert_called_once()
            call_args = mock_send.call_args
            assert call_args[0][0] == "user@example.com"
            assert "Reset your PantryPilot password" in call_args[0][1]
            # Check token is in HTML content
            assert "reset-token-456" in call_args[0][2]

    def test_send_password_reset_email_failure(self):
        """Failed password reset email should return False."""
        with (
            patch("core.email.send_email", return_value=False),
            patch("core.email.get_settings") as mock_settings,
        ):
            mock_settings.return_value.FRONTEND_URL = "https://example.com"
            result = send_password_reset_email("user@example.com", "reset-token")
            assert result is False

    def test_send_password_reset_email_link_format(self):
        """Reset link should be correctly formatted."""
        with (
            patch("core.email.send_email", return_value=True) as mock_send,
            patch("core.email.get_settings") as mock_settings,
        ):
            mock_settings.return_value.FRONTEND_URL = "https://pantrypilot.com"
            send_password_reset_email("user@example.com", "my-reset-token")
            call_args = mock_send.call_args
            html_content = call_args[0][2]
            expected_link = (
                "https://pantrypilot.com/reset-password?token=my-reset-token"
            )
            assert expected_link in html_content

    def test_send_password_reset_email_includes_expiry_warning(self):
        """Password reset email should mention 1 hour expiry."""
        with (
            patch("core.email.send_email", return_value=True) as mock_send,
            patch("core.email.get_settings") as mock_settings,
        ):
            mock_settings.return_value.FRONTEND_URL = "https://example.com"
            send_password_reset_email("user@example.com", "reset-token")
            call_args = mock_send.call_args
            html_content = call_args[0][2]
            assert "1 hour" in html_content
