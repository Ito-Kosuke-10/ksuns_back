from pydantic import BaseModel, Field

from app.schemas.dashboard import AxisSummary, DetailProgress, NextFocus


class DetailQuestion(BaseModel):
    code: str
    axis_code: str
    axis_label: str
    text: str


class DetailQuestionsResponse(BaseModel):
    questions: list[DetailQuestion]
    answers: dict[str, bool | None]
    progress: DetailProgress


class DetailQuestionsUpdateRequest(BaseModel):
    answers: dict[str, bool | None] = Field(default_factory=dict)


class DetailQuestionsUpdateResponse(BaseModel):
    progress: DetailProgress
    axis_scores: list[AxisSummary]
    next_focus: NextFocus | None = None
