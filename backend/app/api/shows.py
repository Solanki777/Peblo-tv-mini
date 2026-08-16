from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.show import Show
from app.schemas.show import ShowCreate, ShowResponse


router = APIRouter(
    prefix="/shows",
    tags=["Shows"],
)


@router.post("/", response_model=ShowResponse)
def create_show(data: ShowCreate, db: Session = Depends(get_db)):
    existing_show = db.query(Show).filter(
        Show.slug == data.slug
    ).first()

    if existing_show:
        raise HTTPException(
            status_code=400,
            detail="A show with this slug already exists",
        )

    show = Show(
        title=data.title,
        slug=data.slug,
        section=data.section,
        synopsis=data.synopsis,
        categories=data.categories,
    )

    db.add(show)
    db.commit()
    db.refresh(show)

    return show


@router.get("/", response_model=list[ShowResponse])
def list_shows(db: Session = Depends(get_db)):
    return db.query(Show).all()


@router.get("/{show_id}", response_model=ShowResponse)
def get_show(show_id: int, db: Session = Depends(get_db)):
    show = db.query(Show).filter(Show.id == show_id).first()

    if not show:
        raise HTTPException(
            status_code=404,
            detail="Show not found",
        )

    return show