from pydantic import Field

from app.schemas.common import ResponseFormat, ToolParams


class GetUserProfileParams(ToolParams):
    upn: str = Field(min_length=1, description="User Principal Name, e.g. alice@contoso.com")
    response_format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN)


class GetUserPresenceParams(ToolParams):
    upn: str = Field(min_length=1, description="User Principal Name")
    response_format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN)


class GetUserOverviewParams(ToolParams):
    upn: str = Field(min_length=1, description="User Principal Name")
    response_format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN)


class GetUserAssignedPoliciesParams(ToolParams):
    upn: str = Field(min_length=1, description="User Principal Name")
    response_format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN)


class ListUserTeamsParams(ToolParams):
    upn: str = Field(min_length=1, description="User Principal Name")
    response_format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN)
