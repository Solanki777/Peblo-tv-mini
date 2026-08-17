from typing import TYPE_CHECKING, List

from sqlalchemy import ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.episode import Episode
    from app.models.show import Show


class Season(Base):
    __tablename__ = "seasons"

    id: Mapped[int] = mapped_column(primary_key=True)

    show_id: Mapped[int] = mapped_column(
        ForeignKey("shows.id", ondelete="CASCADE"),
        index=True,
    )

    season_number: Mapped[int] = mapped_column(Integer)

    show: Mapped["Show"] = relationship(back_populates="seasons")

    episodes: Mapped[List["Episode"]] = relationship(
        back_populates="season",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        UniqueConstraint(
            "show_id",
            "season_number",
            name="uq_season_show_number",
        ),
    )