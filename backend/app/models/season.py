from typing import List

from sqlalchemy import ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Season(Base):
    __tablename__ = "seasons"

    id: Mapped[int] = mapped_column(primary_key=True)

    show_id: Mapped[int] = mapped_column(
        ForeignKey("shows.id", ondelete="CASCADE"),
        index=True,
    )

    season_number: Mapped[int] = mapped_column(Integer)

    show: Mapped["Show"] = relationship(
        back_populates="seasons"
    )

    episodes: Mapped[List["Episode"]] = relationship(
        back_populates="season",
        cascade="all, delete-orphan",
    )

    # FIXED: nothing previously stopped two seasons with the same
    # season_number under one show - this is the DB-level backstop for the
    # check now done in app/api/seasons.py (belt and suspenders: the API
    # gives a clean error, this guarantees it holds even if something else
    # ever writes to this table directly, e.g. a seed script).
    __table_args__ = (
        UniqueConstraint(
            "show_id",
            "season_number",
            name="uq_season_show_number",
        ),
    )