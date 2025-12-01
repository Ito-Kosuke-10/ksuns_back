from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_user
from app.core.db import get_session
from app.models.axis import PlanningAxis
from app.schemas.auth import UserInfo
from app.schemas.deep_questions import DeepMessage, DeepQuestionRequest, DeepThreadResponse
from app.services.deep_questions import add_message, list_messages

router = APIRouter(prefix="/deep_questions", tags=["deep_questions"])


async def _resolve_axis_code(
    session: AsyncSession, axis_code: str | None
) -> tuple[str, str]:
    result = await session.execute(select(PlanningAxis).order_by(PlanningAxis.display_order))
    axes = list(result.scalars())
    if not axes:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No axes defined")
    if axis_code:
        for axis in axes:
            if axis.code == axis_code:
                return axis.code, axis.name
    axis = axes[0]
    return axis.code, axis.name


@router.get("", response_model=DeepThreadResponse)
async def get_deep_messages(
    axis: str | None = Query(default=None, alias="axis"),
    session: AsyncSession = Depends(get_session),
    current_user: UserInfo = Depends(get_current_user),
) -> DeepThreadResponse:
    axis_code, axis_name = await _resolve_axis_code(session, axis)
    rows = await list_messages(session, current_user.id, axis_code)
    messages = []
    for question, answer in reversed(rows):
        messages.append(
            DeepMessage(role="user", text=question.question_text, created_at=question.created_at)
        )
        if answer:
            messages.append(
                DeepMessage(role="assistant", text=answer.answer_text, created_at=answer.created_at)
            )
    return DeepThreadResponse(axis_code=axis_code, axis_name=axis_name, messages=messages)


@router.post("/messages", response_model=DeepThreadResponse)
async def post_deep_message(
    payload: DeepQuestionRequest,
    session: AsyncSession = Depends(get_session),
    current_user: UserInfo = Depends(get_current_user),
) -> DeepThreadResponse:
    await add_message(session, current_user.id, payload.axis_code, payload.question)
    return await get_deep_messages(axis=payload.axis_code, session=session, current_user=current_user)
