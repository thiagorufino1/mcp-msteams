from urllib.parse import quote


def _seg(value: str) -> str:
    return quote(value, safe="")


def user(upn: str) -> str:
    return f"/users/{_seg(upn)}"


def user_presence(user_id: str) -> str:
    return f"/communications/presences/{_seg(user_id)}"


def user_joined_teams(upn: str) -> str:
    return f"/users/{_seg(upn)}/joinedTeams"


def user_teamwork(upn: str) -> str:
    return f"/users/{_seg(upn)}/teamwork"


def team(team_id: str) -> str:
    return f"/teams/{_seg(team_id)}"


def team_channels(team_id: str) -> str:
    return f"/teams/{_seg(team_id)}/channels"


def team_channel(team_id: str, channel_id: str) -> str:
    return f"/teams/{_seg(team_id)}/channels/{_seg(channel_id)}"


def group_members(group_id: str) -> str:
    return f"/groups/{_seg(group_id)}/members"


def group_owners(group_id: str) -> str:
    return f"/groups/{_seg(group_id)}/owners"


def call_record(call_id: str) -> str:
    return f"/communications/callRecords/{_seg(call_id)}"


def call_record_sessions(call_id: str) -> str:
    return f"/communications/callRecords/{_seg(call_id)}/sessions"
