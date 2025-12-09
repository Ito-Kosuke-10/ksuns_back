from pydantic import BaseModel

class ChatRequest(BaseModel):
    message: str          # ユーザーの質問
    # まだセッションID管理が完全でない可能性があるため、
    # 一旦は「ログイン中のユーザー」を自動判別する形で作ります。
    # 必要なら session_id: str を追加します