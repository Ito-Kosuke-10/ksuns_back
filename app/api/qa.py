from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_user
from app.core.db import get_session
from app.schemas.auth import UserInfo
from app.schemas.qa import QAHistoryItem, QAListResponse, QARequest, QAResponse
from app.services.qa import handle_question, list_recent_questions

router = APIRouter(prefix="/qa", tags=["qa"])


@router.post("/messages", response_model=QAResponse)
async def post_question(
    payload: QARequest,
    session: AsyncSession = Depends(get_session),
    current_user: UserInfo = Depends(get_current_user),
) -> QAResponse:
    return await handle_question(
        db=session,
        user_id=current_user.id,
        context_type=payload.context_type,
        axis_code=payload.axis_code,
        question=payload.question,
    )


@router.get("/messages", response_model=QAListResponse)
async def list_questions(
    limit: int = 5,
    session: AsyncSession = Depends(get_session),
    current_user: UserInfo = Depends(get_current_user),
) -> QAListResponse:
    limit = max(1, min(limit, 20))
    items = await list_recent_questions(session, current_user.id, limit)
    return QAListResponse(
        items=[
            QAHistoryItem(
                question=item.question_text,
                answer=item.answer_text,
                axis_code=item.axis_code,
                created_at=item.created_at,
            )
            for item in items
        ]
    )
