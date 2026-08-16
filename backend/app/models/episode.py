from typing import List

from sqlalchemy import (
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Episode(Base):
    __tablename__ = "episodes"

    id: Mapped[int] = mapped_column(primary_key=True)

    episode_id: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        index=True,
    )

    season_id: Mapped[int] = mapped_column(
        ForeignKey("seasons.id", ondelete="CASCADE"),
        index=True,
    )

    episode_number: Mapped[int] = mapped_column(Integer)

    title: Mapped[str] = mapped_column(String(255))

    duration_seconds: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    language: Mapped[str] = mapped_column(
        String(10),
        index=True,
    )

    content_group: Mapped[str] = mapped_column(
        String(255),
        index=True,
    )

    status: Mapped[str] = mapped_column(
        String(30),
        default="draft",
        index=True,
    )

    season: Mapped["Season"] = relationship(
        back_populates="episodes"
    )

    artworks: Mapped[List["Artwork"]] = relationship(
        back_populates="episode",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        UniqueConstraint(
            "content_group",
            "language",
            name="uq_episode_content_group_language",
        ),
    )