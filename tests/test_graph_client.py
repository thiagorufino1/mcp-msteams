import pytest
import respx
import httpx
from unittest.mock import patch
from mcp_msteams.graph.errors import ThrottlingError, NotFoundError, AuthError
from mcp_msteams.graph.cache import clear_cache


MOCK_TOKEN = "mock_bearer_token"


@pytest.fixture(autouse=True)
def reset_cache():
    clear_cache()
    yield


@pytest.fixture
def mock_token():
    with patch("mcp_msteams.graph.client.get_token", return_value=MOCK_TOKEN):
        yield


@pytest.mark.asyncio
@respx.mock
async def test_graph_get_200(mock_token):
    respx.get("https://graph.microsoft.com/v1.0/users/user@test.com").mock(
        return_value=httpx.Response(200, json={"id": "abc123", "displayName": "Test User"})
    )
    from mcp_msteams.graph.client import graph_get
    result = await graph_get("/users/user@test.com", scopes=["https://graph.microsoft.com/.default"])
    assert result["id"] == "abc123"


@pytest.mark.asyncio
@respx.mock
async def test_graph_get_404_raises_not_found(mock_token):
    respx.get("https://graph.microsoft.com/v1.0/users/ghost@test.com").mock(
        return_value=httpx.Response(404, json={"error": {"code": "Request_ResourceNotFound"}})
    )
    from mcp_msteams.graph.client import graph_get
    with pytest.raises(NotFoundError):
        await graph_get("/users/ghost@test.com", scopes=["https://graph.microsoft.com/.default"])


@pytest.mark.asyncio
@respx.mock
async def test_graph_get_401_raises_auth_error(mock_token):
    respx.get("https://graph.microsoft.com/v1.0/users/u@t.com").mock(
        return_value=httpx.Response(401, json={"error": {"code": "InvalidAuthenticationToken"}})
    )
    from mcp_msteams.graph.client import graph_get
    with pytest.raises(AuthError):
        await graph_get("/users/u@t.com", scopes=["https://graph.microsoft.com/.default"])


@pytest.mark.asyncio
@respx.mock
async def test_graph_get_uses_cache_on_second_call(mock_token):
    route = respx.get("https://graph.microsoft.com/v1.0/teams/team1").mock(
        return_value=httpx.Response(200, json={"id": "team1", "displayName": "Team One"})
    )
    from mcp_msteams.graph.client import graph_get
    r1 = await graph_get("/teams/team1", scopes=["https://graph.microsoft.com/.default"], cache_key="teams:team1", ttl=60)
    r2 = await graph_get("/teams/team1", scopes=["https://graph.microsoft.com/.default"], cache_key="teams:team1", ttl=60)
    assert r1 == r2
    assert route.call_count == 1


@pytest.mark.asyncio
@respx.mock
async def test_graph_get_429_raises_throttling_after_retries(mock_token):
    # Patch retry to not actually sleep (speed up test)
    respx.get("https://graph.microsoft.com/v1.0/users/slow@test.com").mock(
        return_value=httpx.Response(429, headers={"Retry-After": "0"}, json={})
    )
    from mcp_msteams.graph.client import graph_get
    with pytest.raises(ThrottlingError):
        await graph_get("/users/slow@test.com", scopes=["https://graph.microsoft.com/.default"])
