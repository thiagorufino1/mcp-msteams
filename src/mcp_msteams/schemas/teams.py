from typing import Literal

from pydantic import Field

from mcp_msteams.schemas.common import ResponseFormat, ToolParams

_TEAM_ID_DESC = (
    "Microsoft Teams group ID (GUID), e.g. 'a6e52f47-1234-5678-abcd-ef0123456789'. "
    "Obtain from list_user_teams if you only have a display name. "
    "Do NOT pass a team display name — it must be the UUID."
)
_CHANNEL_ID_DESC = (
    "Channel ID, e.g. '19:abc123def456@thread.tacv2'. "
    "Obtain from list_team_channels."
)


class ListTeamChannelsParams(ToolParams):
    team_id: str = Field(min_length=1, description=_TEAM_ID_DESC)
    response_format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN)


class ListTeamMembersParams(ToolParams):
    team_id: str = Field(min_length=1, description=_TEAM_ID_DESC)
    response_format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN)


class GetTeamOwnersParams(ToolParams):
    team_id: str = Field(min_length=1, description=_TEAM_ID_DESC)
    response_format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN)


class GetTeamSettingsParams(ToolParams):
    team_id: str = Field(min_length=1, description=_TEAM_ID_DESC)
    response_format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN)


class GetChannelSettingsParams(ToolParams):
    team_id: str = Field(min_length=1, description=_TEAM_ID_DESC)
    channel_id: str = Field(min_length=1, description=_CHANNEL_ID_DESC)
    response_format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN)


class CheckPrivateSharedChannelsParams(ToolParams):
    team_id: str = Field(min_length=1, description=_TEAM_ID_DESC)
    response_format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN)


class DetectOrphanedTeamParams(ToolParams):
    team_id: str = Field(min_length=1, description=_TEAM_ID_DESC)
    response_format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN)


class DetectTeamWithoutOwnerParams(ToolParams):
    team_id: str = Field(min_length=1, description=_TEAM_ID_DESC)
    response_format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN)


class ListAllTeamsParams(ToolParams):
    top: int = Field(default=20, ge=1, le=100, description="Number of teams per page (max 100).")
    skip: int = Field(default=0, ge=0, description="Number of teams to skip (for pagination).")
    privacy: Literal["Public", "Private"] | None = Field(
        default=None,
        description="Filter by privacy type: 'Public' or 'Private'. Omit for all.",
    )
    include_counts: bool = Field(
        default=True,
        description="Include member and owner counts per team. Slower — makes 2 extra API calls per team.",
    )
    response_format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN)


class GetTenantTeamsStatsParams(ToolParams):
    response_format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN)


class ListOrphanedTeamsParams(ToolParams):
    top: int = Field(default=20, ge=1, le=100, description="Max number of orphaned teams to return.")
    response_format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN)


class ListTeamsWithoutMembersParams(ToolParams):
    top: int = Field(default=20, ge=1, le=100, description="Max number of teams without members to return.")
    response_format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN)


class ListTeamsByMemberCountParams(ToolParams):
    top: int = Field(default=10, ge=1, le=50, description="Number of top teams by member count to return.")
    response_format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN)
