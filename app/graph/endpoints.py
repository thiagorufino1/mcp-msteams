# All URL builders return relative paths (base URL set in client).


def user(upn: str) -> str:
    return f"/users/{upn}"


def user_presence(user_id: str) -> str:
    return f"/communications/presences/{user_id}"


def user_joined_teams(upn: str) -> str:
    return f"/users/{upn}/joinedTeams"


def user_teamwork(upn: str) -> str:
    return f"/users/{upn}/teamwork"


def team(team_id: str) -> str:
    return f"/teams/{team_id}"


def team_channels(team_id: str) -> str:
    return f"/teams/{team_id}/channels"


def team_channel(team_id: str, channel_id: str) -> str:
    return f"/teams/{team_id}/channels/{channel_id}"


def group_members(group_id: str) -> str:
    return f"/groups/{group_id}/members"


def group_owners(group_id: str) -> str:
    return f"/groups/{group_id}/owners"


def call_record(call_id: str) -> str:
    return f"/communications/callRecords/{call_id}"


def call_record_sessions(call_id: str) -> str:
    return f"/communications/callRecords/{call_id}/sessions"
