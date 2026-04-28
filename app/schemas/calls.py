from pydantic import Field

from app.schemas.common import ResponseFormat, ToolParams

_DAYS_DESC = "Lookback window in days (1–30, default 7). Note: Call Records API may have up to 15 min latency for very recent calls."
_CALL_ID_DESC = (
    "Call record ID from Microsoft Graph. "
    "Obtain from get_call_quality_summary, list_failed_calls, or list_poor_quality_calls "
    "by reading the 'id' field of each record."
)


class GetCallQualitySummaryParams(ToolParams):
    upn: str = Field(min_length=1, description="User Principal Name")
    days: int = Field(default=7, ge=1, le=30, description=_DAYS_DESC)
    response_format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN)


class DiagnoseCallQualityParams(ToolParams):
    call_id: str = Field(min_length=1, description=_CALL_ID_DESC)
    response_format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN)


class ListFailedCallsParams(ToolParams):
    upn: str = Field(min_length=1, description="User Principal Name")
    days: int = Field(default=7, ge=1, le=30, description=_DAYS_DESC)
    response_format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN)


class ListPoorQualityCallsParams(ToolParams):
    upn: str = Field(min_length=1, description="User Principal Name")
    days: int = Field(default=7, ge=1, le=30, description=_DAYS_DESC)
    response_format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN)
