"""
立地軸の質問カードAPI
"""
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from openai.types.chat import ChatCompletionMessageParam

from app.api.auth import get_current_user
from app.config.location_questions import LOCATION_QUESTIONS
from app.core.db import get_session
from app.models.location_answer import LocationAnswer
from app.schemas.auth import UserInfo
from app.schemas.location import (
    ChatMessage,
    LocationChatRequest,
    LocationChatResponse,
    LocationStatusListResponse,
    LocationStatusResponse,
    LocationSummaryRequest,
    LocationSummaryResponse,
)
from app.services.ai_client import _chat_completion

router = APIRouter(prefix="/api/location", tags=["location"])


@router.get("/status", response_model=LocationStatusListResponse)
async def get_location_status(
    current_user: UserInfo = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> LocationStatusListResponse:
    """ユーザーの全カードの進捗（完了フラグ、サマリー）を返却"""
    try:
        result = await session.execute(
            select(LocationAnswer).where(LocationAnswer.user_id == current_user.id)
        )
        answers = result.scalars().all()
    except Exception as e:
        # テーブルが存在しない場合など、DBエラーが発生した場合は空のリストを返す
        print(f"⚠️ location_answersテーブルへのアクセスエラー: {e}")
        print("💡 テーブルが存在しない可能性があります。create_location_answers_table.py を実行してください。")
        answers = []
    
    # カードIDをキーにした辞書を作成
    answer_dict = {answer.card_id: answer for answer in answers}
    
    # 全カードIDに対してステータスを構築
    statuses: List[LocationStatusResponse] = []
    for card_id in LOCATION_QUESTIONS.keys():
        answer = answer_dict.get(card_id)
        # chat_historyをChatMessageのリストに変換
        chat_history = None
        if answer and answer.chat_history:
            chat_history = [
                ChatMessage(role=msg.get("role", ""), content=msg.get("content", ""))
                for msg in answer.chat_history
            ]
        statuses.append(
            LocationStatusResponse(
                card_id=card_id,
                is_completed=answer.is_completed if answer else False,
                summary=answer.summary if answer else None,
                chat_history=chat_history,
            )
        )
    
    return LocationStatusListResponse(statuses=statuses)


@router.post("/chat", response_model=LocationChatResponse)
async def post_location_chat(
    request: LocationChatRequest,
    current_user: UserInfo = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> LocationChatResponse:
    """指定されたカードの「AI質問」に基づきOpenAIと会話する"""
    # カードIDの存在確認
    if request.card_id not in LOCATION_QUESTIONS:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Card ID '{request.card_id}' not found",
        )
    
    card_data = LOCATION_QUESTIONS[request.card_id]
    initial_question = card_data["initial_question"]
    
    # チャット履歴を構築
    messages: List[ChatCompletionMessageParam] = []
    
    # システムプロンプト
    system_prompt = (
        "あなたは飲食店開業を支援する立地選定の専門家です。"
        "ユーザーと対話しながら、立地選定の各項目を確定していきます。"
        "エリア分析、競合調査、リスク評価など、具体的で実用的なアドバイスを提供してください。"
        "回答は簡潔に、1〜2文程度で返してください。"
    )
    messages.append({"role": "system", "content": system_prompt})
    
    # 初回の場合、初期質問を追加
    if not request.history:
        messages.append({"role": "assistant", "content": initial_question})
    
    # 既存の履歴を追加
    for msg in request.history:
        messages.append({"role": msg.role, "content": msg.content})
    
    # ユーザーのメッセージを追加
    messages.append({"role": "user", "content": request.user_message})
    
    # OpenAI APIを呼び出し
    try:
        assistant_response = await _chat_completion(messages, max_tokens=2000)
    except Exception as e:
        print(f"🔥 OpenAI API呼び出しエラー: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"AI API呼び出しに失敗しました: {str(e)}",
        )
    
    if not assistant_response:
        print("🔥 OpenAI APIからの応答が空です")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="AIからの応答が空でした。時間をおいて再試行してください。",
        )
    
    # 履歴を更新
    updated_history = request.history.copy()
    updated_history.append(ChatMessage(role="user", content=request.user_message))
    updated_history.append(ChatMessage(role="assistant", content=assistant_response))
    
    # DBに保存（既存のレコードがあれば更新、なければ作成）
    # テーブルが存在しない場合でもAIの応答は返す（保存はスキップ）
    try:
        result = await session.execute(
            select(LocationAnswer).where(
                LocationAnswer.user_id == current_user.id,
                LocationAnswer.card_id == request.card_id,
            )
        )
        answer = result.scalar_one_or_none()
        
        # 履歴をJSON形式に変換
        history_json = [{"role": msg.role, "content": msg.content} for msg in updated_history]
        
        if answer:
            answer.chat_history = history_json
        else:
            answer = LocationAnswer(
                user_id=current_user.id,
                card_id=request.card_id,
                chat_history=history_json,
            )
            session.add(answer)
        
        await session.commit()
    except Exception as e:
        # テーブルが存在しない場合やDB接続エラーの場合
        error_msg = str(e)
        if "doesn't exist" in error_msg or "Table" in error_msg or "Can't connect" in error_msg:
            print(f"⚠️ データベースエラー（チャット履歴は保存されません）: {e}")
            print("💡 ローカル開発環境では、テーブルが存在しない場合でもAIの応答は返されます。")
            print("💡 テーブルを作成するには: python create_location_answers_table.py")
            # エラーを返さず、AIの応答だけを返す（履歴は保存されない）
        else:
            # その他のエラーは再スロー
            raise
    
    return LocationChatResponse(
        assistant_message=assistant_response,
        history=updated_history,
    )


@router.post("/summary", response_model=LocationSummaryResponse)
async def post_location_summary(
    request: LocationSummaryRequest,
    current_user: UserInfo = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> LocationSummaryResponse:
    """会話内容を要約してDBに保存し、完了フラグをTrueにする"""
    # カードIDの存在確認
    if request.card_id not in LOCATION_QUESTIONS:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Card ID '{request.card_id}' not found",
        )
    
    card_data = LOCATION_QUESTIONS[request.card_id]
    card_title = card_data["title"]
    
    # チャット履歴をテキストに変換
    chat_text = "\n".join(
        [f"{msg.role}: {msg.content}" for msg in request.chat_history]
    )
    
    # サマリー生成のプロンプト
    prompt = (
        f"あなたは飲食店開業の立地選定の専門家です。"
        f"以下の会話内容を基に、『{card_title}』についての要約を200〜300文字で作成してください。"
        "【重要】"
        "・決定した内容や選択肢を明確に記載してください。"
        "・ユーザーの考えや意図を正確に反映してください。"
        "・具体的で実用的な内容にしてください。"
        "・前向きなトーンを保ってください。"
    )
    
    messages: List[ChatCompletionMessageParam] = [
        {"role": "system", "content": prompt},
        {"role": "user", "content": f"会話内容:\n{chat_text}"},
    ]
    
    try:
        summary = await _chat_completion(messages, max_tokens=2000)
    except Exception as e:
        print(f"🔥 サマリー生成API呼び出しエラー: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"サマリー生成に失敗しました: {str(e)}",
        )
    
    if not summary:
        print("🔥 サマリー生成APIからの応答が空です")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="サマリーの生成に失敗しました。時間をおいて再試行してください。",
        )
    
    # DBに保存（既存のレコードがあれば更新、なければ作成）
    # テーブルが存在しない場合でもサマリーは返す（保存はスキップ）
    try:
        result = await session.execute(
            select(LocationAnswer).where(
                LocationAnswer.user_id == current_user.id,
                LocationAnswer.card_id == request.card_id,
            )
        )
        answer = result.scalar_one_or_none()
        
        # 履歴をJSON形式に変換
        history_json = [{"role": msg.role, "content": msg.content} for msg in request.chat_history]
        
        if answer:
            answer.chat_history = history_json
            answer.summary = summary
            answer.is_completed = True
        else:
            answer = LocationAnswer(
                user_id=current_user.id,
                card_id=request.card_id,
                chat_history=history_json,
                summary=summary,
                is_completed=True,
            )
            session.add(answer)
        
        await session.commit()
    except Exception as e:
        # テーブルが存在しない場合やDB接続エラーの場合
        error_msg = str(e)
        if "doesn't exist" in error_msg or "Table" in error_msg or "Can't connect" in error_msg:
            print(f"⚠️ データベースエラー（サマリーは保存されません）: {e}")
            print("💡 ローカル開発環境では、テーブルが存在しない場合でもサマリーは返されます。")
            print("💡 テーブルを作成するには: python create_location_answers_table.py")
            # エラーを返さず、サマリーだけを返す（保存はされない）
        else:
            # その他のエラーは再スロー
            raise
    
    return LocationSummaryResponse(summary=summary)

