from pydantic import Field

from app.schemas.common import ResponseFormat, ToolParams


class GetCallQualitySummaryParams(ToolParams):
    upn: str = Field(min_length=1, description="User Principal Name")
    days: int = Field(default=7, ge=1, le=30, description="Lookback window in days (1-30)")
    response_format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN)


class DiagnoseCallQualityParams(ToolParams):
    call_id: str = Field(min_length=1, description="Call record ID from Microsoft Graph")
    response_format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN)


class ListFailedCallsParams(ToolParams):
    upn: str = Field(min_length=1, description="User Principal Name")
    days: int = Field(default=7, ge=1, le=30, description="Lookback window in days (1-30)")
    response_format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN)


class ListPoorQualityCallsParams(ToolParams):
    upn: str = Field(min_length=1, description="User Principal Name")
    days: int = Field(default=7, ge=1, le=30, description="Lookback window in days (1-30)")
    response_format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN)
