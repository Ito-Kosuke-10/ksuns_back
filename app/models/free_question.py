from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class FreeQuestion(Base):
    __tablename__ = "free_questions"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    axis_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    question_text: Mapped[str] = mapped_column(String(length=4000), nullable=False)
    answer_text: Mapped[str] = mapped_column(String(length=4000), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )

    user = relationship("User", back_populates="free_questions")
