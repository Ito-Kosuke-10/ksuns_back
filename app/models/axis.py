from datetime import datetime

from sqlalchemy import (
    BigInteger,
    DateTime,
    Enum as SqlEnum,
    ForeignKey,
    Integer,
    JSON,
    Numeric,
    SmallInteger,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class PlanningAxis(Base):
    __tablename__ = "planning_axes"

    id: Mapped[int] = mapped_column(SmallInteger, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    display_order: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)

    steps = relationship(
        "AxisStep",
        back_populates="axis",
        cascade="all, delete-orphan",
    )
    questions = relationship("Question", back_populates="axis")
    answers = relationship("AxisAnswer", back_populates="axis")
    scores = relationship("AxisScore", back_populates="axis")
    qa_conversations = relationship("QAConversation", back_populates="axis")


class AxisStep(Base):
    __tablename__ = "axis_steps"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    axis_id: Mapped[int] = mapped_column(
        SmallInteger, ForeignKey("planning_axes.id", ondelete="CASCADE"), nullable=False
    )
    level: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    code: Mapped[str] = mapped_column(String(128), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    display_order: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)

    axis = relationship("PlanningAxis", back_populates="steps")


class AxisAnswer(Base):
    __tablename__ = "axis_answers"
    __table_args__ = (
        UniqueConstraint("user_id", "axis_id", "level"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    axis_id: Mapped[int] = mapped_column(
        SmallInteger, ForeignKey("planning_axes.id", ondelete="CASCADE"), nullable=False
    )
    level: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    answers_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    user = relationship("User", back_populates="axis_answers")
    axis = relationship("PlanningAxis", back_populates="answers")


class AxisScore(Base):
    __tablename__ = "axis_scores"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    axis_id: Mapped[int] = mapped_column(
        SmallInteger, ForeignKey("planning_axes.id", ondelete="CASCADE"), nullable=False
    )
    score: Mapped[float] = mapped_column(Numeric(3, 1), nullable=False)
    level1_completion_ratio: Mapped[float] = mapped_column(
        Numeric(3, 2), nullable=False, default=0
    )
    level2_completion_ratio: Mapped[float] = mapped_column(
        Numeric(3, 2), nullable=False, default=0
    )
    calculated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )

    user = relationship("User", back_populates="axis_scores")
    axis = relationship("PlanningAxis", back_populates="scores")
