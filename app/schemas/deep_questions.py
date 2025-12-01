from datetime import datetime

from pydantic import BaseModel, Field


class DeepMessage(BaseModel):
    role: str
    text: str
    created_at: datetime


class DeepThreadResponse(BaseModel):
    axis_code: str
    axis_name: str
    messages: list[DeepMessage]


class DeepQuestionRequest(BaseModel):
    axis_code: str = Field(..., min_length=1, max_length=64)
    question: str = Field(..., min_length=1, max_length=2000)
