"""
深掘り機能（Deep Dive）のデータモデル
既存のDeepQuestionモデルとは別に、新しいカードベースの深掘り機能用のモデル
"""
from datetime import datetime, timezone
from enum import Enum

from sqlalchemy import BigInteger, DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class DeepDiveStatus(str, Enum):
    """深掘りカードの進捗ステータス"""

    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


class DeepDiveProgress(Base):
    """深掘りカードの進捗管理"""

    __tablename__ = "deep_dive_progress"
    __table_args__ = (UniqueConstraint("user_id", "card_id"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    axis_code: Mapped[str] = mapped_column(String(64), nullable=False)
    card_id: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[DeepDiveStatus] = mapped_column(
        String(32), nullable=False, default=DeepDiveStatus.NOT_STARTED
    )
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    user = relationship("User", back_populates="deep_dive_progress")


class DeepDiveChatLog(Base):
    """深掘りカードのチャット履歴"""

    __tablename__ = "deep_dive_chat_logs"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    card_id: Mapped[str] = mapped_column(String(128), nullable=False)
    role: Mapped[str] = mapped_column(String(16), nullable=False)  # "user" or "assistant"
    message: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    user = relationship("User", back_populates="deep_dive_chat_logs")

