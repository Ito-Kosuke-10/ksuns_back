from dataclasses import asdict

from fastapi import APIRouter, Depends
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_user
from app.core.db import get_session
from app.models.notes import OwnerNote, StoreStory
from app.schemas.auth import UserInfo
from app.schemas.dashboard import (
    AxisSummary,
    DashboardResponse,
    OwnerNoteRequest,
    OwnerNoteResponse,
)
from app.services.detail_questions import (
    calculate_axis_scores,
    calculate_detail_progress,
    fetch_axis_meta,
    fetch_detail_answers,
    pick_next_focus_axis,
    summarize_concept_text,
)

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("", response_model=DashboardResponse)
async def get_dashboard(
    session: AsyncSession = Depends(get_session),
    current_user: UserInfo = Depends(get_current_user),
) -> DashboardResponse:
    axis_meta = await fetch_axis_meta(session)
    answers = await fetch_detail_answers(session, current_user.id)
    axis_scores_raw = await calculate_axis_scores(session, current_user.id, answers, axis_meta)
    axis_scores = [AxisSummary(**asdict(score)) for score in axis_scores_raw]

    story_result = await session.execute(
        select(StoreStory)
        .where(StoreStory.user_id == current_user.id)
        .order_by(desc(StoreStory.created_at))
        .limit(1)
    )
    story = story_result.scalar_one_or_none()

    note_result = await session.execute(
        select(OwnerNote).where(OwnerNote.user_id == current_user.id)
    )
    note = note_result.scalar_one_or_none()

    progress = calculate_detail_progress(answers)
    concept = summarize_concept_text(story.content if story else None)
    next_focus = pick_next_focus_axis(axis_scores_raw)

    return DashboardResponse(
        concept=concept,
        axes=axis_scores,
        detail_progress=progress,
        next_focus=next_focus,
        ok_line=axis_scores[0].ok_line if axis_scores else 5.0,
        growth_zone=axis_scores[0].growth_zone if axis_scores else 6.0,
        owner_note=note.content if note else "",
        latest_store_story=story.content if story else "",
        user_email=current_user.email,
    )


@router.put("/owner-note", response_model=OwnerNoteResponse)
async def upsert_owner_note(
    payload: OwnerNoteRequest,
    session: AsyncSession = Depends(get_session),
    current_user: UserInfo = Depends(get_current_user),
) -> OwnerNoteResponse:
    result = await session.execute(
        select(OwnerNote).where(OwnerNote.user_id == current_user.id)
    )
    note = result.scalar_one_or_none()
    if note:
        note.content = payload.content
    else:
        note = OwnerNote(user_id=current_user.id, content=payload.content)
        session.add(note)
    await session.commit()
    await session.refresh(note)
    return OwnerNoteResponse(owner_note=note.content)
