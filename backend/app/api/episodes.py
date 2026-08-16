from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.episode import Episode
from app.models.season import Season
from app.schemas.episode import EpisodeCreate, EpisodeResponse


router = APIRouter(
    prefix="/episodes",
    tags=["Episodes"],
)


@router.post("/", response_model=EpisodeResponse)
def create_episode(
    data: EpisodeCreate,
    db: Session = Depends(get_db),
):
    # Check that the season exists
    season = db.query(Season).filter(
        Season.id == data.season_id
    ).first()

    if not season:
        raise HTTPException(
            status_code=404,
            detail="Season not found",
        )

    # Check unique episode_id
    existing_episode = db.query(Episode).filter(
        Episode.episode_id == data.episode_id
    ).first()

    if existing_episode:
        raise HTTPException(
            status_code=400,
            detail="Episode ID already exists",
        )

    # Check content_group + language uniqueness
    existing_content = db.query(Episode).filter(
        Episode.content_group == data.content_group,
        Episode.language == data.language,
    ).first()

    if existing_content:
        raise HTTPException(
            status_code=400,
            detail="This content group already exists for this language",
        )

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


@router.get("/{episode_id}", response_model=EpisodeResponse)
def get_episode(
    episode_id: str,
    db: Session = Depends(get_db),
):
    episode = db.query(Episode).filter(
        Episode.episode_id == episode_id
    ).first()

    if not episode:
        raise HTTPException(
            status_code=404,
            detail="Episode not found",
        )

    return episode