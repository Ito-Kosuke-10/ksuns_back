import json
import os
from fastapi import APIRouter, HTTPException
from openai import AzureOpenAI
from pydantic import BaseModel

class ChatRequest(BaseModel):
    message: str

router = APIRouter()

client = AzureOpenAI(
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    api_version="2024-02-15-preview",
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT")
)

@router.post("/chat/advice")
async def chat_advice(req: ChatRequest):
    
    # ▼▼▼ 1. チャットの言葉に応じて「事業計画データ」を自動切替 ▼▼▼
    
    # デフォルトは「カフェ」
    plan_type = "cafe"
    
    # ワード判定（プラン内容の切り替え）
    if "テラス" in req.message or "海" in req.message:
        plan_type = "terrace"
    elif "バー" in req.message or "酒" in req.message:
        plan_type = "bar"
    else:
        # それ以外はカフェ
        plan_type = "cafe"
    
    # データ定義（3パターンのみ）
    plans = {
        "terrace": {
            "concept": "海沿いの開放的なテラスがあるカフェレストラン。波音を聞きながらリラックスできる空間。",
            "menu": "トロピカルドリンク、シーフードランチ",
            "price": 2000
        },
        "bar": {
            "concept": "こだわりの地酒とカクテルが楽しめる大人のオーセンティックバー。落ち着いた照明のシックな内装。",
            "menu": "オリジナルカクテル、ウイスキー、ドライフルーツ",
            "price": 5000
        },
        "cafe": {
            "concept": "30代女性向けの隠れ家カフェ。木の温もりを感じる北欧風の内装。",
            "menu": "オーガニックランチ、スペシャルティコーヒー",
            "price": 1500
        }
    }
    
    current_plan = plans[plan_type]
    user_name = "ゲスト"
    # ▲▲▲ ここまで ▲▲▲


    # ▼▼▼ 2. 画像の自動選択ロジック ▼▼▼
    image_url = None
    
    # 「内装」「イメージ」「画像」「写真」「見せて」などの言葉があれば画像URLをセット
    triggers = ["内装", "イメージ", "画像", "写真", "見せて"]
    if any(word in req.message for word in triggers):
        print(f"Mock image triggered for: {plan_type}")
        
        if plan_type == "terrace":
            # 指定画像：テラス/海
            image_url = "https://images.unsplash.com/photo-1559339352-11d035aa65de?q=80&w=1000&auto=format&fit=crop"
            
        elif plan_type == "bar":
            # 指定画像：バー/酒
            image_url = "https://images.unsplash.com/photo-1552566626-52f8b828add9?q=80&w=1000&auto=format&fit=crop"
            
        else: # cafe
            # デフォルト：北欧風のおしゃれなカフェ
            image_url = "https://images.unsplash.com/photo-1554118811-1e0d58224f24?q=80&w=1000&auto=format&fit=crop"
    # ▲▲▲ ここまで ▲▲▲


    # ▼▼▼ 3. テキスト回答の生成（ここを修正！） ▼▼▼
    
    # 画像があるかどうかで、AIへの指示をガラッと変えます
    if image_url:
        # 画像がある場合の強力な指示
        instruction_prompt = """
【重要：画像表示中】
現在、ユーザーの画面には、すでにあなたの指示によって「コンセプトに合わせた内装イメージ画像」が表示されています。
したがって、回答の中で以下のように振る舞ってください：

1. 必ず冒頭で「イメージ画像をご用意しました」と断言してください。
2. 「私はAIなので画像は生成できません」「具体的な画像は提供できません」といった否定的な発言は**絶対に禁止**です。
3. まるでその画像を見ながら案内しているかのように、自信を持ってコンセプトを説明してください。
"""
    else:
        # 画像がない場合
        instruction_prompt = "ユーザーの質問に親身に回答してください。"

    system_prompt = f"""
あなたは飲食店開業支援AIです。ユーザーは「{user_name}」さんです。
現在、ユーザーは以下の事業計画を検討しています。

【現在の計画データ】
{json.dumps(current_plan, ensure_ascii=False)}

{instruction_prompt}
"""

    try:
        response = client.chat.completions.create(
            model=os.getenv("AZURE_DEPLOYMENT_NAME", "gpt-4o-mini"),
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": req.message}
            ],
            temperature=0.7,
        )
        ai_message = response.choices[0].message.content
        
        return {
            "reply": ai_message, 
            "image_url": image_url
        }

    except Exception as e:
        print(f"OpenAI Error: {e}")
        raise HTTPException(status_code=500, detail="AIの応答に失敗しました")