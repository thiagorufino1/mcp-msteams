from __future__ import annotations

import pytest

from mcp_msteams.logging_config import audited


@pytest.mark.asyncio
async def test_audited_records_error_status_for_structured_error_response():
    recorded: list[tuple[str, str | None]] = []

    @audited
    async def sample_tool() -> dict[str, str]:
        return {"error": "permission_denied", "message": "Forbidden"}

    def fake_record(tool: str, safe_kwargs: dict[str, str], elapsed_ms: int, status: str, error_type: str | None) -> None:
        recorded.append((status, error_type))

    from unittest.mock import patch

    with patch("mcp_msteams.logging_config._record", new=fake_record):
        result = await sample_tool()

    assert result["error"] == "permission_denied"
    assert recorded == [("error", "permission_denied")]
