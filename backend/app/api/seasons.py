from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.season import Season
from app.models.show import Show
from app.schemas.season import SeasonCreate, SeasonResponse


router = APIRouter(
    prefix="/seasons",
    tags=["Seasons"],
)


@router.post("/", response_model=SeasonResponse)
def create_season(data: SeasonCreate, db: Session = Depends(get_db)):
    show = db.query(Show).filter(Show.id == data.show_id).first()

    if not show:
        raise HTTPException(
            status_code=404,
            detail="Show not found",
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


@router.put("/{season_id}")
def update_season(
    season_id: int,
    data: SeasonCreate,
    db: Session = Depends(get_db)
):
    season = db.query(Season).filter(
        Season.id == season_id
    ).first()

    if not season:
        raise HTTPException(
            status_code=404,
            detail="Season not found"
        )

    season.show_id = data.show_id
    season.season_number = data.season_number

    db.commit()
    db.refresh(season)

    return season



@router.delete("/{season_id}")
def delete_season(
    season_id: int,
    db: Session = Depends(get_db)
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