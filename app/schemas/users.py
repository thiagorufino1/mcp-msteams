from pydantic import Field

from app.schemas.common import ResponseFormat, ToolParams

_UPN_DESC = (
    "User Principal Name — the user's full email address in Azure AD, "
    "e.g. 'alice@contoso.com'. Must include the domain. "
    "Ask the admin for the exact UPN if not provided; use search_user to resolve display names."
)


class GetUserProfileParams(ToolParams):
    upn: str = Field(min_length=1, description=_UPN_DESC)
    response_format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN)


class GetUserPresenceParams(ToolParams):
    upn: str = Field(min_length=1, description=_UPN_DESC)
    response_format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN)


class GetUserOverviewParams(ToolParams):
    upn: str = Field(min_length=1, description=_UPN_DESC)
    response_format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN)


class GetUserAssignedPoliciesParams(ToolParams):
    upn: str = Field(min_length=1, description=_UPN_DESC)
    response_format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN)


class ListUserTeamsParams(ToolParams):
    upn: str = Field(min_length=1, description=_UPN_DESC)
    response_format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN)


class SearchUserParams(ToolParams):
    query: str = Field(
        min_length=1,
        description=(
            "Search query — display name, email prefix, or UPN fragment. "
            "Examples: 'Alice Smith', 'alice', 'alice@contoso'. "
            "Returns up to 10 matching users with their UPNs."
        ),
    )
    response_format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN)
