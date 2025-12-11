"""
深掘り機能（Deep Dive）のAPIスキーマ
"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class DeepDiveCard(BaseModel):
    """深掘りカードの情報"""

    id: str
    title: str
    initial_question: str
    status: str  # "not_started" | "in_progress" | "completed" | "locked"
    summary: Optional[str] = None  # 完了時のサマリー（Noneを明示的に許容）


class DeepDiveStep(BaseModel):
    """深掘りステップの情報"""

    step: int
    step_title: str
    cards: list[DeepDiveCard]


class DeepDiveListResponse(BaseModel):
    """深掘りカード一覧のレスポンス"""

    axis_code: str
    axis_name: str
    steps: list[DeepDiveStep]


class DeepDiveChatMessage(BaseModel):
    """チャットメッセージ"""

    role: str  # "user" | "assistant"
    message: str
    created_at: datetime


class DeepDiveChatResponse(BaseModel):
    """チャット履歴のレスポンス"""

    card_id: str
    card_title: str
    initial_question: str
    messages: list[DeepDiveChatMessage]
    status: str | None = None  # カードのステータス（オプショナル）
    summary: str | None = None  # カードのサマリー（オプショナル）


class DeepDiveChatRequest(BaseModel):
    """チャット送信のリクエスト"""

    message: str = Field(..., min_length=1, max_length=2000)


class DeepDiveCompleteResponse(BaseModel):
    """カード完了処理のレスポンス"""

    card_id: str
    status: str
    summary: str | None = None

