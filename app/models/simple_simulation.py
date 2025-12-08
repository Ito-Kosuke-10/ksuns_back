from datetime import datetime
from enum import Enum

from sqlalchemy import (
    BigInteger,
    DateTime,
    Enum as SqlEnum,
    ForeignKey,
    JSON,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.plan import PlanningPlan # からちゃん追加部分 複数プラン対応のため、プランモデルを追加に対応

class SimulationStatus(str, Enum):
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    DISCARDED = "discarded"


class FundsCommentCategory(str, Enum):
    RELAXED = "relaxed"
    TIGHT = "tight"
    CRITICAL = "critical"


class SimpleSimulationSession(Base):
    __tablename__ = "simple_simulation_sessions"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    # ★ からちゃん追加: どのプランの簡易シミュレーションかを示す
    plan_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("planning_plans.id", ondelete="SET NULL"),  # テーブル名は実装に合わせて
        nullable=True,
    )
    guest_session_token: Mapped[str | None] = mapped_column(
        String(255), nullable=True, unique=True
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    status: Mapped[SimulationStatus] = mapped_column(
        SqlEnum(
            SimulationStatus,
            values_callable=lambda enum: [member.value for member in enum],
            name="simulationstatus",
        ),
        nullable=False,
        default=SimulationStatus.IN_PROGRESS,
    )

    user = relationship("User", back_populates="simulation_sessions")
    answers = relationship(
        "SimpleSimulationAnswer",
        back_populates="session",
        cascade="all, delete-orphan",
    )
    result = relationship(
        "SimpleSimulationResult",
        back_populates="session",
        uselist=False,
        cascade="all, delete-orphan",
    )
    # ★ からちゃん追加: プランとのリレーション
    planning_plan = relationship("PlanningPlan", back_populates="simulation_sessions")


class SimpleSimulationAnswer(Base):
    __tablename__ = "simple_simulation_answers"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("simple_simulation_sessions.id", ondelete="CASCADE")
    )
    question_code: Mapped[str] = mapped_column(String(64), nullable=False)
    answer_values: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )

    session = relationship("SimpleSimulationSession", back_populates="answers")


class SimpleSimulationResult(Base):
    __tablename__ = "simple_simulation_results"
    __table_args__ = (UniqueConstraint("session_id"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("simple_simulation_sessions.id", ondelete="CASCADE")
    )
    axis_scores: Mapped[dict] = mapped_column(JSON, nullable=False)
    funds_comment_category: Mapped[FundsCommentCategory] = mapped_column(
        SqlEnum(
            FundsCommentCategory,
            values_callable=lambda enum: [member.value for member in enum],
            name="fundscommentcategory",
        ),
        nullable=False,
    )
    funds_comment_text: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    store_story_text: Mapped[str | None] = mapped_column(String(4096), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )

    session = relationship("SimpleSimulationSession", back_populates="result")
