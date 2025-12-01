from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.axis import PlanningAxis
from app.models.free_question import FreeQuestion
from app.models.qa import QAContextType, QAConversation, QAMessage, QARole
from app.schemas.qa import QAResponse
from app.services.ai_client import answer_question as ai_answer_question


async def handle_question(
    db: AsyncSession,
    user_id: int,
    context_type: str,
    axis_code: str | None,
    question: str,
) -> QAResponse:
    axis_id = None
    if context_type == QAContextType.AXIS.value and axis_code:
        result = await db.execute(select(PlanningAxis).where(PlanningAxis.code == axis_code))
        axis = result.scalar_one_or_none()
        if axis:
            axis_id = axis.id

    convo = QAConversation(
        user_id=user_id,
        context_type=QAContextType(context_type),
        axis_id=axis_id,
        created_at=datetime.utcnow(),
    )
    db.add(convo)
    await db.flush()

    db.add(
        QAMessage(
            conversation_id=convo.id,
            role=QARole.USER,
            content=question,
        )
    )

    context = {"axis_code": axis_code, "question": question}
    reply_text = await ai_answer_question(context, question)
    if not reply_text:
        reply_text = "ご質問ありがとうございます。詳細な情報をもとに、次のステップを一緒に整理していきましょう。"

    db.add(
        QAMessage(
            conversation_id=convo.id,
            role=QARole.ASSISTANT,
            content=reply_text,
        )
    )
    db.add(
        FreeQuestion(
            user_id=user_id,
            axis_code=axis_code,
            question_text=question,
            answer_text=reply_text,
            created_at=datetime.utcnow(),
        )
    )

    await db.commit()

    return QAResponse(reply=reply_text)


async def list_recent_questions(
    db: AsyncSession, user_id: int, limit: int = 5
) -> list[FreeQuestion]:
    result = await db.execute(
        select(FreeQuestion)
        .where(FreeQuestion.user_id == user_id)
        .order_by(FreeQuestion.created_at.desc())
        .limit(limit)
    )
    return list(result.scalars())
