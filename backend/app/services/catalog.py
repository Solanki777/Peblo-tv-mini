"""Builds the catalogue.json the viewer reads.

Rules encoded here (see reference.json + the brief):
  - Only shows with a section, and only episodes with status="published",
    are eligible.
  - Episodes sharing a content_group are language variants of ONE catalogue
    entry. They collapse into a single entry with a `languages` list.
  - Season 0 is trailers, not a normal season - we still include it (as
    season_number 0) so nothing is silently dropped, but callers (the
    viewer) must not render it in the normal season list. See README.
  - Ordering is fully deterministic: sections follow reference.json order
    (unknown sections sort after, alphabetically), shows sort by title,
    seasons by season_number, content groups by their lowest episode
    number, languages alphabetically. Same DB state always produces
    byte-identical output (aside from `generated_at`/`publish_run_id`),
    which is what makes the publish job idempotent.
  - Anything that fails validation (see services/validation.py) is left out
    of the catalogue entirely rather than published half-finished.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, List

from sqlalchemy.orm import Session

from app.models.artwork import Artwork
from app.models.episode import Episode
from app.models.season import Season
from app.models.show import Show
from app.services.validation import ValidationReport, build_validation_report

SECTION_ORDER = ["featured", "series", "minisodes", "songs"]


def _section_sort_key(section: str) -> tuple:
    if section in SECTION_ORDER:
        return (0, SECTION_ORDER.index(section))
    return (1, section)


def build_catalog(db: Session, report: ValidationReport | None = None) -> dict:
    if report is None:
        report = build_validation_report(db)

    blocked_episode_ids = report.blocked_episode_ids
    shows_missing_section_ids = {row["id"] for row in report.shows_missing_section}

    shows: List[Show] = db.query(Show).all()
    seasons: List[Season] = db.query(Season).all()
    episodes: List[Episode] = (
        db.query(Episode).filter(Episode.status == "published").all()
    )
    episode_ids = [e.id for e in episodes]
    artworks: List[Artwork] = (
        db.query(Artwork).filter(Artwork.episode_id.in_(episode_ids)).all()
        if episode_ids
        else []
    )

    artworks_by_episode: Dict[int, dict] = {}
    for a in artworks:
        artworks_by_episode.setdefault(a.episode_id, {})[a.artwork_type] = {
            "storage_key": a.storage_key,
            "width": a.width,
            "height": a.height,
        }

    seasons_by_id = {s.id: s for s in seasons}
    seasons_by_show: Dict[int, List[Season]] = {}
    for s in seasons:
        seasons_by_show.setdefault(s.show_id, []).append(s)

    # episode -> season -> show, filtered to eligible episodes only
    episodes_by_season: Dict[int, List[Episode]] = {}
    for e in episodes:
        if e.id in blocked_episode_ids:
            continue
        season = seasons_by_id.get(e.season_id)
        if season is None or season.show_id in shows_missing_section_ids:
            continue
        episodes_by_season.setdefault(e.season_id, []).append(e)

    sections: Dict[str, List[dict]] = {}
    included_shows = 0
    included_episode_variants = 0

    for show in shows:
        if not show.section or show.id in shows_missing_section_ids:
            continue

        show_seasons = []
        for season in sorted(
            seasons_by_show.get(show.id, []), key=lambda s: s.season_number
        ):
            season_episodes = episodes_by_season.get(season.id, [])
            if not season_episodes:
                continue

            groups: Dict[str, List[Episode]] = {}
            for ep in season_episodes:
                groups.setdefault(ep.content_group, []).append(ep)

            content_entries = []
            for content_group, variants in groups.items():
                variants_sorted = sorted(variants, key=lambda e: e.language)
                min_episode_number = min(v.episode_number for v in variants_sorted)

                languages = []
                for v in variants_sorted:
                    languages.append(
                        {
                            "language": v.language,
                            "episode_id": v.episode_id,
                            "title": v.title,
                            "duration_seconds": v.duration_seconds,
                            "artwork": artworks_by_episode.get(v.id, {}),
                        }
                    )
                    included_episode_variants += 1

                # Prefer English as the "primary" display title/artwork
                # for surfaces that only want one, falling back to
                # whichever language variant sorts first.
                primary = next(
                    (v for v in variants_sorted if v.language == "en"),
                    variants_sorted[0],
                )

                content_entries.append(
                    {
                        "content_group": content_group,
                        "episode_number": min_episode_number,
                        "title": primary.title,
                        "duration_seconds": primary.duration_seconds,
                        "artwork": artworks_by_episode.get(primary.id, {}),
                        "languages": languages,
                    }
                )

            content_entries.sort(key=lambda c: c["episode_number"])

            show_seasons.append(
                {
                    "season_number": season.season_number,
                    "is_trailers": season.season_number == 0,
                    "episodes": content_entries,
                }
            )

        if not show_seasons:
            continue

        included_shows += 1
        categories = [c.strip() for c in (show.categories or "").split(",") if c.strip()]

        sections.setdefault(show.section, []).append(
            {
                "id": show.id,
                "slug": show.slug,
                "title": show.title,
                "synopsis": show.synopsis,
                "categories": categories,
                "seasons": show_seasons,
            }
        )

    for section_shows in sections.values():
        section_shows.sort(key=lambda s: s["title"].lower())

    ordered_sections = [
        {"section": section, "shows": sections[section]}
        for section in sorted(sections.keys(), key=_section_sort_key)
    ]

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "sections": ordered_sections,
        "counts": {
            "shows": included_shows,
            "episode_variants": included_episode_variants,
        },
    }
