from pydantic import BaseModel, Field


class ConceptSummary(BaseModel):
    title: str
    description: str


class AxisSummary(BaseModel):
    code: str
    name: str
    score: float
    ok_line: float
    growth_zone: float
    comment: str
    next_step: str
    answered: int
    total_questions: int
    missing: int


class DetailProgress(BaseModel):
    answered: int = Field(..., ge=0)
    total: int = Field(..., ge=0)


class NextFocus(BaseModel):
    axis_code: str
    axis_name: str
    reason: str
    message: str


class DashboardResponse(BaseModel):
    concept: ConceptSummary
    axes: list[AxisSummary]
    detail_progress: DetailProgress
    next_focus: NextFocus | None = None
    ok_line: float = 5.0
    growth_zone: float = 6.0
    owner_note: str = ""
    latest_store_story: str = ""
    user_email: str


class OwnerNoteRequest(BaseModel):
    content: str = Field(..., min_length=1, max_length=4000)


class OwnerNoteResponse(BaseModel):
    owner_note: str
