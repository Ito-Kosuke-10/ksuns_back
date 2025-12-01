from pydantic import BaseModel, Field


class AxisListResponse(BaseModel):
    axes: list[dict]


class AxisDetailResponse(BaseModel):
    code: str
    name: str
    score: float
    answers: dict
    feedback: str


class AxisUpdateRequest(BaseModel):
    level: int = Field(..., ge=1, le=2)
    answers: dict
