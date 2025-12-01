from datetime import datetime
from enum import Enum

from sqlalchemy import (
    BigInteger,
    DateTime,
    Enum as SqlEnum,
    ForeignKey,
    SmallInteger,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class QAContextType(str, Enum):
    GLOBAL = "global"
    AXIS = "axis"


class QARole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class QAConversation(Base):
    __tablename__ = "qa_conversations"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE")
    )
    context_type: Mapped[QAContextType] = mapped_column(
        SqlEnum(
            QAContextType,
            values_callable=lambda enum: [member.value for member in enum],
            name="qacontexttype",
        ),
        nullable=False,
        default=QAContextType.GLOBAL,
    )
    axis_id: Mapped[int | None] = mapped_column(
        SmallInteger, ForeignKey("planning_axes.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )

    user = relationship("User", back_populates="qa_conversations")
    axis = relationship("PlanningAxis", back_populates="qa_conversations")
    messages = relationship(
        "QAMessage",
        back_populates="conversation",
        cascade="all, delete-orphan",
    )


class QAMessage(Base):
    __tablename__ = "qa_messages"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    conversation_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("qa_conversations.id", ondelete="CASCADE")
    )
    role: Mapped[QARole] = mapped_column(
        SqlEnum(
            QARole,
            values_callable=lambda enum: [member.value for member in enum],
            name="qarole",
        ),
        nullable=False,
    )
    content: Mapped[str] = mapped_column(String(length=4000), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )

    conversation = relationship("QAConversation", back_populates="messages")
