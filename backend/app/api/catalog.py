"""What the viewer reads. No auth, no DB query - just the published file.

Serving a pre-built file instead of querying the DB per-request means the
viewer never pays for joins/aggregation on every page load, and it can
never see a show mid-edit - it only ever sees what the last successful
publish produced. The trade-off is staleness: an edit isn't visible to
viewers until someone hits publish again. See README for where this
approach stops scaling.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from app.config import CATALOG_KEY
from app.services.storage import get_storage

router = APIRouter(tags=["Catalog"])


def _load_catalog() -> dict:
    storage = get_storage()
    try:
        return storage.read_json(CATALOG_KEY)
    except FileNotFoundError:
        raise HTTPException(
            status_code=404,
            detail="No catalogue has been published yet.",
        )


@router.get("/catalog")
def get_catalog():
    return _load_catalog()


@router.get("/catalog/search")
def search_catalog(
    q: str | None = Query(default=None, description="Matches show title, episode title, or category"),
    category: str | None = None,
    language: str | None = None,
    section: str | None = None,
):
    """Naive in-memory filter over the published catalogue.

    Fine at this catalogue's scale (dozens of shows). At real scale this
    would need to move to a DB-backed / search-index query instead of
    linear-scanning JSON on every request - see README's search section for
    where that line is and what I'd reach for next (Postgres full-text
    search or a dedicated index like Meilisearch/Elasticsearch, plus
    caching the parsed catalogue in memory rather than re-reading it from
    disk per request).
    """
    catalog = _load_catalog()
    q_lower = q.lower() if q else None

    matched_sections = []
    for section_entry in catalog.get("sections", []):
        if section and section_entry["section"] != section:
            continue

        matched_shows = []
        for show in section_entry["shows"]:
            if category and category not in show.get("categories", []):
                continue

            show_title_match = q_lower is None or q_lower in show["title"].lower()
            category_text_match = q_lower is not None and any(
                q_lower in c.lower() for c in show.get("categories", [])
            )

            matched_seasons = []
            for season_entry in show["seasons"]:
                matched_episodes = []
                for ep in season_entry["episodes"]:
                    languages = ep["languages"]
                    if language:
                        languages = [l for l in languages if l["language"] == language]
                        if not languages:
                            continue

                    episode_title_match = q_lower is not None and any(
                        q_lower in l["title"].lower() for l in ep["languages"]
                    )

                    if q_lower is not None and not (
                        show_title_match or category_text_match or episode_title_match
                    ):
                        continue

                    matched_episodes.append({**ep, "languages": languages})

                if matched_episodes:
                    matched_seasons.append({**season_entry, "episodes": matched_episodes})

            if not matched_seasons:
                continue

            matched_shows.append({**show, "seasons": matched_seasons})

        if matched_shows:
            matched_sections.append({"section": section_entry["section"], "shows": matched_shows})

    return {
        "generated_at": catalog.get("generated_at"),
        "query": {"q": q, "category": category, "language": language, "section": section},
        "sections": matched_sections,
    }
