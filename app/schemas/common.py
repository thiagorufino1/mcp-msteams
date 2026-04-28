from enum import Enum

from pydantic import BaseModel, ConfigDict


class ResponseFormat(str, Enum):
    JSON = "json"
    MARKDOWN = "markdown"


class ToolParams(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
