from urllib.parse import quote


def _seg(value: str) -> str:
    return quote(value, safe="")


def user(upn: str) -> str:
    return f"/users/{_seg(upn)}"


def user_presence(user_id: str) -> str:
    return f"/users/{_seg(user_id)}/presence"


def user_joined_teams(upn: str) -> str:
    return f"/users/{_seg(upn)}/joinedTeams"


def user_teamwork(upn: str) -> str:
    return f"/users/{_seg(upn)}/teamwork"


def teams_user_configurations() -> str:
    return "/admin/teams/userConfigurations"


def team_channel_messages(team_id: str, channel_id: str) -> str:
    return f"/teams/{_seg(team_id)}/channels/{_seg(channel_id)}/messages"


def user_registered_devices(upn: str) -> str:
    return f"/users/{_seg(upn)}/registeredDevices"


def device(device_id: str) -> str:
    return f"/devices/{_seg(device_id)}"


def user_online_meetings(upn: str) -> str:
    return f"/users/{_seg(upn)}/onlineMeetings"


def user_online_meeting(upn: str, meeting_id: str) -> str:
    return f"/users/{_seg(upn)}/onlineMeetings/{_seg(meeting_id)}"


def user_online_meeting_attendance_reports(upn: str, meeting_id: str) -> str:
    return f"/users/{_seg(upn)}/onlineMeetings/{_seg(meeting_id)}/attendanceReports"


def user_online_meeting_attendance_records(upn: str, meeting_id: str, report_id: str) -> str:
    return f"/users/{_seg(upn)}/onlineMeetings/{_seg(meeting_id)}/attendanceReports/{_seg(report_id)}/attendanceRecords"


def service_announcement_issues() -> str:
    return "/admin/serviceAnnouncement/issues"


def team(team_id: str) -> str:
    return f"/teams/{_seg(team_id)}"


def team_channels(team_id: str) -> str:
    return f"/teams/{_seg(team_id)}/channels"


def team_members(team_id: str) -> str:
    return f"/teams/{_seg(team_id)}/members"


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


def groups_count() -> str:
    return "/groups/$count"


def group_members_count(group_id: str) -> str:
    return f"/groups/{_seg(group_id)}/members/$count"


def group_owners_count(group_id: str) -> str:
    return f"/groups/{_seg(group_id)}/owners/$count"
