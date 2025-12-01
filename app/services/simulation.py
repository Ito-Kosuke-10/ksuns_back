from datetime import datetime, timedelta
from typing import Dict, Iterable, Optional

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.axis import AxisScore, PlanningAxis
from app.models.notes import StoreStory, StoreStorySource
from app.models.simple_simulation import (
    FundsCommentCategory,
    SimpleSimulationAnswer,
    SimpleSimulationResult,
    SimpleSimulationSession,
    SimulationStatus,
)
from app.schemas.simulation import SubmitSimulationRequest, SimulationResultResponse
from app.services.ai_client import generate_store_story as ai_generate_store_story

AXIS_CODES = [
    "concept",
    "funds",
    "location",
    "menu",
    "equipment",
    "operation",
    "marketing",
    "compliance",
]

# Mapping of question_code to axis contributions
QUESTION_AXIS_MAP: dict[str, list[str]] = {
    "q1": ["concept", "marketing"],
    "q2": ["concept", "marketing"],
    "q3": ["concept", "marketing"],
    "q4": ["concept"],
    "q5": ["funds", "menu"],
    "q6": ["menu"],
    "q7": ["menu"],
    "q8": ["funds", "equipment", "operation"],
    "q9": ["location"],
    "q10": ["equipment", "operation"],
    "q11": ["concept", "marketing"],
    "q12": ["operation", "marketing"],
}

UNKNOWN_PREFIX = "undecided"


def _is_unknown(values: Iterable[str]) -> bool:
    return any(val.startswith(UNKNOWN_PREFIX) for val in values)


def calculate_axis_scores(answers: dict[str, list[str]]) -> dict[str, float]:
    """
    Simple heuristic:
    - For each axis, compute ratio of answered (non-unknown) questions to mapped questions.
    - Score = ratio * 5 (cap at 5.0). Minimum 0.0.
    """
    axis_counts: dict[str, int] = {axis: 0 for axis in AXIS_CODES}
    axis_known: dict[str, int] = {axis: 0 for axis in AXIS_CODES}

    for q_code, axes in QUESTION_AXIS_MAP.items():
        for axis in axes:
            axis_counts[axis] += 1
            values = answers.get(q_code, [])
            if values and not _is_unknown(values):
                axis_known[axis] += 1

    scores: dict[str, float] = {}
    for axis in AXIS_CODES:
        total = axis_counts.get(axis, 1)
        known = axis_known.get(axis, 0)
        ratio = known / total if total else 0
        score = min(5.0, round(ratio * 5, 1))
        scores[axis] = score
    # complianceは第1週でほぼ未着手想定、質問割当が少ないため最低0〜1程度
    if scores.get("compliance") == 0:
        scores["compliance"] = 1.0
    return scores


def generate_funds_comment(
    answers: dict[str, list[str]],
) -> tuple[FundsCommentCategory, str]:
    seats = answers.get("q8", [])
    budget = answers.get("q5", [])
    if seats and any(val in ["41_plus", "two_or_more_shops"] for val in seats):
        return (
            FundsCommentCategory.TIGHT,
            "大きめの席数を想定しているため、初期費用と人件費に注意が必要です。",
        )
    if budget and any(val in ["over_8001", "6001_to_8000"] for val in budget):
        return (
            FundsCommentCategory.RELAXED,
            "客単価が高めの想定なので、席数と回転数次第では余裕のある計画になりそうです。",
        )
    return (
        FundsCommentCategory.TIGHT,
        "標準的な客単価・席数を想定。家賃と人件費のバランスを慎重に試算しましょう。",
    )


async def generate_store_story(answers: dict[str, list[str]]) -> str:
    concept = ", ".join(answers.get("q1", []) or ["気軽に立ち寄れるお店"])
    mood = ", ".join(answers.get("q2", []) or ["落ち着いた雰囲気"])
    cuisine = ", ".join(answers.get("q6", []) or ["得意料理"])
    fallback = (
        f"あなたのお店は「{concept}」を中心に、{mood}で過ごせる空間。"
        f"看板は「{cuisine}」。オープン初日から、あなたらしい店づくりが始まります。"
    )
    story = await ai_generate_store_story({"concept": concept, "mood": mood, "cuisine": cuisine})
    return story or fallback


async def process_simulation_submission(
    db: AsyncSession,
    payload: SubmitSimulationRequest,
    user_id: Optional[int],
) -> SimulationResultResponse:
    answers_dict = {item.question_code: item.values for item in payload.answers}

    session = SimpleSimulationSession(
        user_id=user_id,
        guest_session_token=payload.guest_session_token,
        status=SimulationStatus.COMPLETED,
        completed_at=datetime.utcnow(),
    )
    db.add(session)
    await db.flush()  # to get session.id

    for item in payload.answers:
        db.add(
            SimpleSimulationAnswer(
                session_id=session.id,
                question_code=item.question_code,
                answer_values=item.values,
            )
        )

    axis_scores = calculate_axis_scores(answers_dict)
    funds_category, funds_comment = generate_funds_comment(answers_dict)
    story_text = await generate_store_story(answers_dict)

    db.add(
        SimpleSimulationResult(
            session_id=session.id,
            axis_scores=axis_scores,
            funds_comment_category=funds_category,
            funds_comment_text=funds_comment,
            store_story_text=story_text,
        )
    )

    # If authenticated, persist per-axis scores and store story
    if user_id:
        axis_map = await _get_axis_id_map(db)
        for axis_code, score in axis_scores.items():
            axis_id = axis_map.get(axis_code)
            if axis_id is None:
                continue
            db.add(
                AxisScore(
                    user_id=user_id,
                    axis_id=axis_id,
                    score=score,
                    level1_completion_ratio=0,
                    level2_completion_ratio=0,
                    calculated_at=datetime.utcnow(),
                )
            )
        # store story
        db.add(
            StoreStory(
                user_id=user_id,
                source=StoreStorySource.SIMPLE_SIMULATION,
                content=story_text,
            )
        )

    await db.commit()

    return SimulationResultResponse(
        session_id=session.id,
        axis_scores=axis_scores,
        funds_comment_category=funds_category.value,
        funds_comment_text=funds_comment,
        store_story_text=story_text,
    )


async def attach_session_to_user(
    db: AsyncSession,
    session_id: int,
    user_id: int,
) -> Optional[SimulationResultResponse]:
    result = await db.execute(
        select(SimpleSimulationSession).where(SimpleSimulationSession.id == session_id)
    )
    session_obj = result.scalar_one_or_none()
    if not session_obj:
        return None

    # Attach user
    session_obj.user_id = user_id

    # Get result
    res_result = await db.execute(
        select(SimpleSimulationResult).where(SimpleSimulationResult.session_id == session_id)
    )
    sim_result = res_result.scalar_one_or_none()
    if not sim_result:
        await db.commit()
        return None

    # Persist story and axis scores for the user
    db.add(
        StoreStory(
            user_id=user_id,
            source=StoreStorySource.SIMPLE_SIMULATION,
            content=sim_result.store_story_text or "",
        )
    )

    axis_map = await _get_axis_id_map(db)
    await db.execute(delete(AxisScore).where(AxisScore.user_id == user_id))
    for axis_code, score in sim_result.axis_scores.items():
        axis_id = axis_map.get(axis_code)
        if axis_id is None:
            continue
        db.add(
            AxisScore(
                user_id=user_id,
                axis_id=axis_id,
                score=score,
                level1_completion_ratio=0,
                level2_completion_ratio=0,
                calculated_at=datetime.utcnow(),
            )
        )

    await db.commit()

    return SimulationResultResponse(
        session_id=session_id,
        axis_scores=sim_result.axis_scores,
        funds_comment_category=sim_result.funds_comment_category.value,
        funds_comment_text=sim_result.funds_comment_text or "",
        store_story_text=sim_result.store_story_text or "",
    )


async def _get_axis_id_map(db: AsyncSession) -> dict[str, int]:
    result = await db.execute(select(PlanningAxis.code, PlanningAxis.id))
    return {code: axis_id for code, axis_id in result.all()}
