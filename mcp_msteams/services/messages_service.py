from mcp_msteams.utils.response import not_implemented_response


async def get_recent_channel_messages(team_id: str, channel_id: str, count: int = 20) -> dict:
    # TODO: GET /teams/{team_id}/channels/{channel_id}/messages?$top={count}
    # Requires: ChannelMessage.Read.All
    return not_implemented_response("get_recent_channel_messages", "GET /teams/{id}/channels/{id}/messages — needs ChannelMessage.Read.All")


async def search_channel_messages(team_id: str, channel_id: str, query: str) -> dict:
    # TODO: POST /search/query with entityTypes=chatMessage
    return not_implemented_response("search_channel_messages", "POST /search/query with entityTypes=chatMessage")


async def summarize_channel_activity(team_id: str, channel_id: str, days: int = 7) -> dict:
    # TODO: GET /teams/{id}/channels/{id}/messages with date filter, aggregate counts
    return not_implemented_response("summarize_channel_activity", "GET /teams/{id}/channels/{id}/messages with date filter")
