"""MSAL authentication wrapper for Microsoft Graph API token acquisition."""

from __future__ import annotations

import msal

from app.config import settings
from app.graph.errors import AuthError

_app: msal.ConfidentialClientApplication | None = None


def _get_app() -> msal.ConfidentialClientApplication:
    """Get or create a singleton MSAL ConfidentialClientApplication instance."""
    global _app
    if _app is None:
        _app = msal.ConfidentialClientApplication(
            settings.azure_client_id,
            authority=f"https://login.microsoftonline.com/{settings.azure_tenant_id}",
            client_credential=settings.azure_client_secret,
        )
    return _app


def get_token(scopes: list[str]) -> str:
    """
    Acquire an access token for the specified scopes using client credentials flow.

    Args:
        scopes: List of scopes (e.g., ["https://graph.microsoft.com/.default"]).

    Returns:
        The access token string.

    Raises:
        AuthError: If token acquisition fails.
    """
    app = _get_app()
    result = app.acquire_token_for_client(scopes=scopes)
    if "access_token" not in result:
        raise AuthError(
            f"Token acquisition failed: {result.get('error_description', result.get('error', 'unknown'))}",
            status_code=401,
        )
    return result["access_token"]
