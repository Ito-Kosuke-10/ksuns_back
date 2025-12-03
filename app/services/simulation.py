from datetime import datetime
from typing import Dict, Iterable, Optional

from fastapi import HTTPException, status
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
from app.services.ai_client import (
    generate_concept_summary as ai_generate_concept_summary,
    generate_funds_summary as ai_generate_funds_summary,
    generate_store_story as ai_generate_store_story,
)

# Axis codes used across the project
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

# Mapping of simple_simulation question codes to relevant axes (7問版)
QUESTION_AXIS_MAP: dict[str, list[str]] = {
    "main_genre": ["concept", "marketing"],
    "sub_genre": ["concept", "marketing"],
    "seats": ["operation", "funds"],
    "price_point": ["funds", "menu"],
    "price_range": ["funds", "menu"],
    "business_hours": ["operation"],
    "location": ["location", "marketing"],
}

UNKNOWN_PREFIX = "undecided"


def _is_unknown(values: Iterable[str]) -> bool:
    return any(str(val).startswith(UNKNOWN_PREFIX) for val in values)


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

    # compliance は第1週でほぼ未着手想定、質問割当が少ないため最低 1.0 とする
    if scores.get("compliance") == 0:
        scores["compliance"] = 1.0
    return scores


def generate_funds_comment(store_profile: dict[str, object]) -> tuple[FundsCommentCategory, str]:
    seats = int(store_profile.get("seats") or 0)
    price_point = int(store_profile.get("price_point") or 0)

    if seats >= 40:
        return (
            FundsCommentCategory.TIGHT,
            "席数が多めの想定です。初期費用と人件費が膨らみやすいため、家賃とシフトのバランスを慎重に試算してください。",
        )
    if price_point >= 8000:
        return (
            FundsCommentCategory.RELAXED,
            "客単価が高めの想定です。席数と回転数次第では余裕のある計画にできますが、体験価値やオペレーション品質の維持に留意してください。",
        )
    return (
        FundsCommentCategory.TIGHT,
        "標準的な席数・客単価の想定です。家賃・人件費の固定費を抑え、回転数が低い場合のシナリオも試算しておくと安心です。",
    )


async def generate_store_story(store_profile: dict[str, object]) -> str:
    story = await ai_generate_store_story(store_profile)
    if story:
        return story

    main = store_profile.get("main_genre") or "お店"
    sub = store_profile.get("sub_genre") or ""
    location = store_profile.get("location") or "街"
    hours = store_profile.get("business_hours") or "営業時間未設定"
    return (
        f"{location}にある{main}（{sub}）として、{hours}帯を中心にお客さまを迎える計画です。"
        "こじんまりとしつつも温かい雰囲気で、日常を少し特別にする場所を目指します。"
    )


async def process_simulation_submission(
    db: AsyncSession,
    payload: SubmitSimulationRequest,
    user_id: Optional[int],
) -> SimulationResultResponse:
    answers_dict = {item.question_code: item.values for item in payload.answers}

    store_profile = _build_store_profile(answers_dict)
    missing = _find_missing_required(store_profile)
    if missing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"missing required fields: {', '.join(missing)}",
        )

    axis_scores = calculate_axis_scores(answers_dict)
    funds_category, funds_comment = generate_funds_comment(store_profile)
    story_text = await generate_store_story(store_profile)
    concept_title, concept_detail = await ai_generate_concept_summary(store_profile)
    funds_summary = await ai_generate_funds_summary(store_profile)

    # 未ログイン: 計算結果のみ返却（DB保存しない）
    if user_id is None:
        return SimulationResultResponse(
            session_id=0,
            axis_scores=axis_scores,
            funds_comment_category=funds_category.value,
            funds_comment_text=funds_comment,
            store_story_text=story_text,
            concept_title=concept_title,
            concept_detail=concept_detail,
            funds_summary=funds_summary,
        )

    # ログイン済み: 保存（既存tokenがあれば上書き再利用）
    session = None
    if payload.guest_session_token:
        session = await _get_session_by_guest_token(db, payload.guest_session_token)

    if session:
        session.user_id = user_id
        session.status = SimulationStatus.COMPLETED
        session.completed_at = datetime.utcnow()
        await db.execute(delete(SimpleSimulationAnswer).where(SimpleSimulationAnswer.session_id == session.id))
        await db.execute(delete(SimpleSimulationResult).where(SimpleSimulationResult.session_id == session.id))
    else:
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

    db.add(
        SimpleSimulationResult(
            session_id=session.id,
            axis_scores=axis_scores,
            funds_comment_category=funds_category,
            funds_comment_text=funds_comment,
            store_story_text=story_text,
        )
    )

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
        concept_title=concept_title,
        concept_detail=concept_detail,
        funds_summary=funds_summary,
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
        concept_title="コンセプトは未保存です",
        concept_detail="最新の簡易シミュレーションを実行すると再生成されます。",
        funds_summary=sim_result.funds_comment_text or "",
    )


async def _get_axis_id_map(db: AsyncSession) -> dict[str, int]:
    result = await db.execute(select(PlanningAxis.code, PlanningAxis.id))
    return {code: axis_id for code, axis_id in result.all()}


def _build_store_profile(answers: dict[str, list[str]]) -> dict[str, object]:
    """フロントからの回答を store_profile 形式に正規化する。"""

    def pick_first(key: str, default: str = "") -> str:
        vals = answers.get(key) or []
        return vals[0] if vals else default

    def pick_number(key: str, default: int = 0) -> int:
        vals = answers.get(key) or []
        if not vals:
            return default
        try:
            return int(float(vals[0]))
        except ValueError:
            return default

    return {
        "main_genre": pick_first("main_genre", "undecided"),
        "sub_genre": pick_first("sub_genre", "undecided"),
        "seats": pick_number("seats", 0),
        "price_range": pick_first("price_range", "undecided"),
        "price_point": pick_number("price_point", 0),
        "business_hours": pick_first("business_hours", "undecided"),
        "location": pick_first("location", "undecided"),
    }


def _find_missing_required(store_profile: dict[str, object]) -> list[str]:
    required = ["main_genre", "sub_genre", "seats", "price_point", "business_hours", "location"]
    missing: list[str] = []
    for key in required:
        val = store_profile.get(key)
        if val in (None, "", "undecided", 0):
            missing.append(key)
    return missing


async def _get_session_by_guest_token(db: AsyncSession, token: str) -> Optional[SimpleSimulationSession]:
    result = await db.execute(
        select(SimpleSimulationSession).where(SimpleSimulationSession.guest_session_token == token)
    )
    return result.scalar_one_or_none()
