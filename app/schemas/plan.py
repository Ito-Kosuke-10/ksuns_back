# プラン関連のスキーマ　からちゃん
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


class PlanResponse(BaseModel):
    """単一プランの情報"""

    id: int
    name: str
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True


class PlanListResponse(BaseModel):
    """プラン一覧のレスポンス"""

    plans: List[PlanResponse]


class PlanCreateRequest(BaseModel):
    """新規プラン作成時のリクエスト"""

    # 「別プランを検討する」ボタンからは name を空で投げてもOKにしておく
    name: Optional[str] = None
