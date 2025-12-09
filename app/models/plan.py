# 複数プラン対応のため、プランモデルを追加　からちゃん
from datetime import datetime, timezone

from sqlalchemy import BigInteger, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class PlanningPlan(Base):
    """
    開業プラン（例：焼肉プラン、居酒屋プランなど）を表すモデル。

    STEP1 ではまだ他のモデルとは紐付けず、
    「ユーザーにぶら下がるプランの入れ物」だけを用意する。
    """

    __tablename__ = "planning_plans"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    # このプランを持つユーザー
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    # プラン名（例：「焼肉プラン」「居酒屋プラン」など）
    name: Mapped[str] = mapped_column(String(255), nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # ------------------------------------------------------------------
    # リレーション
    # ------------------------------------------------------------------
    user = relationship("User", back_populates="plans")
    
    # 他のモデルから参照されるための設定
    simulation_sessions = relationship("SimpleSimulationSession", back_populates="planning_plan", cascade="all, delete-orphan")
