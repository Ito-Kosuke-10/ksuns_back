"""
収支予測軸のAPIスキーマ
"""
from typing import List, Optional

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    """チャットメッセージ"""
    role: str = Field(..., description="'user' または 'assistant'")
    content: str = Field(..., description="メッセージ内容")


class RevenueForecastStatusResponse(BaseModel):
    """カードの進捗ステータス"""
    card_id: str
    is_completed: bool
    summary: Optional[str] = None
    chat_history: Optional[List[ChatMessage]] = None


class RevenueForecastStatusListResponse(BaseModel):
    """全カードの進捗ステータス一覧"""
    statuses: List[RevenueForecastStatusResponse]


class RevenueForecastChatRequest(BaseModel):
    """チャット送信リクエスト"""
    card_id: str = Field(..., description="カードID (例: '1')")
    user_message: str = Field(..., description="ユーザーのメッセージ")
    history: List[ChatMessage] = Field(default_factory=list, description="チャット履歴")


class RevenueForecastChatResponse(BaseModel):
    """チャット応答"""
    assistant_message: str = Field(..., description="AIの応答")
    history: List[ChatMessage] = Field(..., description="更新されたチャット履歴")


class RevenueForecastSummaryRequest(BaseModel):
    """サマリー生成リクエスト"""
    card_id: str = Field(..., description="カードID")
    chat_history: List[ChatMessage] = Field(..., description="チャット履歴")


class RevenueForecastSummaryResponse(BaseModel):
    """サマリー生成応答"""
    summary: str = Field(..., description="生成されたサマリー")

