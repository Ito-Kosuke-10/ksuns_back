from typing import List, Optional

from pydantic import BaseModel, Field


class AnswerItem(BaseModel):
    question_code: str = Field(..., min_length=1, description="e.g. q1, q2...")
    values: List[str] = Field(default_factory=list)


class SubmitSimulationRequest(BaseModel):
    answers: List[AnswerItem] = Field(..., min_length=1)
    guest_session_token: Optional[str] = None


class SimulationResultResponse(BaseModel):
    session_id: int
    axis_scores: dict[str, float]
    funds_comment_category: str
    funds_comment_text: str
    store_story_text: str


class AttachUserRequest(BaseModel):
    session_id: int = Field(..., ge=1)
