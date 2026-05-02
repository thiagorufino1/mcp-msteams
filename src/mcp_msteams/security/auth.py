from __future__ import annotations

import threading

import msal

from mcp_msteams.config import settings
from mcp_msteams.graph.errors import AuthError

_app: msal.ConfidentialClientApplication | None = None
_app_lock = threading.Lock()


def _get_app() -> msal.ConfidentialClientApplication:
    global _app
    if _app is None:
        with _app_lock:
            if _app is None:
                _app = msal.ConfidentialClientApplication(
                    settings.azure_client_id,
                    authority=f"https://login.microsoftonline.com/{settings.azure_tenant_id}",
                    client_credential=settings.azure_client_secret.get_secret_value(),
                )
    return _app


def get_token(scopes: list[str]) -> str:
    app = _get_app()
    result = app.acquire_token_for_client(scopes=scopes)
    if "access_token" not in result:
        raise AuthError(
            f"Token acquisition failed: {result.get('error', 'unknown')}",
            status_code=401,
        )
    return result["access_token"]
