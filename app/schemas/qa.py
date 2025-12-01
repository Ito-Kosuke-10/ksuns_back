from datetime import datetime

from pydantic import BaseModel, Field


class QARequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000)
    context_type: str = Field("global", pattern="^(global|axis)$")
    axis_code: str | None = None


class QAResponse(BaseModel):
    reply: str


class QAHistoryItem(BaseModel):
    question: str
    answer: str
    axis_code: str | None = None
    created_at: datetime


class QAListResponse(BaseModel):
    items: list[QAHistoryItem]
