from datetime import datetime
from typing import List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.axis import PlanningAxis
from app.models.deep_question import DeepAnswer, DeepQuestion
from app.services.ai_client import answer_question as ai_answer_question


async def _axis_name(session: AsyncSession, axis_code: str) -> str:
    result = await session.execute(select(PlanningAxis).where(PlanningAxis.code == axis_code))
    axis = result.scalar_one_or_none()
    return axis.name if axis and axis.name else axis_code


async def list_messages(
    session: AsyncSession,
    user_id: int,
    axis_code: str,
    limit: int = 20,
) -> list[tuple[DeepQuestion, DeepAnswer | None]]:
    result = await session.execute(
        select(DeepQuestion)
        .where(DeepQuestion.user_id == user_id, DeepQuestion.axis_code == axis_code)
        .order_by(DeepQuestion.created_at.desc())
        .limit(limit)
    )
    questions = list(result.scalars())
    question_ids = [q.id for q in questions]
    answers_map: dict[int, DeepAnswer] = {}
    if question_ids:
        answers_result = await session.execute(
            select(DeepAnswer).where(DeepAnswer.deep_question_id.in_(question_ids))
        )
        for ans in answers_result.scalars():
            answers_map[ans.deep_question_id] = ans
    return [(q, answers_map.get(q.id)) for q in questions]


async def add_message(
    session: AsyncSession,
    user_id: int,
    axis_code: str,
    question_text: str,
) -> None:
    dq = DeepQuestion(
        user_id=user_id,
        axis_code=axis_code,
        question_text=question_text,
        created_at=datetime.utcnow(),
    )
    session.add(dq)
    await session.flush()

    reply = await ai_answer_question({"axis_code": axis_code}, question_text)
    if not reply:
        reply = "深掘りのための回答生成に失敗しました。別の聞き方でもう一度お試しください。"

    session.add(
        DeepAnswer(
            deep_question_id=dq.id,
            answer_text=reply,
            created_at=datetime.utcnow(),
        )
    )
    await session.commit()
