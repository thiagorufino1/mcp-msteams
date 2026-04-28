from app.utils.response import not_implemented_response


async def check_known_teams_incidents() -> dict:
    # TODO: GET /admin/serviceAnnouncement/issues?$filter=service eq 'Microsoft Teams'
    # Requires: ServiceHealth.Read.All
    return not_implemented_response("check_known_teams_incidents", "GET /admin/serviceAnnouncement/issues — needs ServiceHealth.Read.All")
