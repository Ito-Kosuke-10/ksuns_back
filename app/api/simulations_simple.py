import asyncio
import json
import logging
from typing import AsyncGenerator, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_user, get_current_user_optional
from app.core.db import get_session
from app.models.simple_simulation import SimpleSimulationAnswer, SimpleSimulationSession
from app.schemas.auth import UserInfo
from app.schemas.simulation import (
    AttachUserRequest,
    SimulationResultResponse,
    SubmitSimulationRequest,
)
from app.services.ai_client import _chat_completion_stream
from app.services.simulation import (
    MAIN_GENRE_LABELS,
    SUB_GENRE_LABELS,
    LOCATION_LABELS,
    attach_session_to_user,
    process_simulation_submission,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/simulations/simple", tags=["simulations"])


# AI advice generation prompts for each category
ADVICE_PROMPTS = {
    "location": {
        "event_name": "advice_location_delta",
        "system": """あなたは飲食店開業の立地選定の専門家です。
ユーザーの店舗プロファイルに基づいて、立地に関する具体的なアドバイスを提供してください。
200〜300文字程度で、実用的で前向きなアドバイスを日本語で回答してください。""",
    },
    "hr": {
        "event_name": "advice_hr_delta",
        "system": """あなたは飲食店開業の人材採用・オペレーションの専門家です。
ユーザーの店舗プロファイルに基づいて、人材採用とオペレーションに関する具体的なアドバイスを提供してください。
200〜300文字程度で、実用的で前向きなアドバイスを日本語で回答してください。""",
    },
    "menu": {
        "event_name": "advice_menu_delta",
        "system": """あなたは飲食店開業のメニュー開発の専門家です。
ユーザーの店舗プロファイルに基づいて、メニュー構成や価格設定に関する具体的なアドバイスを提供してください。
200〜300文字程度で、実用的で前向きなアドバイスを日本語で回答してください。""",
    },
    "marketing": {
        "event_name": "advice_marketing_delta",
        "system": """あなたは飲食店開業の販促・マーケティングの専門家です。
ユーザーの店舗プロファイルに基づいて、集客やSNS運用に関する具体的なアドバイスを提供してください。
200〜300文字程度で、実用的で前向きなアドバイスを日本語で回答してください。""",
    },
    "funds": {
        "event_name": "advice_funds_delta",
        "system": """あなたは飲食店開業の資金計画の専門家です。
ユーザーの店舗プロファイルに基づいて、資金調達や収支計画に関する具体的なアドバイスを提供してください。
200〜300文字程度で、実用的で前向きなアドバイスを日本語で回答してください。""",
    },
}


@router.post("/result", response_model=SimulationResultResponse)
async def submit_simple_simulation(
    payload: SubmitSimulationRequest,
    session: AsyncSession = Depends(get_session),
    current_user: Optional[UserInfo] = Depends(get_current_user_optional),
) -> SimulationResultResponse:
    return await process_simulation_submission(
        db=session,
        payload=payload,
        user_id=current_user.id if current_user else None,
    )


@router.post("/attach-user", response_model=SimulationResultResponse)
async def attach_user_to_session(
    payload: AttachUserRequest,
    session: AsyncSession = Depends(get_session),
    current_user: UserInfo = Depends(get_current_user),
) -> SimulationResultResponse:
    result = await attach_session_to_user(
        db=session,
        session_id=payload.session_id,
        user_id=current_user.id,
    )
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Simulation session not found"
        )
    return result


async def _get_session_profile(db: AsyncSession, session_id: int) -> dict:
    """Get simulation session profile from database."""
    # Get session
    result = await db.execute(
        select(SimpleSimulationSession).where(SimpleSimulationSession.id == session_id)
    )
    session_obj = result.scalar_one_or_none()
    if not session_obj:
        return {}

    # Get answers
    result = await db.execute(
        select(SimpleSimulationAnswer).where(SimpleSimulationAnswer.session_id == session_id)
    )
    answers = result.scalars().all()

    # Build profile
    profile = {}
    for answer in answers:
        values = answer.answer_values.get("values", [])
        if values:
            profile[answer.question_code] = values[0] if len(values) == 1 else values

    return profile


def _build_profile_description(profile: dict) -> str:
    """Build a human-readable profile description for AI prompts."""
    parts = []

    # Genre
    main_genre = profile.get("main_genre", "")
    sub_genre = profile.get("sub_genre", "")
    genre_label = MAIN_GENRE_LABELS.get(main_genre, main_genre)
    sub_label = SUB_GENRE_LABELS.get(sub_genre, "")
    if sub_label:
        parts.append(f"業態: {sub_label}{genre_label}")
    elif genre_label:
        parts.append(f"業態: {genre_label}")

    # Location
    location = profile.get("location", "")
    location_label = LOCATION_LABELS.get(location, location)
    if location_label:
        parts.append(f"立地: {location_label}")

    # Seats
    seats = profile.get("seats", "")
    if seats:
        parts.append(f"席数: {seats}席")

    # Price point
    price = profile.get("price_point", "")
    if price:
        parts.append(f"客単価: {price}円")

    # Business hours
    hours = profile.get("business_hours", "")
    if hours:
        parts.append(f"営業時間: {hours}")

    return "\n".join(parts) if parts else "情報なし"


async def _generate_advice_stream(
    category: str, profile_desc: str
) -> AsyncGenerator[str, None]:
    """Generate streaming advice for a specific category."""
    prompt_config = ADVICE_PROMPTS.get(category)
    if not prompt_config:
        yield ""
        return

    messages = [
        {"role": "system", "content": prompt_config["system"]},
        {"role": "user", "content": f"以下の店舗プロファイルに基づいてアドバイスをください:\n\n{profile_desc}"},
    ]

    async for chunk in _chat_completion_stream(messages, max_tokens=512):
        yield chunk


async def _event_stream(session_id: int, db: AsyncSession) -> AsyncGenerator[str, None]:
    """Generate SSE event stream for simulation result."""
    try:
        # Get profile from database
        profile = await _get_session_profile(db, session_id)
        if not profile:
            yield f"event: error\ndata: {json.dumps({'error': 'Session not found'})}\n\n"
            return

        profile_desc = _build_profile_description(profile)
        logger.info(f"Generating AI advice for session {session_id}")

        # Generate advice for each category
        for category, config in ADVICE_PROMPTS.items():
            event_name = config["event_name"]
            logger.info(f"Generating {category} advice...")

            async for chunk in _generate_advice_stream(category, profile_desc):
                if chunk:
                    data = json.dumps({"delta": chunk}, ensure_ascii=False)
                    yield f"event: {event_name}\ndata: {data}\n\n"

            # Small delay between categories
            await asyncio.sleep(0.1)

        # Send done event
        yield f"event: done\ndata: {json.dumps({'status': 'completed'})}\n\n"
        logger.info(f"AI advice generation completed for session {session_id}")

    except Exception as e:
        logger.error(f"Error generating AI advice: {e}")
        yield f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"


@router.get("/result-stream")
async def stream_simulation_result(
    session_id: int = Query(..., description="Simulation session ID"),
    db: AsyncSession = Depends(get_session),
) -> StreamingResponse:
    """
    Stream AI-generated advice for simulation result using Server-Sent Events.

    Events:
    - advice_location_delta: Location advice chunks
    - advice_hr_delta: HR/Operation advice chunks
    - advice_menu_delta: Menu advice chunks
    - advice_marketing_delta: Marketing advice chunks
    - advice_funds_delta: Funding advice chunks
    - done: Completion signal
    - error: Error message
    """
    return StreamingResponse(
        _event_stream(session_id, db),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
