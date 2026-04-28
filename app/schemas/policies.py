from pydantic import Field

from app.schemas.common import ResponseFormat, ToolParams


class CompareUserPoliciesParams(ToolParams):
    upn1: str = Field(min_length=1, description="First user's UPN")
    upn2: str = Field(min_length=1, description="Second user's UPN to compare against")
    response_format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN)


class DetectPolicyConflictsParams(ToolParams):
    upn: str = Field(min_length=1, description="User Principal Name to check for policy conflicts")
    response_format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN)
