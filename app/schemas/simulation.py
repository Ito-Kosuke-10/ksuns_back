from typing import List, Optional

from pydantic import BaseModel, Field


class AnswerItem(BaseModel):
    question_code: str = Field(..., min_length=1, description="e.g. main_genre, seats")
    values: List[str] = Field(default_factory=list)


class SubmitSimulationRequest(BaseModel):
    answers: List[AnswerItem] = Field(..., min_length=1)
    guest_session_token: Optional[str] = Field(
        default=None, description="Optional token to identify a guest session (for reuse)"
    )
    plan_id: Optional[int] = Field(
        default=None,
        description="Attach this simulation result to a specific opening plan (logged-in users only)",
    )


class FinancialForecast(BaseModel):
    """Financial forecast data for simulation result."""
    monthly_sales: Optional[int] = None
    estimated_rent: Optional[int] = None
    cost_ratio: Optional[float] = None  # 原価率 (%)
    labor_cost_ratio: Optional[float] = None  # 人件費率 (%)
    profit_ratio: Optional[float] = None  # 利益率 (%)
    break_even_sales: Optional[int] = None  # 損益分岐売上
    funds_comment_category: str
    funds_comment_text: str


class SimulationResultResponse(BaseModel):
    session_id: int
    axis_scores: dict[str, float]
    # コンセプト関連
    concept_name: str  # 例: "駅近のサラリーマン向け大衆居酒屋"
    concept_sub_comment: str  # 20-30文字のサブコメント
    # 収支予想
    financial_forecast: Optional[FinancialForecast] = None
    # 開店にあたっての留意事項
    opening_notes: str
    # 後方互換性のため維持（非推奨）
    funds_comment_category: str = ""
    funds_comment_text: str = ""
    store_story_text: str = ""
    concept_title: str = ""
    concept_detail: str = ""
    funds_summary: str = ""
    monthly_sales: Optional[int] = None


class AttachUserRequest(BaseModel):
    session_id: int = Field(..., ge=1)
