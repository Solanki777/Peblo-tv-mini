from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import require_editor
from app.models.season import Season
from app.models.show import Show
from app.models.user import User
from app.schemas.season import SeasonCreate, SeasonResponse


router = APIRouter(
    prefix="/seasons",
    tags=["Seasons"],
)


@router.post("/", response_model=SeasonResponse)
def create_season(
    data: SeasonCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_editor),
):
    show = db.query(Show).filter(Show.id == data.show_id).first()

    if not show:
        raise HTTPException(
            status_code=404,
            detail="Show not found",
        )

    # FIXED: nothing previously stopped two seasons with the same
    # season_number existing under one show, which silently breaks the
    # catalogue builder's "one season entry per season_number" grouping
    # and the viewer's season list. Now enforced here (and at the DB level
    # via a unique constraint - see the migration) with a message an
    # editor can act on.
    duplicate = (
        db.query(Season)
        .filter(Season.show_id == data.show_id, Season.season_number == data.season_number)
        .first()
    )
    if duplicate:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Season {data.season_number} already exists for this show. "
                f"Each season number can only be used once per show."
            ),
        )

    season = Season(
        show_id=data.show_id,
        season_number=data.season_number,
    )

    db.add(season)
    db.commit()
    db.refresh(season)

    return season


@router.get("/", response_model=list[SeasonResponse])
def list_seasons(db: Session = Depends(get_db)):
    return db.query(Season).all()


@router.get("/{season_id}", response_model=SeasonResponse)
def get_season(season_id: int, db: Session = Depends(get_db)):
    season = db.query(Season).filter(
        Season.id == season_id
    ).first()

    if not season:
        raise HTTPException(
            status_code=404,
            detail="Season not found",
        )

    return season


@router.put("/{season_id}", response_model=SeasonResponse)
def update_season(
    season_id: int,
    data: SeasonCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_editor),
):
    season = db.query(Season).filter(
        Season.id == season_id
    ).first()

    if not season:
        raise HTTPException(
            status_code=404,
            detail="Season not found"
        )

    show = db.query(Show).filter(Show.id == data.show_id).first()
    if not show:
        raise HTTPException(status_code=404, detail="Show not found")

    duplicate = (
        db.query(Season)
        .filter(
            Season.show_id == data.show_id,
            Season.season_number == data.season_number,
            Season.id != season_id,
        )
        .first()
    )
    if duplicate:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Season {data.season_number} already exists for this show. "
                f"Each season number can only be used once per show."
            ),
        )

    season.show_id = data.show_id
    season.season_number = data.season_number

    db.commit()
    db.refresh(season)

    return season


@router.delete("/{season_id}")
def delete_season(
    season_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_editor),
):
    season = db.query(Season).filter(
        Season.id == season_id
    ).first()

    if not season:
        raise HTTPException(
            status_code=404,
            detail="Season not found"
        )

    db.delete(season)
    db.commit()

    return {
        "message": "Season deleted successfully"
    }