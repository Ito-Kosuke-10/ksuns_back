"""
メニュー軸のAPIスキーマ
"""
from typing import List, Optional

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    """チャットメッセージ"""
    role: str = Field(..., description="'user' または 'assistant'")
    content: str = Field(..., description="メッセージ内容")


class MenuStatusResponse(BaseModel):
    """カードの進捗ステータス"""
    card_id: str
    is_completed: bool
    summary: Optional[str] = None
    chat_history: Optional[List[ChatMessage]] = None


class MenuStatusListResponse(BaseModel):
    """全カードの進捗ステータス一覧"""
    statuses: List[MenuStatusResponse]


class MenuChatRequest(BaseModel):
    """チャット送信リクエスト"""
    card_id: str = Field(..., description="カードID (例: '1')")
    user_message: str = Field(..., description="ユーザーのメッセージ")
    history: List[ChatMessage] = Field(default_factory=list, description="チャット履歴")


class MenuChatResponse(BaseModel):
    """チャット応答"""
    assistant_message: str = Field(..., description="AIの応答")
    history: List[ChatMessage] = Field(..., description="更新されたチャット履歴")


class MenuSummaryRequest(BaseModel):
    """サマリー生成リクエスト"""
    card_id: str = Field(..., description="カードID")
    chat_history: List[ChatMessage] = Field(..., description="チャット履歴")


class MenuSummaryResponse(BaseModel):
    """サマリー生成応答"""
    summary: str = Field(..., description="生成されたサマリー")

