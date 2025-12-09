import json
import os
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from openai import AzureOpenAI

# 既存のモジュールをインポート（パスは環境に合わせて調整してください）
from app.core.db import get_session
from app.models import AxisAnswer, User
from app.schemas.free_chat import ChatRequest
from app.api.auth import get_current_user

router = APIRouter()

# Azure Clientの初期化
client = AzureOpenAI(
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview"),
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT")
)
DEPLOYMENT_NAME = os.getenv("AZURE_DEPLOYMENT_NAME", "gpt-4o-mini")

@router.post("/chat/advice")
async def chat_advice(
    req: ChatRequest,
    # ↓↓↓ ここからコメントアウト（行頭に # をつける）
    # current_user: User = Depends(get_current_user), 
    # db: AsyncSession = Depends(get_session)
    # ↑↑↑ ここまでコメントアウト
):
    # 1. DB取得処理をコメントアウトし、仮のデータを設定する
    # stmt = ...
    # result = ...
    # answer_record = ...

    # ★仮の事業計画データ（DBから取れたことにする）
    plan_data = {
        "concept": "30代女性向けの隠れ家カフェ",
        "menu": "オーガニックランチ",
        "price": 1500
    }
    
    # ★仮のユーザー名
    user_name = "ゲスト"

    # 2. システムプロンプト (仮の user_name を使うように少し修正)
    system_prompt = f"""
あなたは飲食店開業支援AIです。ユーザーは開業を目指す「{user_name}」さんです。
以下の事業計画データを踏まえて、ユーザーの質問に親身にアドバイスしてください。

【現在の計画データ】
{json.dumps(plan_data, ensure_ascii=False, indent=2)}

回答は簡潔かつ具体的に。
"""

    # 3. Azure OpenAIへリクエスト (ここはそのまま)
    try:
        response = client.chat.completions.create(
            model=os.getenv("AZURE_DEPLOYMENT_NAME", "gpt-4o-mini"), # 念のためgetで
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": req.message}
            ],
            temperature=0.7,
        )
        return {"reply": response.choices[0].message.content}

    except Exception as e:
        print(f"OpenAI Error: {e}")
        raise HTTPException(status_code=500, detail="AIの応答に失敗しました")