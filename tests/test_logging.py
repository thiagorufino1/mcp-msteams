from __future__ import annotations

import pytest
from unittest.mock import patch

from mcp_msteams.logging_config import audited, _result_status


def test_result_status_for_structured_error_response():
    status, error_type = _result_status({"error": "permission_denied", "message": "Forbidden"})
    assert status == "error"
    assert error_type == "permission_denied"


@pytest.mark.asyncio
async def test_audited_sanitizes_logged_exception_message():
    captured: list[str] = []

    @audited
    async def sample_tool() -> dict[str, str]:
        raise RuntimeError("token eyJabc.def.ghi for alice@contoso.com")

    def fake_error(_event: str, **kwargs: str) -> None:
        captured.append(kwargs["error"])

    with patch("mcp_msteams.logging_config.logger.error", new=fake_error):
        with pytest.raises(RuntimeError):
            await sample_tool()

    assert captured
    assert "[TOKEN]" in captured[0]
    assert "alice@contoso.com" not in captured[0]
