import pytest
from unittest.mock import AsyncMock, patch


@pytest.mark.asyncio
async def test_get_user_profile_calls_graph():
    mock_result = {"id": "abc123", "displayName": "Alice", "userPrincipalName": "alice@corp.com"}

    with patch("app.services.users_service.graph_get", new=AsyncMock(return_value=mock_result)):
        from app.services.users_service import get_user_profile
        result = await get_user_profile("alice@corp.com")

    assert result["id"] == "abc123"
    assert result["displayName"] == "Alice"


@pytest.mark.asyncio
async def test_get_user_overview_combines_profile_and_teams():
    profile = {"id": "abc123", "displayName": "Alice", "userPrincipalName": "alice@corp.com"}
    teams = {"value": [{"id": "t1", "displayName": "Sales Team"}]}
    presence = {"availability": "Available", "activity": "Available"}

    async def mock_graph_get(path, *args, **kwargs):
        if "joinedTeams" in path:
            return teams
        if "presences" in path:
            return presence
        return profile

    with patch("app.services.users_service.graph_get", new=mock_graph_get):
        from app.services.users_service import get_user_overview
        result = await get_user_overview("alice@corp.com")

    assert result["upn"] == "alice@corp.com"
    assert result["profile"]["displayName"] == "Alice"
    assert result["teams"]["value"][0]["displayName"] == "Sales Team"
