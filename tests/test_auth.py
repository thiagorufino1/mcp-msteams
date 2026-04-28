"""Tests for MSAL authentication and token acquisition."""

import pytest
from unittest.mock import MagicMock, patch

from app.graph.errors import AuthError


def test_get_token_returns_access_token():
    """Test that get_token returns a valid access token."""
    mock_app = MagicMock()
    mock_app.acquire_token_for_client.return_value = {"access_token": "test_token_abc"}

    with patch("app.security.auth._get_app", return_value=mock_app):
        from app.security.auth import get_token

        token = get_token(["https://graph.microsoft.com/.default"])

    assert token == "test_token_abc"


def test_get_token_raises_auth_error_on_failure():
    """Test that get_token raises AuthError when token acquisition fails."""
    mock_app = MagicMock()
    mock_app.acquire_token_for_client.return_value = {
        "error": "invalid_client",
        "error_description": "Bad client secret",
    }

    with patch("app.security.auth._get_app", return_value=mock_app):
        from app.security.auth import get_token

        with pytest.raises(AuthError, match="Token acquisition failed"):
            get_token(["https://graph.microsoft.com/.default"])


def test_get_app_is_singleton():
    """Test that _get_app returns the same instance on multiple calls."""
    import app.security.auth as auth_module

    with patch("msal.ConfidentialClientApplication") as mock_cls:
        mock_cls.return_value = MagicMock()
        auth_module._app = None
        app1 = auth_module._get_app()
        app2 = auth_module._get_app()
        assert mock_cls.call_count == 1
        assert app1 is app2
        auth_module._app = None  # cleanup
