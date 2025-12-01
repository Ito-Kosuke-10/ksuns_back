from datetime import datetime

from pydantic import BaseModel, Field


class SummaryRequest(BaseModel):
    summary_type: str = Field(..., pattern="^(family|staff|bank|public)$")


class SummaryResponse(BaseModel):
    summary_type: str
    content: str
    created_at: datetime
