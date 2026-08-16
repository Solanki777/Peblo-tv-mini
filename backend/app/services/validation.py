"""Publish-blocking validation.

Ideally these rules (episode needs artwork + duration before it can be
marked "published"; a published show needs a section) would be enforced the
moment an editor tries to flip an episode/show into that state, in the CRUD
routers. That wiring hasn't been done yet (see README "what I left out").
Until it is, this module is the safety net: the publish job runs the same
checks right before it builds the catalogue, so a half-finished episode
can never leak into what viewers see - it just gets skipped and reported
here instead, grouped so an editor can fix it without pinging an engineer.

Only episodes with status == "published" are considered "trying to publish"
- drafts are expected to be incomplete and aren't reported as blockers.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List

from sqlalchemy.orm import Session

from app.models.artwork import Artwork
from app.models.episode import Episode
from app.models.season import Season
from app.models.show import Show

REQUIRED_ARTWORK_TYPES = {"poster", "banner", "thumbnail"}


@dataclass
class ValidationReport:
    shows_missing_section: List[dict] = field(default_factory=list)
    episodes_missing_duration: List[dict] = field(default_factory=list)
    episodes_missing_artwork: List[dict] = field(default_factory=list)

    @property
    def issue_count(self) -> int:
        return (
            len(self.shows_missing_section)
            + len(self.episodes_missing_duration)
            + len(self.episodes_missing_artwork)
        )

    @property
    def blocked_episode_ids(self) -> set[int]:
        """Primary-key episode.id values that must be excluded from the
        catalogue: either because their own show has no section, or because
        the episode itself is missing duration/artwork."""
        blocked = {e["_episode_pk"] for e in self.episodes_missing_duration}
        blocked |= {e["_episode_pk"] for e in self.episodes_missing_artwork}
        return blocked

    def to_public_dict(self) -> dict:
        """Same report, without the internal `_episode_pk` bookkeeping key."""

        def strip(rows: List[dict]) -> List[dict]:
            return [{k: v for k, v in row.items() if not k.startswith("_")} for row in rows]

        return {
            "issue_count": self.issue_count,
            "shows_missing_section": strip(self.shows_missing_section),
            "episodes_missing_duration": strip(self.episodes_missing_duration),
            "episodes_missing_artwork": strip(self.episodes_missing_artwork),
        }


def build_validation_report(db: Session) -> ValidationReport:
    report = ValidationReport()

    published_episodes: List[Episode] = (
        db.query(Episode).filter(Episode.status == "published").all()
    )

    if not published_episodes:
        return report

    season_ids = {e.season_id for e in published_episodes}
    seasons: Dict[int, Season] = {
        s.id: s for s in db.query(Season).filter(Season.id.in_(season_ids)).all()
    }

    show_ids = {s.show_id for s in seasons.values()}
    shows: Dict[int, Show] = {
        sh.id: sh for sh in db.query(Show).filter(Show.id.in_(show_ids)).all()
    }

    episode_ids = [e.id for e in published_episodes]
    artworks: List[Artwork] = (
        db.query(Artwork).filter(Artwork.episode_id.in_(episode_ids)).all()
    )
    artwork_types_by_episode: Dict[int, set[str]] = {}
    for a in artworks:
        artwork_types_by_episode.setdefault(a.episode_id, set()).add(a.artwork_type)

    flagged_show_ids: set[int] = set()
    for show in shows.values():
        if not show.section:
            report.shows_missing_section.append(
                {"id": show.id, "title": show.title, "slug": show.slug}
            )
            flagged_show_ids.add(show.id)

    for episode in published_episodes:
        season = seasons.get(episode.season_id)
        show = shows.get(season.show_id) if season else None

        location = {
            "episode_id": episode.episode_id,
            "title": episode.title,
            "language": episode.language,
            "content_group": episode.content_group,
            "show": show.title if show else "(unknown show)",
            "season_number": season.season_number if season else None,
            "_episode_pk": episode.id,
        }

        if episode.duration_seconds is None:
            report.episodes_missing_duration.append(dict(location))

        present_types = artwork_types_by_episode.get(episode.id, set())
        missing_types = sorted(REQUIRED_ARTWORK_TYPES - present_types)
        if missing_types:
            report.episodes_missing_artwork.append(
                {**location, "missing_artwork_types": missing_types}
            )

    return report
