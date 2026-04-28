from mcp_msteams.utils.response import not_implemented_response


async def get_recent_meetings(upn: str, days: int = 7) -> dict:
    # TODO: GET /users/{upn}/onlineMeetings?$filter=startDateTime ge {date}
    # Requires: OnlineMeetings.Read.All
    return not_implemented_response("get_recent_meetings", "GET /users/{upn}/onlineMeetings — needs OnlineMeetings.Read.All")


async def diagnose_meeting_issues(meeting_id: str) -> dict:
    # TODO: GET /users/{upn}/onlineMeetings/{meetingId} + attendanceReports
    return not_implemented_response("diagnose_meeting_issues", "GET /users/{upn}/onlineMeetings/{id} + attendanceReports")
