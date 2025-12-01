from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class DeepQuestion(Base):
    __tablename__ = "deep_questions"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    axis_code: Mapped[str] = mapped_column(String(64), nullable=False)
    question_text: Mapped[str] = mapped_column(String(length=4000), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )

    user = relationship("User", back_populates="deep_questions")
    answer = relationship(
        "DeepAnswer",
        back_populates="question",
        uselist=False,
        cascade="all, delete-orphan",
    )


class DeepAnswer(Base):
    __tablename__ = "deep_answers"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    deep_question_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("deep_questions.id", ondelete="CASCADE"), nullable=False
    )
    answer_text: Mapped[str] = mapped_column(String(length=4000), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )

    question = relationship("DeepQuestion", back_populates="answer")
