"""Simulation service for simple simulation functionality."""
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.simple_simulation import (
    FundsCommentCategory,
    SimpleSimulationAnswer,
    SimpleSimulationResult,
    SimpleSimulationSession,
    SimulationStatus,
)
from app.models.axis import PlanningAxis, AxisScore
from sqlalchemy import delete
from app.schemas.simulation import SimulationResultResponse, SubmitSimulationRequest


# Required fields for store profile
REQUIRED_FIELDS = ["main_genre", "sub_genre", "seats", "price_point", "business_hours", "location"]


def calculate_axis_scores(answers: dict) -> dict[str, float]:
    """Calculate axis scores from simulation answers."""
    scores = {
        "concept": 0.0,
        "funds": 0.0,
        "compliance": 0.0,
        "operation": 0.0,
        "location": 0.0,
        "interior": 0.0,
        "marketing": 0.0,
        "menu": 0.0,
    }

    main_genre = answers.get("main_genre", [])
    if main_genre and main_genre[0] != "undecided_main":
        scores["concept"] = 5.0

    sub_genre = answers.get("sub_genre", [])
    if sub_genre:
        scores["concept"] += 2.5

    seats = answers.get("seats", [])
    if seats:
        scores["operation"] = 5.0

    price_point = answers.get("price_point", [])
    if price_point:
        scores["funds"] = 5.0

    location = answers.get("location", [])
    if location:
        scores["location"] = 5.0

    # Compliance gets minimum 1.0 when zero
    if scores["compliance"] == 0.0:
        scores["compliance"] = 1.0

    return scores


def generate_funds_comment(data: dict) -> tuple[FundsCommentCategory, str, int]:
    """Generate funds comment based on store profile data."""
    seats = data.get("seats", 0)
    price_point = data.get("price_point", 0)

    if isinstance(seats, str):
        seats = int(seats) if seats.isdigit() else 0
    if isinstance(price_point, str):
        price_point = int(price_point) if price_point.isdigit() else 0

    # Calculate monthly revenue estimate
    monthly_revenue = int(seats * price_point * 30 * 0.7)  # 70% occupancy

    if monthly_revenue > 5000000:  # > 500万
        category = FundsCommentCategory.RELAXED
        text = "資金計画に余裕があります。"
    elif monthly_revenue > 2000000:  # > 200万
        category = FundsCommentCategory.TIGHT
        text = "資金計画は標準的です。計画的な運営が必要です。"
    else:
        category = FundsCommentCategory.TIGHT
        text = "資金計画に注意が必要です。慎重な運営を心がけてください。"

    return (category, text, monthly_revenue)


def _build_store_profile(answers: dict) -> dict:
    """Build store profile from answers."""
    profile = {}
    for key in REQUIRED_FIELDS:
        value = answers.get(key, [])
        if value:
            profile[key] = value[0] if isinstance(value, list) else value
    return profile


def _find_missing_required(profile: dict) -> list[str]:
    """Find missing required fields in profile."""
    return [key for key in REQUIRED_FIELDS if key not in profile or not profile[key]]


async def ai_generate_store_story(payload: dict) -> Optional[str]:
    """Generate store story using AI. Returns None if AI fails."""
    # AI implementation would go here
    # For now, return None to trigger fallback
    return None


async def generate_store_story(profile: dict) -> str:
    """Generate store story from profile, with fallback if AI fails."""
    ai_story = await ai_generate_store_story(profile)
    if ai_story:
        return ai_story

    # Fallback story generation
    main_genre = profile.get("main_genre", "店舗")
    location = profile.get("location", "")
    seats = profile.get("seats", "")

    return f"{main_genre}として、{location}で{seats}席規模の店舗を計画しています。"


async def _get_axis_id_map(db: AsyncSession) -> dict[str, int]:
    """Get mapping of axis codes to axis IDs."""
    result = await db.execute(select(PlanningAxis))
    axes = result.scalars().all()
    return {axis.code: axis.id for axis in axes}


async def process_simulation_submission(
    db: AsyncSession,
    payload: SubmitSimulationRequest,
    user_id: Optional[int],
) -> SimulationResultResponse:
    """Process simulation submission and return results."""

    # Convert answers to dict
    answers_dict = {item.question_code: item.values for item in payload.answers}

    # Build store profile
    profile = _build_store_profile(answers_dict)

    # Calculate scores
    axis_scores = calculate_axis_scores(answers_dict)

    # Generate funds comment
    funds_category, funds_text, monthly_sales = generate_funds_comment(profile)

    # Generate store story
    store_story = await generate_store_story(profile)

    # If no user and no guest token, return without saving
    if user_id is None and not payload.guest_session_token:
        return SimulationResultResponse(
            session_id=0,
            axis_scores=axis_scores,
            funds_comment_category=funds_category.value,
            funds_comment_text=funds_text,
            store_story_text=store_story,
            concept_title=profile.get("main_genre", ""),
            concept_detail=profile.get("sub_genre", ""),
            funds_summary=funds_text,
            monthly_sales=monthly_sales,
        )

    # Guest without token - require token
    if user_id is None and payload.guest_session_token == "":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Guest session token is required for saving results",
        )

    # Check if session with same guest_session_token already exists
    session_obj = None
    if payload.guest_session_token:
        result = await db.execute(
            select(SimpleSimulationSession).where(
                SimpleSimulationSession.guest_session_token == payload.guest_session_token
            )
        )
        session_obj = result.scalar_one_or_none()

    if session_obj:
        # Update existing session - delete old answers and result first
        await db.execute(
            delete(SimpleSimulationAnswer).where(
                SimpleSimulationAnswer.session_id == session_obj.id
            )
        )
        await db.execute(
            delete(SimpleSimulationResult).where(
                SimpleSimulationResult.session_id == session_obj.id
            )
        )
        # Update session status
        session_obj.status = SimulationStatus.COMPLETED
        session_obj.user_id = user_id
    else:
        # Create new session
        session_obj = SimpleSimulationSession(
            user_id=user_id,
            guest_session_token=payload.guest_session_token if not user_id else None,
            status=SimulationStatus.COMPLETED,
        )
        db.add(session_obj)
        await db.flush()

    # Save answers
    for item in payload.answers:
        answer = SimpleSimulationAnswer(
            session_id=session_obj.id,
            question_code=item.question_code,
            answer_values={"values": item.values},
        )
        db.add(answer)

    # Save result
    result_obj = SimpleSimulationResult(
        session_id=session_obj.id,
        axis_scores=axis_scores,
        funds_comment_category=funds_category,
        funds_comment_text=funds_text,
        store_story_text=store_story,
    )
    db.add(result_obj)

    # If user is logged in, save axis scores
    if user_id:
        axis_map = await _get_axis_id_map(db)
        for axis_code, score in axis_scores.items():
            if axis_code in axis_map:
                axis_score = AxisScore(
                    user_id=user_id,
                    axis_id=axis_map[axis_code],
                    score=score,
                )
                db.add(axis_score)

    await db.commit()

    return SimulationResultResponse(
        session_id=session_obj.id,
        axis_scores=axis_scores,
        funds_comment_category=funds_category.value,
        funds_comment_text=funds_text,
        store_story_text=store_story,
        concept_title=profile.get("main_genre", ""),
        concept_detail=profile.get("sub_genre", ""),
        funds_summary=funds_text,
        monthly_sales=monthly_sales,
    )


async def attach_session_to_user(
    db: AsyncSession,
    session_id: int,
    user_id: int,
) -> Optional[SimulationResultResponse]:
    """Attach an existing simulation session to a user."""

    # Get session
    result = await db.execute(
        select(SimpleSimulationSession).where(SimpleSimulationSession.id == session_id)
    )
    session_obj = result.scalar_one_or_none()

    if not session_obj:
        return None

    # Update user_id
    session_obj.user_id = user_id

    # Get simulation result
    result = await db.execute(
        select(SimpleSimulationResult).where(SimpleSimulationResult.session_id == session_id)
    )
    sim_result = result.scalar_one_or_none()

    if not sim_result:
        return None

    # Save axis scores for user
    axis_map = await _get_axis_id_map(db)
    for axis_code, score in sim_result.axis_scores.items():
        if axis_code in axis_map:
            axis_score = AxisScore(
                user_id=user_id,
                axis_id=axis_map[axis_code],
                score=score,
            )
            db.add(axis_score)

    await db.commit()

    return SimulationResultResponse(
        session_id=session_id,
        axis_scores=sim_result.axis_scores,
        funds_comment_category=sim_result.funds_comment_category.value,
        funds_comment_text=sim_result.funds_comment_text or "",
        store_story_text=sim_result.store_story_text or "",
        concept_title="",
        concept_detail="",
        funds_summary=sim_result.funds_comment_text or "",
        monthly_sales=None,
    )
