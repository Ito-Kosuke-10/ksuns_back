from datetime import datetime
from enum import Enum

from sqlalchemy import BigInteger, DateTime, Enum as SqlEnum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class StoreStorySource(str, Enum):
    SIMPLE_SIMULATION = "simple_simulation"
    PLANNING_UPDATE = "planning_update"


class OwnerNote(Base):
    __tablename__ = "owner_notes"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), unique=True
    )
    content: Mapped[str] = mapped_column(String(length=4000), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    user = relationship("User", back_populates="owner_note")


class StoreStory(Base):
    __tablename__ = "store_stories"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE")
    )
    source: Mapped[StoreStorySource] = mapped_column(
        SqlEnum(
            StoreStorySource,
            values_callable=lambda enum: [member.value for member in enum],
            name="storestorysource",
        ),
        nullable=False,
    )
    content: Mapped[str] = mapped_column(String(length=4000), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )

    user = relationship("User", back_populates="store_stories")
