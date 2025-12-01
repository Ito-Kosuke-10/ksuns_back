from enum import Enum

from sqlalchemy import (
    BigInteger,
    Enum as SqlEnum,
    ForeignKey,
    JSON,
    SmallInteger,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class QuestionGroup(str, Enum):
    SIMPLE_WEEK1 = "simple_week1"
    LEVEL1 = "level1"
    LEVEL2 = "level2"


class AnswerType(str, Enum):
    SINGLE = "single"
    MULTI = "multi"
    SLIDER = "slider"
    SHORT_TEXT = "short_text"
    TEXT = "text"


class SourceType(str, Enum):
    STATIC = "static"
    AI_GENERATED = "ai_generated"


class Question(Base):
    __tablename__ = "questions"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    question_code: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    question_group: Mapped[QuestionGroup] = mapped_column(
        SqlEnum(
            QuestionGroup,
            values_callable=lambda enum: [member.value for member in enum],
            name="questiongroup",
        ),
        nullable=False,
    )
    axis_id: Mapped[int | None] = mapped_column(
        SmallInteger, ForeignKey("planning_axes.id", ondelete="SET NULL"), nullable=True
    )
    source_type: Mapped[SourceType] = mapped_column(
        SqlEnum(
            SourceType,
            values_callable=lambda enum: [member.value for member in enum],
            name="sourcetype",
        ),
        nullable=False,
        default=SourceType.STATIC,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    prompt: Mapped[str] = mapped_column(String(2048), nullable=False)
    answer_type: Mapped[AnswerType] = mapped_column(
        SqlEnum(
            AnswerType,
            values_callable=lambda enum: [member.value for member in enum],
            name="answertype",
        ),
        nullable=False,
    )
    options_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    display_order: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)

    axis = relationship("PlanningAxis", back_populates="questions")
