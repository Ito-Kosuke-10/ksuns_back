from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_user
from app.core.db import get_session
from app.models.axis import AxisScore
from app.models.notes import StoreStory
from app.models.summaries import Summary, SummaryType
from app.schemas.auth import UserInfo
from app.schemas.summaries import SummaryRequest, SummaryResponse
from app.services.ai_client import generate_summary

router = APIRouter(prefix="/summaries", tags=["summaries"])


@router.post("", response_model=SummaryResponse)
async def create_summary(
    payload: SummaryRequest,
    session: AsyncSession = Depends(get_session),
    current_user: UserInfo = Depends(get_current_user),
) -> SummaryResponse:
    axis_scores = await session.execute(
        select(AxisScore).where(AxisScore.user_id == current_user.id).order_by(desc(AxisScore.calculated_at))
    )
    latest_scores = {row.axis.code if row.axis else str(row.axis_id): float(row.score) for row in axis_scores.scalars()}

    story_result = await session.execute(
        select(StoreStory)
        .where(StoreStory.user_id == current_user.id)
        .order_by(desc(StoreStory.created_at))
        .limit(1)
    )
    story = story_result.scalar_one_or_none()

    content = await generate_summary(
        payload.summary_type,
        {"axis_scores": latest_scores, "store_story": story.content if story else ""},
    )
    if not content:
        content = _build_summary_text(payload.summary_type, latest_scores, story.content if story else "")

    summary = Summary(
        user_id=current_user.id,
        summary_type=SummaryType(payload.summary_type),
        content=content,
    )
    session.add(summary)
    await session.commit()
    await session.refresh(summary)

    return SummaryResponse(
        summary_type=payload.summary_type,
        content=summary.content,
        created_at=summary.created_at,
    )


def _build_summary_text(summary_type: str, axis_scores: dict[str, float], story: str) -> str:
    header_map = {
        "family": "家族向けサマリー",
        "staff": "従業員向けサマリー",
        "bank": "銀行向けサマリー",
        "public": "公的機関向けサマリー",
    }
    header = header_map.get(summary_type, "サマリー")
    scores_text = " / ".join(f"{k}: {v}" for k, v in axis_scores.items()) if axis_scores else "スコア未算出"
    return (
        f"{header}\n"
        f"現時点の8軸スコア: {scores_text}\n"
        f"店舗イメージ: {story or '未入力'}\n"
        f"※このテキストは仮生成です。詳細計画に合わせて更新してください。"
    )
