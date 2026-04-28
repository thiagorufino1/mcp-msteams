from typing import Any

from pydantic import BaseModel


class CallQualityMetrics(BaseModel):
    call_id: str
    start_time: str
    duration_seconds: int | None = None
    participants: int = 0
    result: str = "unknown"
    failure_reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump()
