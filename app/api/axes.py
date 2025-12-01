from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_user
from app.core.db import get_session
from app.models.axis import AxisAnswer, AxisScore, AxisStep, PlanningAxis
from app.schemas.auth import UserInfo
from app.schemas.axes import (
    AxisDetailResponse,
    AxisListResponse,
    AxisUpdateRequest,
)

router = APIRouter(prefix="/axes", tags=["axes"])


@router.get("", response_model=AxisListResponse)
async def list_axes(
    session: AsyncSession = Depends(get_session),
    current_user: UserInfo = Depends(get_current_user),
) -> AxisListResponse:
    axes_result = await session.execute(select(PlanningAxis))
    steps_result = await session.execute(select(AxisStep))
    axes = axes_result.scalars().all()
    steps = steps_result.scalars().all()

    axis_steps_map: dict[int, list[AxisStep]] = {}
    for step in steps:
        axis_steps_map.setdefault(step.axis_id, []).append(step)

    items = []
    for axis in axes:
        items.append(
            {
                "code": axis.code,
                "name": axis.name,
                "description": axis.description or "",
                "steps": [
                    {
                        "level": s.level,
                        "code": s.code,
                        "title": s.title,
                        "description": s.description or "",
                        "display_order": s.display_order,
                    }
                    for s in sorted(axis_steps_map.get(axis.id, []), key=lambda x: x.display_order)
                ],
            }
        )
    return AxisListResponse(axes=items)


@router.get("/{axis_code}", response_model=AxisDetailResponse)
async def get_axis_detail(
    axis_code: str,
    session: AsyncSession = Depends(get_session),
    current_user: UserInfo = Depends(get_current_user),
) -> AxisDetailResponse:
    axis_result = await session.execute(select(PlanningAxis).where(PlanningAxis.code == axis_code))
    axis = axis_result.scalar_one_or_none()
    if not axis:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Axis not found")

    score_result = await session.execute(
        select(AxisScore)
        .where(AxisScore.axis_id == axis.id, AxisScore.user_id == current_user.id)
        .order_by(AxisScore.calculated_at.desc())
    )
    score_row = score_result.scalars().first()

    answer_result = await session.execute(
        select(AxisAnswer).where(AxisAnswer.axis_id == axis.id, AxisAnswer.user_id == current_user.id)
    )
    answers = answer_result.scalars().all()

    feedback = _generate_feedback(score_row.score if score_row else 0.0)

    return AxisDetailResponse(
        code=axis.code,
        name=axis.name,
        score=float(score_row.score) if score_row else 0.0,
        answers={f"level_{ans.level}": ans.answers_json for ans in answers},
        feedback=feedback,
    )


@router.put("/{axis_code}/answers", response_model=AxisDetailResponse)
async def update_axis_answers(
    axis_code: str,
    payload: AxisUpdateRequest,
    session: AsyncSession = Depends(get_session),
    current_user: UserInfo = Depends(get_current_user),
) -> AxisDetailResponse:
    axis_result = await session.execute(select(PlanningAxis).where(PlanningAxis.code == axis_code))
    axis = axis_result.scalar_one_or_none()
    if not axis:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Axis not found")

    answer_result = await session.execute(
        select(AxisAnswer).where(
            AxisAnswer.axis_id == axis.id,
            AxisAnswer.user_id == current_user.id,
            AxisAnswer.level == payload.level,
        )
    )
    existing = answer_result.scalar_one_or_none()
    if existing:
        existing.answers_json = payload.answers
    else:
        session.add(
            AxisAnswer(
                user_id=current_user.id,
                axis_id=axis.id,
                level=payload.level,
                answers_json=payload.answers,
            )
        )
    await session.commit()

    # Reload answers
    answer_result = await session.execute(
        select(AxisAnswer).where(AxisAnswer.axis_id == axis.id, AxisAnswer.user_id == current_user.id)
    )
    answers = answer_result.scalars().all()
    score_value = _recalculate_score(answers)
    score_row = await session.execute(
        select(AxisScore)
        .where(AxisScore.axis_id == axis.id, AxisScore.user_id == current_user.id)
        .order_by(AxisScore.calculated_at.desc())
    )
    score = score_row.scalars().first()
    if score:
        score.score = score_value
    else:
        session.add(
            AxisScore(
                user_id=current_user.id,
                axis_id=axis.id,
                score=score_value,
                level1_completion_ratio=0,
                level2_completion_ratio=0,
            )
        )
    await session.commit()

    feedback = _generate_feedback(score_value)

    return AxisDetailResponse(
        code=axis.code,
        name=axis.name,
        score=score_value,
        answers={f"level_{ans.level}": ans.answers_json for ans in answers},
        feedback=feedback,
    )


def _generate_feedback(score: float) -> str:
    if score >= 5:
        return "OKラインに達しています。次は成長ゾーンの計画を検討しましょう。"
    if score >= 3:
        return "方向性は見えています。数字や具体策を足して5点を目指しましょう。"
    return "まだ余白があります。基本的な方針と初期の具体案を整理していきましょう。"


def _recalculate_score(answers: list[AxisAnswer]) -> float:
    # Very simple heuristic: level1 answered => 3点、level2 answered => 5点
    levels = {a.level for a in answers}
    if 2 in levels:
        return 5.0
    if 1 in levels:
        return 3.5
    return 0.0
