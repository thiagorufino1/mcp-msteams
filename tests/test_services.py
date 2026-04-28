import pytest
from unittest.mock import AsyncMock, patch


@pytest.mark.asyncio
async def test_get_user_profile_calls_graph():
    mock_result = {"id": "abc123", "displayName": "Alice", "userPrincipalName": "alice@corp.com"}

    with patch("mcp_msteams.services.users_service.graph_get", new=AsyncMock(return_value=mock_result)):
        from mcp_msteams.services.users_service import get_user_profile
        result = await get_user_profile("alice@corp.com")

    assert result["id"] == "abc123"
    assert result["displayName"] == "Alice"


@pytest.mark.asyncio
async def test_detect_orphaned_team_no_members():
    with patch("mcp_msteams.services.teams_service.graph_get_all", new=AsyncMock(return_value=[])):
        from mcp_msteams.services.teams_service import detect_orphaned_team
        result = await detect_orphaned_team("team-uuid-123")
    assert result["is_orphaned"] is True
    assert result["member_count"] == 0


@pytest.mark.asyncio
async def test_detect_team_without_owner_has_owners():
    owners_list = [{"id": "u1", "displayName": "Alice"}]
    with patch("mcp_msteams.services.teams_service.graph_get_all", new=AsyncMock(return_value=owners_list)):
        from mcp_msteams.services.teams_service import detect_team_without_owner
        result = await detect_team_without_owner("team-uuid-123")
    assert result["has_no_owner"] is False
    assert result["owner_count"] == 1


@pytest.mark.asyncio
async def test_get_user_overview_combines_profile_and_teams():
    profile = {"id": "abc123", "displayName": "Alice", "userPrincipalName": "alice@corp.com"}
    teams_list = [{"id": "t1", "displayName": "Sales Team"}]
    presence = {"availability": "Available", "activity": "Available"}

    async def mock_graph_get(path, *args, **kwargs):
        if "presences" in path:
            return presence
        return profile

    with patch("mcp_msteams.services.users_service.graph_get", new=mock_graph_get), \
         patch("mcp_msteams.services.users_service.graph_get_all", new=AsyncMock(return_value=teams_list)):
        from mcp_msteams.services.users_service import get_user_overview
        result = await get_user_overview("alice@corp.com")

    assert result["upn"] == "alice@corp.com"
    assert result["profile"]["displayName"] == "Alice"
    assert result["teams"]["value"][0]["displayName"] == "Sales Team"
