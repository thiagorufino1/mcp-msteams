from pydantic import Field

from app.schemas.common import ResponseFormat, ToolParams


class ListTeamChannelsParams(ToolParams):
    team_id: str = Field(min_length=1, description="Teams group ID (UUID)")
    response_format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN)


class ListTeamMembersParams(ToolParams):
    team_id: str = Field(min_length=1, description="Teams group ID (UUID)")
    response_format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN)


class GetTeamOwnersParams(ToolParams):
    team_id: str = Field(min_length=1, description="Teams group ID (UUID)")
    response_format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN)


class GetTeamSettingsParams(ToolParams):
    team_id: str = Field(min_length=1, description="Teams group ID (UUID)")
    response_format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN)


class GetChannelSettingsParams(ToolParams):
    team_id: str = Field(min_length=1, description="Teams group ID (UUID)")
    channel_id: str = Field(min_length=1, description="Channel ID")
    response_format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN)


class CheckPrivateSharedChannelsParams(ToolParams):
    team_id: str = Field(min_length=1, description="Teams group ID (UUID)")
    response_format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN)


class DetectOrphanedTeamParams(ToolParams):
    team_id: str = Field(min_length=1, description="Teams group ID (UUID)")
    response_format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN)


class DetectTeamWithoutOwnerParams(ToolParams):
    team_id: str = Field(min_length=1, description="Teams group ID (UUID)")
    response_format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN)
