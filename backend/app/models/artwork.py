from sqlalchemy import ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Artwork(Base):
    __tablename__ = "artworks"

    id: Mapped[int] = mapped_column(primary_key=True)

    episode_id: Mapped[int] = mapped_column(
        ForeignKey("episodes.id", ondelete="CASCADE"),
        index=True,
    )

    artwork_type: Mapped[str] = mapped_column(
        String(20)
    )

    storage_key: Mapped[str] = mapped_column(
        String(500)
    )

    width: Mapped[int] = mapped_column(Integer)
    height: Mapped[int] = mapped_column(Integer)
    size_bytes: Mapped[int] = mapped_column(Integer)

    episode: Mapped["Episode"] = relationship(
        back_populates="artworks"
    )

    __table_args__ = (
        UniqueConstraint(
            "episode_id",
            "artwork_type",
            name="uq_episode_artwork_type",
        ),
    )