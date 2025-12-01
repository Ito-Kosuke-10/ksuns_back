from datetime import datetime
from enum import Enum

from sqlalchemy import BigInteger, DateTime, Enum as SqlEnum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class SummaryType(str, Enum):
    FAMILY = "family"
    STAFF = "staff"
    BANK = "bank"
    PUBLIC = "public"


class Summary(Base):
    __tablename__ = "summaries"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE")
    )
    summary_type: Mapped[SummaryType] = mapped_column(
        SqlEnum(
            SummaryType,
            values_callable=lambda enum: [member.value for member in enum],
            name="summarytype",
        ),
        nullable=False,
    )
    content: Mapped[str] = mapped_column(String(length=8000), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )

    user = relationship("User", back_populates="summaries")
