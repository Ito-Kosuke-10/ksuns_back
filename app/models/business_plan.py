from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class BusinessPlanDraft(Base):
    __tablename__ = "business_plan_drafts"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    snapshot_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    summary_for_bank: Mapped[str | None] = mapped_column(Text, nullable=True)
    summary_for_family: Mapped[str | None] = mapped_column(Text, nullable=True)
    funding_plan: Mapped[str | None] = mapped_column(Text, nullable=True)
    cashflow_outline: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)

    user = relationship("User", back_populates="business_plan_drafts")
