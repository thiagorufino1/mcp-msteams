import pytest
from unittest.mock import MagicMock, patch

import mcp_msteams.security.auth as auth_module
from mcp_msteams.security.auth import get_token
from mcp_msteams.graph.errors import AuthError


def test_get_token_returns_access_token():
    mock_app = MagicMock()
    mock_app.acquire_token_for_client.return_value = {"access_token": "test_token_abc"}
    original_app = auth_module._app
    try:
        auth_module._app = mock_app
        token = get_token(["https://graph.microsoft.com/.default"])
    finally:
        auth_module._app = original_app
    assert token == "test_token_abc"


def test_get_token_raises_auth_error_on_failure():
    mock_app = MagicMock()
    mock_app.acquire_token_for_client.return_value = {
        "error": "invalid_client",
        "error_description": "Bad client secret",
    }
    original_app = auth_module._app
    try:
        auth_module._app = mock_app
        with pytest.raises(AuthError, match="Token acquisition failed"):
            get_token(["https://graph.microsoft.com/.default"])
    finally:
        auth_module._app = original_app


def test_get_app_is_singleton():
    with patch("msal.ConfidentialClientApplication") as mock_cls:
        mock_cls.return_value = MagicMock()
        original_app = auth_module._app
        auth_module._app = None
        try:
            app1 = auth_module._get_app()
            app2 = auth_module._get_app()
            assert mock_cls.call_count == 1
            assert app1 is app2
        finally:
            auth_module._app = original_app
