from datetime import datetime

from sqlalchemy import BigInteger, DateTime, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class User(Base):
    __tablename__ = "users"
    __table_args__ = (UniqueConstraint("google_sub"), UniqueConstraint("email"))

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    google_sub: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    # Relationships (minimal)
    simulation_sessions = relationship(
        "SimpleSimulationSession",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    axis_answers = relationship(
        "AxisAnswer",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    axis_scores = relationship(
        "AxisScore",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    detail_question_answers = relationship(
        "DetailQuestionAnswer",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    owner_note = relationship(
        "OwnerNote",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )
    store_stories = relationship(
        "StoreStory",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    summaries = relationship(
        "Summary",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    qa_conversations = relationship(
        "QAConversation",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    deep_questions = relationship(
        "DeepQuestion",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    free_questions = relationship(
        "FreeQuestion",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    business_plan_drafts = relationship(
        "BusinessPlanDraft",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    # plans リレーションを追加　からちゃん
    plans = relationship(
        "PlanningPlan",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    concept_answers = relationship(
        "ConceptAnswer",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    revenue_forecast_answers = relationship(
        "RevenueForecastAnswer",
        back_populates="user",
        cascade="all, delete-orphan",
    )
