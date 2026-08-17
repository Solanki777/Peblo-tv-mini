from typing import TYPE_CHECKING, List

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.season import Season


class Show(Base):
    __tablename__ = "shows"

    id: Mapped[int] = mapped_column(primary_key=True)

    title: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        index=True,
    )

    slug: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        index=True,
    )

    section: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        index=True,
    )

    synopsis: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    categories: Mapped[str] = mapped_column(Text)

    seasons: Mapped[List["Season"]] = relationship(
        back_populates="show",
        cascade="all, delete-orphan",
    )