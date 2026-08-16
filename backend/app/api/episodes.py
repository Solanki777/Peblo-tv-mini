from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import require_editor
from app.models.artwork import Artwork
from app.models.episode import Episode
from app.models.season import Season
from app.models.show import Show
from app.models.user import User
from app.schemas.episode import EpisodeCreate, EpisodeResponse

router = APIRouter(
    prefix="/episodes",
    tags=["Episodes"],
)

REQUIRED_ARTWORK_TYPES = {"poster", "banner", "thumbnail"}


def _publish_blockers(
    db: Session,
    show: Show,
    duration_seconds: int | None,
    episode_pk: int | None,
) -> list[str]:
    """What's stopping this episode from being marked published.

    FIXED: previously nothing stopped `PUT /episodes/{id}` from setting
    status="published" on an episode with no duration and no artwork - the
    brief's "an episode can't be published without artwork and a
    duration" rule only existed later, at publish-job time
    (services/validation.py), where a non-compliant episode was silently
    dropped from the catalogue rather than the edit being rejected. That's
    still useful as a safety net (kept as-is), but an editor deserves to
    know *at the moment they try to publish an episode* why it won't take,
    not after they've moved on and it quietly never showed up in Netflix-
    style browse.
    """
    blockers: list[str] = []

    if duration_seconds is None:
        blockers.append("Duration is required before this episode can be published.")

    if not show.section:
        blockers.append(
            "This episode's show has no section yet - add one before publishing episodes in it."
        )

    if episode_pk is not None:
        present_types = {
            a.artwork_type
            for a in db.query(Artwork).filter(Artwork.episode_id == episode_pk).all()
        }
    else:
        # Brand new episode: it can't have artwork yet (artwork upload
        # requires an existing episode_id), so this will always block a
        # create-as-published in one step - which is correct: create as
        # draft, add artwork, then publish.
        present_types = set()

    missing = sorted(REQUIRED_ARTWORK_TYPES - present_types)
    if missing:
        blockers.append(f"Missing artwork: {', '.join(missing)}.")

    return blockers


@router.post("/", response_model=EpisodeResponse)
def create_episode(
    data: EpisodeCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_editor),
):
    season = db.query(Season).filter(
        Season.id == data.season_id
    ).first()

    if not season:
        raise HTTPException(
            status_code=404,
            detail="Season not found",
        )

    show = db.query(Show).filter(Show.id == season.show_id).first()

    existing_episode = db.query(Episode).filter(
        Episode.episode_id == data.episode_id
    ).first()

    if existing_episode:
        raise HTTPException(
            status_code=400,
            detail="Episode ID already exists",
        )

    existing_content = db.query(Episode).filter(
        Episode.content_group == data.content_group,
        Episode.language == data.language,
    ).first()

    if existing_content:
        raise HTTPException(
            status_code=400,
            detail="This content group already exists for this language",
        )

    if data.status == "published":
        blockers = _publish_blockers(db, show, data.duration_seconds, episode_pk=None)
        if blockers:
            raise HTTPException(status_code=422, detail={"errors": blockers})

    episode = Episode(
        episode_id=data.episode_id,
        season_id=data.season_id,
        episode_number=data.episode_number,
        title=data.title,
        duration_seconds=data.duration_seconds,
        language=data.language,
        content_group=data.content_group,
        status=data.status,
    )

    db.add(episode)
    db.commit()
    db.refresh(episode)

    return episode


@router.get("/", response_model=list[EpisodeResponse])
def list_episodes(db: Session = Depends(get_db)):
    return db.query(Episode).all()


@router.get("/lookup/{episode_code}", response_model=EpisodeResponse)
def get_episode_by_code(
    episode_code: str,
    db: Session = Depends(get_db),
):
    """Look up by the human-readable business key (Episode.episode_id),
    e.g. from a CMS deep link. Separate path from `/{episode_id}` below,
    which is the internal numeric id used everywhere else (list, edit,
    delete) - see FIXED note on that route for why they used to collide.
    """
    episode = db.query(Episode).filter(
        Episode.episode_id == episode_code
    ).first()

    if not episode:
        raise HTTPException(
            status_code=404,
            detail="Episode not found",
        )

    return episode


@router.get("/{episode_id}", response_model=EpisodeResponse)
def get_episode(
    episode_id: int,
    db: Session = Depends(get_db),
):
    # FIXED: this used to take a *string* and look up by the business-key
    # Episode.episode_id, while PUT/DELETE on this exact same path took an
    # int and looked up by the internal primary key - same URL shape,
    # two different meanings depending on HTTP method. Now consistent
    # with PUT/DELETE (internal id); business-key lookup moved to
    # /episodes/lookup/{episode_code} above.
    episode = db.query(Episode).filter(
        Episode.id == episode_id
    ).first()

    if not episode:
        raise HTTPException(
            status_code=404,
            detail="Episode not found",
        )

    return episode


@router.put("/{episode_id}", response_model=EpisodeResponse)
def update_episode(
    episode_id: int,
    data: EpisodeCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_editor),
):
    episode = db.query(Episode).filter(
        Episode.id == episode_id
    ).first()

    if not episode:
        raise HTTPException(
            status_code=404,
            detail="Episode not found"
        )

    season = db.query(Season).filter(Season.id == data.season_id).first()
    if not season:
        raise HTTPException(status_code=404, detail="Season not found")
    show = db.query(Show).filter(Show.id == season.show_id).first()

    # FIXED: update previously did zero uniqueness checking, so editing an
    # episode to reuse another episode's episode_id, or another episode's
    # (content_group, language) pair, hit the DB's unique constraint and
    # surfaced as a raw 500 instead of a clean, actionable 400.
    id_conflict = (
        db.query(Episode)
        .filter(Episode.episode_id == data.episode_id, Episode.id != episode_id)
        .first()
    )
    if id_conflict:
        raise HTTPException(status_code=400, detail="Episode ID already exists")

    content_conflict = (
        db.query(Episode)
        .filter(
            Episode.content_group == data.content_group,
            Episode.language == data.language,
            Episode.id != episode_id,
        )
        .first()
    )
    if content_conflict:
        raise HTTPException(
            status_code=400,
            detail="This content group already exists for this language",
        )

    if data.status == "published":
        blockers = _publish_blockers(
            db, show, data.duration_seconds, episode_pk=episode_id
        )
        if blockers:
            raise HTTPException(status_code=422, detail={"errors": blockers})

    episode.episode_id = data.episode_id
    episode.season_id = data.season_id
    episode.episode_number = data.episode_number
    episode.title = data.title
    episode.duration_seconds = data.duration_seconds
    episode.language = data.language
    episode.content_group = data.content_group
    episode.status = data.status

    db.commit()
    db.refresh(episode)

    return episode


@router.delete("/{episode_id}")
def delete_episode(
    episode_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_editor),
):
    episode = db.query(Episode).filter(
        Episode.id == episode_id
    ).first()

    if not episode:
        raise HTTPException(
            status_code=404,
            detail="Episode not found"
        )

    db.delete(episode)
    db.commit()

    return {
        "message": "Episode deleted successfully"
    }