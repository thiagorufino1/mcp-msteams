from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta, timezone
from typing import Any

from mcp_msteams.graph import endpoints
from mcp_msteams.graph.client import graph_get_all
from mcp_msteams.security.permissions import SCOPES


def _message_author_name(message: dict[str, Any]) -> str:
    from_user = (((message.get("from") or {}).get("user")) or {})
    return from_user.get("displayName") or from_user.get("id") or "Unknown"


def _message_text(message: dict[str, Any]) -> str:
    body = message.get("body") or {}
    return str(body.get("content") or "").strip()


def _message_datetime(message: dict[str, Any]) -> datetime | None:
    value = message.get("createdDateTime")
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


async def get_recent_channel_messages(team_id: str, channel_id: str, count: int = 20) -> dict[str, Any]:
    data = await graph_get_all(
        endpoints.team_channel_messages(team_id, channel_id),
        scopes=SCOPES["channel_read"],
        params={"$top": str(count)},
        max_pages=1,
    )
    messages = data[:count]
    lines = [f"## Recent Channel Messages: {channel_id} ({len(messages)} returned)"]
    for message in messages:
        author = _message_author_name(message)
        text = _message_text(message)[:120] or "<no text>"
        lines.append(f"- **{author}** | {message.get('createdDateTime', '?')} | {text}")
    return {
        "team_id": team_id,
        "channel_id": channel_id,
        "messages": messages,
        "count": len(messages),
        "markdown": "\n".join(lines),
    }


async def search_channel_messages(team_id: str, channel_id: str, query: str) -> dict[str, Any]:
    # Graph channel messages API supports listing, but not scoped full-text search.
    # We fetch the recent channel message set and filter locally as a pragmatic fallback.
    data = await graph_get_all(
        endpoints.team_channel_messages(team_id, channel_id),
        scopes=SCOPES["channel_read"],
        params={"$top": "50"},
        max_pages=5,
    )
    normalized_query = query.lower()
    matches = [
        message for message in data
        if normalized_query in _message_text(message).lower()
    ]
    lines = [f"## Channel Message Search: '{query}' ({len(matches)} matches)"]
    for message in matches[:20]:
        author = _message_author_name(message)
        text = _message_text(message)[:120] or "<no text>"
        lines.append(f"- **{author}** | {message.get('createdDateTime', '?')} | {text}")
    if len(matches) > 20:
        lines.append(f"- ...and {len(matches) - 20} more")
    return {
        "team_id": team_id,
        "channel_id": channel_id,
        "query": query,
        "matches": matches,
        "count": len(matches),
        "search_method": "local_filter_recent_messages",
        "markdown": "\n".join(lines),
    }


async def summarize_channel_activity(team_id: str, channel_id: str, days: int = 7) -> dict[str, Any]:
    data = await graph_get_all(
        endpoints.team_channel_messages(team_id, channel_id),
        scopes=SCOPES["channel_read"],
        params={"$top": "50"},
        max_pages=10,
    )
    cutoff = datetime.now(tz=timezone.utc) - timedelta(days=days)
    recent_messages = []
    for message in data:
        message_dt = _message_datetime(message)
        if message_dt and message_dt >= cutoff:
            recent_messages.append(message)

    authors = Counter(_message_author_name(message) for message in recent_messages)
    lines = [f"## Channel Activity Summary: {channel_id} (last {days} days)"]
    lines.append(f"- **Messages analyzed:** {len(recent_messages)}")
    lines.append(f"- **Unique authors:** {len(authors)}")
    for author, message_count in authors.most_common(10):
        lines.append(f"- **{author}:** {message_count}")
    return {
        "team_id": team_id,
        "channel_id": channel_id,
        "days": days,
        "message_count": len(recent_messages),
        "unique_authors": len(authors),
        "top_authors": [{"author": author, "count": count} for author, count in authors.most_common(10)],
        "messages": recent_messages,
        "markdown": "\n".join(lines),
    }
