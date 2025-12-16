"""
マインドマップ機能のAPI
- SSE認証: 短命ticket方式（ワンタイム・TTL 60秒）
- 新規DBテーブルは作らない（既存*_answersテーブルを使用）
"""
from __future__ import annotations

import json
import logging
import secrets
from datetime import datetime, timedelta
from enum import Enum
from typing import AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_user
from app.config.mindmap_nodes import (
    AXIS_CONFIG,
    VALID_NODE_IDS,
    get_card_title,
    parse_node_id,
)
from app.core.db import get_session
from app.models.concept_answer import ConceptAnswer
from app.models.funding_plan_answer import FundingPlanAnswer
from app.models.interior_exterior_answer import InteriorExteriorAnswer
from app.models.location_answer import LocationAnswer
from app.models.marketing_answer import MarketingAnswer
from app.models.menu_answer import MenuAnswer
from app.models.operation_answer import OperationAnswer
from app.models.revenue_forecast_answer import RevenueForecastAnswer
from app.schemas.auth import UserInfo
from app.services.ai_client import _chat_completion_stream

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/mindmap", tags=["mindmap"])


# ============================================================
# 軸コード → Answerモデル マッピング
# ============================================================
AXIS_ANSWER_MODELS = {
    "concept": ConceptAnswer,
    "revenue_forecast": RevenueForecastAnswer,
    "funds": FundingPlanAnswer,
    "operation": OperationAnswer,
    "location": LocationAnswer,
    "interior_exterior": InteriorExteriorAnswer,
    "marketing": MarketingAnswer,
    "menu": MenuAnswer,
}


# ============================================================
# Ticket管理（メモリ保存）
# ============================================================
_tickets: dict[str, dict] = {}
TICKET_TTL_SECONDS = 60


def _cleanup_expired_tickets() -> None:
    """期限切れticketを削除"""
    now = datetime.utcnow()
    expired = [k for k, v in _tickets.items() if v["expires_at"] < now]
    for k in expired:
        del _tickets[k]


def _create_ticket(user_id: int, node_id: str) -> str:
    """ワンタイムticketを発行"""
    _cleanup_expired_tickets()
    ticket = secrets.token_urlsafe(32)
    _tickets[ticket] = {
        "user_id": user_id,
        "node_id": node_id,
        "expires_at": datetime.utcnow() + timedelta(seconds=TICKET_TTL_SECONDS),
    }
    return ticket


def _validate_ticket(ticket: str, node_id: str) -> int | None:
    """
    ticketを検証し、user_idを返す（検証後は削除 = ワンタイム）

    Returns:
        int | None: 有効な場合はuser_id、無効な場合はNone
    """
    _cleanup_expired_tickets()
    data = _tickets.pop(ticket, None)
    if not data:
        return None
    if data["expires_at"] < datetime.utcnow():
        return None
    if data["node_id"] != node_id:
        return None
    return data["user_id"]


# ============================================================
# Schemas
# ============================================================
class MindmapNodeStatus(str, Enum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


class TicketResponse(BaseModel):
    ticket: str
    expires_in: int


class StatusUpdateRequest(BaseModel):
    status: MindmapNodeStatus


class NodeInfo(BaseModel):
    node_id: str
    name: str
    type: str  # "axis" or "card"
    status: MindmapNodeStatus | None
    summary: str | None = None
    completed_count: int | None = None
    total_count: int | None = None


class AxisScoreInfo(BaseModel):
    axis_code: str
    name: str
    score: float
    completed: int
    total: int


class MindmapStateResponse(BaseModel):
    nodes: list[NodeInfo]
    axis_scores: list[AxisScoreInfo]


class NodeStatusResponse(BaseModel):
    node_id: str
    status: MindmapNodeStatus
    summary: str | None
    updated_at: datetime


# ============================================================
# Helper Functions
# ============================================================
async def _get_answer_model_instance(
    db: AsyncSession, user_id: int, axis_code: str, card_id: str
):
    """指定されたカードの回答レコードを取得"""
    AnswerModel = AXIS_ANSWER_MODELS.get(axis_code)
    if not AnswerModel:
        return None

    result = await db.execute(
        select(AnswerModel).where(
            AnswerModel.user_id == user_id,
            AnswerModel.card_id == card_id,
        )
    )
    return result.scalar_one_or_none()


async def _get_chat_history_from_db(
    db: AsyncSession, user_id: int, node_id: str
) -> list[dict] | None:
    """DBからchat_historyを取得"""
    try:
        axis_code, card_id = parse_node_id(node_id)
    except ValueError:
        return None

    if card_id is None:
        return None  # 軸ノードはサマリー対象外

    answer = await _get_answer_model_instance(db, user_id, axis_code, card_id)
    if answer and answer.chat_history:
        return answer.chat_history
    return None


def _derive_status(answer) -> MindmapNodeStatus:
    """回答レコードからstatusを導出"""
    if answer is None:
        return MindmapNodeStatus.NOT_STARTED
    if answer.is_completed:
        return MindmapNodeStatus.COMPLETED
    if answer.chat_history and len(answer.chat_history) > 0:
        return MindmapNodeStatus.IN_PROGRESS
    return MindmapNodeStatus.NOT_STARTED


# ============================================================
# SSE Stream Generator
# ============================================================
async def _summary_event_stream(
    db: AsyncSession, user_id: int, node_id: str
) -> AsyncGenerator[str, None]:
    """サマリーSSEストリームを生成"""
    try:
        # nodeIdのパース
        try:
            axis_code, card_id = parse_node_id(node_id)
        except ValueError:
            yield f"event: error\ndata: {json.dumps({'error': 'Invalid node_id', 'code': 'INVALID_NODE'})}\n\n"
            return

        if card_id is None:
            yield f"event: error\ndata: {json.dumps({'error': 'Axis node cannot have summary', 'code': 'AXIS_NODE'})}\n\n"
            return

        # chat_history取得
        chat_history = await _get_chat_history_from_db(db, user_id, node_id)
        if not chat_history:
            yield f"event: error\ndata: {json.dumps({'error': 'chat_history not found', 'code': 'NO_HISTORY'})}\n\n"
            return

        # カードタイトル取得
        card_title = get_card_title(node_id) or "項目"

        # チャット履歴をテキスト化
        chat_text = "\n".join(
            f"{msg.get('role', 'unknown')}: {msg.get('content', '')}"
            for msg in chat_history
        )

        # サマリー生成プロンプト
        system_prompt = (
            f"あなたは飲食店開業支援のAIアシスタントです。"
            f"以下の会話内容を基に、『{card_title}』についての要約を200〜300文字で作成してください。"
            "【重要】"
            "・ユーザーの考えや意図を正確に反映してください。"
            "・具体的で実用的な内容にしてください。"
            "・前向きなトーンを保ってください。"
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"会話内容:\n{chat_text}"},
        ]

        # ストリーミング生成
        full_summary = ""
        async for chunk in _chat_completion_stream(messages, max_tokens=512):
            if chunk:
                full_summary += chunk
                data = json.dumps({"delta": chunk}, ensure_ascii=False)
                yield f"event: summary_delta\ndata: {data}\n\n"

        # DB更新: summary保存 & is_completed=True
        AnswerModel = AXIS_ANSWER_MODELS.get(axis_code)
        if AnswerModel:
            result = await db.execute(
                select(AnswerModel).where(
                    AnswerModel.user_id == user_id,
                    AnswerModel.card_id == card_id,
                )
            )
            answer = result.scalar_one_or_none()
            if answer:
                answer.summary = full_summary
                answer.is_completed = True
                await db.commit()
                logger.info(f"Summary saved for node_id={node_id}, user_id={user_id}")

        # done イベント
        done_data = json.dumps({
            "status": "completed",
            "node_id": node_id,
            "summary": full_summary,
        }, ensure_ascii=False)
        yield f"event: done\ndata: {done_data}\n\n"

    except Exception as e:
        logger.error(f"Error generating summary for node_id={node_id}: {e}")
        yield f"event: error\ndata: {json.dumps({'error': str(e), 'code': 'INTERNAL_ERROR'})}\n\n"


# ============================================================
# API Endpoints
# ============================================================

@router.post("/node/{node_id}/summary-ticket", response_model=TicketResponse)
async def create_summary_ticket(
    node_id: str,
    current_user: UserInfo = Depends(get_current_user),
) -> TicketResponse:
    """
    サマリーSSE接続用のワンタイムticketを発行

    - 認証: Bearer 必須
    - TTL: 60秒
    - 1回利用で無効化
    """
    # nodeIdの検証
    if node_id not in VALID_NODE_IDS:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Invalid node_id: {node_id}",
        )

    # 軸ノードはサマリー対象外
    try:
        _, card_id = parse_node_id(node_id)
        if card_id is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Axis node cannot have summary",
            )
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Invalid node_id: {node_id}",
        )

    ticket = _create_ticket(current_user.id, node_id)
    return TicketResponse(ticket=ticket, expires_in=TICKET_TTL_SECONDS)


@router.get("/node/{node_id}/summary-stream")
async def stream_summary(
    node_id: str,
    ticket: str = Query(..., description="ワンタイムticket"),
    db: AsyncSession = Depends(get_session),
) -> StreamingResponse:
    """
    サマリーをSSEでストリーミング生成

    - 認証: ticket（query param）
    - EventSource互換（text/event-stream）

    SSEイベント:
    - summary_delta: チャンク送信
    - done: 完了（summary保存済み）
    - error: エラー
    """
    # ticket検証
    user_id = _validate_ticket(ticket, node_id)
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired ticket",
        )

    return StreamingResponse(
        _summary_event_stream(db, user_id, node_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.put("/node/{node_id}/status", response_model=NodeStatusResponse)
async def update_node_status(
    node_id: str,
    request: StatusUpdateRequest,
    current_user: UserInfo = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
) -> NodeStatusResponse:
    """
    ノードのstatusを更新（未完了に戻す等）

    - 認証: Bearer 必須
    - completed への直接変更は禁止（400）
    - summary は削除しない
    """
    # nodeIdの検証
    if node_id not in VALID_NODE_IDS:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Invalid node_id: {node_id}",
        )

    try:
        axis_code, card_id = parse_node_id(node_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Invalid node_id: {node_id}",
        )

    # 軸ノードはstatus更新対象外
    if card_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Axis node status cannot be updated directly",
        )

    # completed への直接変更は禁止
    if request.status == MindmapNodeStatus.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot directly set status to 'completed'. Use summary-stream endpoint.",
        )

    # 回答レコード取得
    answer = await _get_answer_model_instance(db, current_user.id, axis_code, card_id)

    if answer is None:
        # レコードが存在しない場合、not_startedへの変更は何もしない
        if request.status == MindmapNodeStatus.NOT_STARTED:
            return NodeStatusResponse(
                node_id=node_id,
                status=MindmapNodeStatus.NOT_STARTED,
                summary=None,
                updated_at=datetime.utcnow(),
            )
        # in_progressへの変更も、レコードがなければ意味がない
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Answer record not found for this node",
        )

    # is_completed を更新（summaryは残す）
    if request.status == MindmapNodeStatus.NOT_STARTED:
        answer.is_completed = False
    elif request.status == MindmapNodeStatus.IN_PROGRESS:
        answer.is_completed = False

    await db.commit()
    await db.refresh(answer)

    return NodeStatusResponse(
        node_id=node_id,
        status=_derive_status(answer),
        summary=answer.summary,
        updated_at=answer.updated_at,
    )


@router.get("/state", response_model=MindmapStateResponse)
async def get_mindmap_state(
    current_user: UserInfo = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
) -> MindmapStateResponse:
    """
    マインドマップ表示用の状態一覧＋レーダースコア

    - 認証: Bearer 必須
    - 既存 *_answers を参照して status を導出
    - dashboard と同じ計算式を使用
    """
    nodes: list[NodeInfo] = []
    axis_scores: list[AxisScoreInfo] = []

    for axis_code, config in AXIS_CONFIG.items():
        AnswerModel = AXIS_ANSWER_MODELS.get(axis_code)
        if not AnswerModel:
            continue

        questions = config["questions"]

        # 該当軸の全回答を取得
        result = await db.execute(
            select(AnswerModel).where(AnswerModel.user_id == current_user.id)
        )
        answers = {a.card_id: a for a in result.scalars()}

        completed_count = 0
        card_nodes: list[NodeInfo] = []

        for card_id, q_data in questions.items():
            answer = answers.get(card_id)
            status = _derive_status(answer)

            # dashboardと同じく「回答あり」としてカウント
            if answer and (
                answer.is_completed or
                (answer.chat_history and len(answer.chat_history) > 0) or
                (answer.summary and len(answer.summary) > 0)
            ):
                completed_count += 1

            card_nodes.append(NodeInfo(
                node_id=f"{axis_code}_{card_id}",
                name=q_data["title"],
                type="card",
                status=status,
                summary=answer.summary if answer else None,
            ))

        # 軸ノード（集約）を先頭に追加
        nodes.append(NodeInfo(
            node_id=axis_code,
            name=config["name"],
            type="axis",
            status=None,  # 軸ノード自体にはstatusなし
            completed_count=completed_count,
            total_count=len(questions),
        ))

        # カードノードを追加
        nodes.extend(card_nodes)

        # 軸スコア（dashboardと同じ計算式: answered / total * 10）
        score = round((completed_count / len(questions)) * 10, 1) if questions else 0.0
        axis_scores.append(AxisScoreInfo(
            axis_code=axis_code,
            name=config["name"],
            score=score,
            completed=completed_count,
            total=len(questions),
        ))

    return MindmapStateResponse(nodes=nodes, axis_scores=axis_scores)
