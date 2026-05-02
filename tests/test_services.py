import pytest
from unittest.mock import AsyncMock, patch
from datetime import datetime, timezone


@pytest.mark.asyncio
async def test_get_user_profile_calls_graph():
    mock_result = {"id": "abc123", "displayName": "Alice", "userPrincipalName": "alice@corp.com"}

    with patch("mcp_msteams.services.users_service.graph_get", new=AsyncMock(return_value=mock_result)):
        from mcp_msteams.services.users_service import get_user_profile
        result = await get_user_profile("alice@corp.com")

    assert result["id"] == "abc123"
    assert result["displayName"] == "Alice"
    assert "## Perfil do Usuário: Alice" in result["markdown"]


@pytest.mark.asyncio
async def test_detect_orphaned_team_no_members():
    with patch("mcp_msteams.services.teams_service.graph_get_all", new=AsyncMock(return_value=[])):
        from mcp_msteams.services.teams_service import detect_orphaned_team
        result = await detect_orphaned_team("team-uuid-123")
    assert result["is_orphaned"] is True
    assert result["member_count"] == 0


@pytest.mark.asyncio
async def test_detect_orphaned_team_uses_team_members_endpoint():
    captured_paths: list[str] = []

    async def mock_graph_get_all(path, *args, **kwargs):
        captured_paths.append(path)
        return [{"id": "u1"}]

    with patch("mcp_msteams.services.teams_service.graph_get_all", new=mock_graph_get_all):
        from mcp_msteams.services.teams_service import detect_orphaned_team
        result = await detect_orphaned_team("team-uuid-123")

    assert result["member_count"] == 1
    assert captured_paths == ["/teams/team-uuid-123/members"]


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


@pytest.mark.asyncio
async def test_list_failed_calls_filters_recent_records_by_user_participant_id():
    captured: dict[str, object] = {}

    async def mock_graph_get_all(path, *args, **kwargs):
        captured["path"] = path
        captured["params"] = kwargs.get("params")
        captured["extra_headers"] = kwargs.get("extra_headers")
        return [{"id": "call-1"}, {"id": "call-2"}]

    async def mock_graph_get(path, *args, **kwargs):
        if path.startswith("/communications/callRecords/call-1"):
            return {
                "id": "call-1",
                "result": "failure",
                "startDateTime": "2026-04-28T10:00:00Z",
                "participants_v2": [{"id": "user-123"}],
            }
        return {"id": "call-2", "startDateTime": "2026-04-28T11:00:00Z", "participants_v2": [{"id": "other-user"}]}

    with patch("mcp_msteams.services.calls_service.graph_get_all", new=mock_graph_get_all), \
         patch("mcp_msteams.services.calls_service.graph_get", new=mock_graph_get), \
         patch("mcp_msteams.services.calls_service.get_user_profile", new=AsyncMock(return_value={"id": "user-123"})):
        from mcp_msteams.services.calls_service import list_failed_calls
        result = await list_failed_calls("alice@corp.com", days=7)

    params = captured["params"]
    assert isinstance(params, dict)
    assert "startDateTime ge '" not in params["$filter"]
    assert "startDateTime ge " in params["$filter"]
    assert captured["path"] == "/communications/callRecords"
    assert captured["extra_headers"] == {"Prefer": "odata.maxpagesize=60"}
    assert len(result["failed_calls"]) == 1
    assert result["failed_calls"][0]["id"] == "call-1"


@pytest.mark.asyncio
async def test_list_failed_calls_matches_nested_participant_user_identity():
    async def mock_graph_get_all(path, *args, **kwargs):
        return [{"id": "call-1"}]

    async def mock_graph_get(path, *args, **kwargs):
        return {
            "id": "call-1",
            "result": "failure",
            "startDateTime": "2026-04-28T10:00:00Z",
            "participants_v2": [
                {
                    "id": "participant-record-id",
                    "identity": {
                        "user": {
                            "id": "user-123",
                            "userPrincipalName": "alice@corp.com",
                        }
                    },
                }
            ],
        }

    with patch("mcp_msteams.services.calls_service.graph_get_all", new=mock_graph_get_all), \
         patch("mcp_msteams.services.calls_service.graph_get", new=mock_graph_get), \
         patch("mcp_msteams.services.calls_service.get_user_profile", new=AsyncMock(return_value={"id": "user-123"})):
        from mcp_msteams.services.calls_service import list_failed_calls
        result = await list_failed_calls("alice@corp.com", days=7)

    assert len(result["failed_calls"]) == 1
    assert result["failed_calls"][0]["id"] == "call-1"


@pytest.mark.asyncio
async def test_list_failed_calls_sorts_records_descending_by_start_time():
    async def mock_graph_get_all(path, *args, **kwargs):
        return [{"id": "call-1"}, {"id": "call-2"}]

    async def mock_graph_get(path, *args, **kwargs):
        if path.startswith("/communications/callRecords/call-1"):
            return {
                "id": "call-1",
                "result": "failure",
                "startDateTime": "2026-04-28T09:00:00Z",
                "participants_v2": [{"id": "user-123"}],
            }
        return {
            "id": "call-2",
            "result": "failure",
            "startDateTime": "2026-04-28T11:00:00Z",
            "participants_v2": [{"id": "user-123"}],
        }

    with patch("mcp_msteams.services.calls_service.graph_get_all", new=mock_graph_get_all), \
         patch("mcp_msteams.services.calls_service.graph_get", new=mock_graph_get), \
         patch("mcp_msteams.services.calls_service.get_user_profile", new=AsyncMock(return_value={"id": "user-123"})):
        from mcp_msteams.services.calls_service import list_failed_calls
        result = await list_failed_calls("alice@corp.com", days=7)

    assert [record["id"] for record in result["failed_calls"]] == ["call-2", "call-1"]


@pytest.mark.asyncio
async def test_list_failed_calls_uses_expanded_call_records_page_budget():
    captured: dict[str, object] = {}

    async def mock_graph_get_all(path, *args, **kwargs):
        captured["max_pages"] = kwargs.get("max_pages")
        return []

    with patch("mcp_msteams.services.calls_service.graph_get_all", new=mock_graph_get_all), \
         patch("mcp_msteams.services.calls_service.get_user_profile", new=AsyncMock(return_value={"id": "user-123"})):
        from mcp_msteams.services.calls_service import list_failed_calls
        await list_failed_calls("alice@corp.com", days=7)

    assert captured["max_pages"] == 12


def test_call_records_date_filter_uses_safe_cutoff_for_30_days():
    fake_now = datetime(2026, 4, 29, 1, 15, 30, tzinfo=timezone.utc)

    with patch("mcp_msteams.services.calls_service.utc_now", return_value=fake_now):
        from mcp_msteams.services.calls_service import _call_records_date_filter
        filter_value = _call_records_date_filter(30)

    assert filter_value == "startDateTime ge 2026-03-30T01:20:30Z"


@pytest.mark.asyncio
async def test_list_teams_without_members_respects_scan_cap():
    page_calls = {"count": 0}

    async def mock_graph_get(path, *args, **kwargs):
        page_calls["count"] += 1
        return {
            "@odata.count": 5000,
            "value": [{"id": f"team-{page_calls['count']}", "displayName": f"Team {page_calls['count']}"}],
            "@odata.nextLink": "/groups?page=next",
        }

    with patch("mcp_msteams.services.teams_service.graph_get", new=mock_graph_get), \
         patch("mcp_msteams.services.teams_service._get_member_count", new=AsyncMock(return_value=0)), \
         patch("mcp_msteams.services.teams_service._TEAM_SCAN_MAX_TEAMS", 2):
        from mcp_msteams.services.teams_service import list_teams_without_members
        result = await list_teams_without_members(top=10)

    assert result["teams_scanned"] == 2
    assert result["is_complete_scan"] is False
@pytest.mark.asyncio
async def test_get_user_overview_includes_team_ids_in_markdown():
    profile = {"id": "abc123", "displayName": "Alice", "userPrincipalName": "alice@corp.com"}
    teams_list = [{"id": "team-id-999", "displayName": "Secret Project"}]
    presence = {"availability": "Available", "activity": "Available"}

    async def mock_graph_get(path, *args, **kwargs):
        if "presence" in path:
            return presence
        return profile

    with patch("mcp_msteams.services.users_service.graph_get", new=mock_graph_get), \
         patch("mcp_msteams.services.users_service.graph_get_all", new=AsyncMock(return_value=teams_list)):
        from mcp_msteams.services.users_service import get_user_overview
        result = await get_user_overview("alice@corp.com")

    markdown = result["markdown"]
    assert "Secret Project" in markdown
    assert "team-id-999" in markdown
    # Verify the formatting is correct (Markdown bold + code)
    assert "**Secret Project** (`team-id-999`)" in markdown


@pytest.mark.asyncio
async def test_get_user_assigned_policies_reads_effective_policy_assignments():
    user_config = {
        "value": [
            {
                "id": "user-123",
                "userPrincipalName": "alice@corp.com",
                "effectivePolicyAssignments": [
                    {
                        "policyType": "TeamsMeetingPolicy",
                        "policyAssignment": {
                            "displayName": "CustomMeetingPolicy",
                            "assignmentType": "direct",
                            "policyId": "policy-1",
                        },
                    },
                    {
                        "policyType": "TeamsCallingPolicy",
                        "policyAssignment": {
                            "displayName": "AllOn",
                            "assignmentType": "group",
                            "policyId": "policy-2",
                            "groupId": "group-123",
                        },
                    },
                ],
            }
        ]
    }

    with patch("mcp_msteams.services.users_service.graph_get", new=AsyncMock(return_value=user_config)):
        from mcp_msteams.services.users_service import get_user_assigned_policies
        result = await get_user_assigned_policies("alice@corp.com")

    assert result["user_id"] == "user-123"
    assert result["count"] == 2
    assert result["assigned_policies"][0]["policyType"] == "TeamsMeetingPolicy"
    assert result["assigned_policies"][0]["policyName"] == "CustomMeetingPolicy"
    assert result["assigned_policies"][1]["assignmentType"] == "group"


@pytest.mark.asyncio
async def test_check_known_teams_incidents_uses_pt_br_labels():
    issue_list = [
        {
            "id": "TM123",
            "service": "Microsoft Teams",
            "status": "serviceDegradation",
            "classification": "advisory",
            "title": "Example issue",
        }
    ]
    issue_detail = {
        "id": "TM123",
        "service": "Microsoft Teams",
        "status": "serviceDegradation",
        "classification": "advisory",
        "title": "Example issue",
        "posts": [
            {
                "description": {
                    "content": (
                        "Current status: Monitoring a fix. "
                        "Root cause: Example cause. "
                        "Next update by: Monday, May 4, 2026, at 1:00 PM UTC"
                    )
                }
            }
        ],
    }

    with patch("mcp_msteams.services.incidents_service.graph_get_all", new=AsyncMock(return_value=issue_list)), \
         patch("mcp_msteams.services.incidents_service.graph_get", new=AsyncMock(return_value=issue_detail)):
        from mcp_msteams.services.incidents_service import check_known_teams_incidents
        result = await check_known_teams_incidents()

    markdown = result["markdown"]
    assert "## Integridade do Serviço do Teams (1)" in markdown
    assert "**Avisos:** 1" in markdown
    assert "| ID | Título | Resumo das atividades |" in markdown
    assert "Causa raiz: Example cause." in markdown
    assert "Próxima atualização até:" in markdown
