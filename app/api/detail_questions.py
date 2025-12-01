from dataclasses import asdict

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_user
from app.core.db import get_session
from app.schemas.auth import UserInfo
from app.schemas.dashboard import AxisSummary
from app.schemas.detail_questions import (
    DetailQuestion,
    DetailQuestionsResponse,
    DetailQuestionsUpdateRequest,
    DetailQuestionsUpdateResponse,
)
from app.services.detail_questions import (
    calculate_axis_scores,
    calculate_detail_progress,
    fetch_axis_meta,
    fetch_detail_answers,
    get_detail_questions as get_detail_question_defs,
    pick_next_focus_axis,
    save_detail_answers,
)

router = APIRouter(prefix="/detail_questions", tags=["detail_questions"])


@router.get("", response_model=DetailQuestionsResponse)
async def get_detail_questions(
    session: AsyncSession = Depends(get_session),
    current_user: UserInfo = Depends(get_current_user),
) -> DetailQuestionsResponse:
    questions = get_detail_question_defs()
    answers = await fetch_detail_answers(session, current_user.id)
    progress = calculate_detail_progress(answers)
    all_codes = [q["code"] for q in questions]
    filled_answers = {code: answers.get(code) for code in all_codes}

    return DetailQuestionsResponse(
        questions=[DetailQuestion(**q) for q in questions],
        answers=filled_answers,
        progress=progress,
    )


@router.put("", response_model=DetailQuestionsUpdateResponse)
async def update_detail_questions(
    payload: DetailQuestionsUpdateRequest,
    session: AsyncSession = Depends(get_session),
    current_user: UserInfo = Depends(get_current_user),
) -> DetailQuestionsUpdateResponse:
    try:
        await save_detail_answers(session, current_user.id, payload.answers)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    answers = await fetch_detail_answers(session, current_user.id)
    axis_meta = await fetch_axis_meta(session)
    axis_scores_raw = await calculate_axis_scores(session, current_user.id, answers, axis_meta)
    axis_scores = [AxisSummary(**asdict(score)) for score in axis_scores_raw]

    return DetailQuestionsUpdateResponse(
        progress=calculate_detail_progress(answers),
        axis_scores=axis_scores,
        next_focus=pick_next_focus_axis(axis_scores_raw),
    )
