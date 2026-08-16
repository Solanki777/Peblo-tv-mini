from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import require_editor
from app.models.show import Show
from app.models.user import User
from app.schemas.show import ShowCreate, ShowResponse

router = APIRouter(
    prefix="/shows",
    tags=["Shows"],
)


@router.post("/", response_model=ShowResponse)
def create_show(
    data: ShowCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_editor),
):
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


@router.put("/{show_id}", response_model=ShowResponse)
def update_show(
    show_id: int,
    data: ShowCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_editor),
):
    show = db.query(Show).filter(
        Show.id == show_id
    ).first()

    if not show:
        raise HTTPException(
            status_code=404,
            detail="Show not found"
        )

    # FIXED: this used to check nothing, so renaming show A's slug to
    # show B's existing slug would 500 on the DB's unique constraint
    # instead of returning a clean, editor-readable error. Now it checks
    # the same way create does, excluding the row being edited so a show
    # can keep its own slug.
    slug_conflict = (
        db.query(Show)
        .filter(Show.slug == data.slug, Show.id != show_id)
        .first()
    )
    if slug_conflict:
        raise HTTPException(
            status_code=400,
            detail="A show with this slug already exists",
        )

    show.title = data.title
    show.slug = data.slug
    show.section = data.section
    show.synopsis = data.synopsis
    show.categories = data.categories

    db.commit()
    db.refresh(show)

    return show


@router.delete("/{show_id}")
def delete_show(
    show_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_editor),
):
    show = db.query(Show).filter(
        Show.id == show_id
    ).first()

    if not show:
        raise HTTPException(
            status_code=404,
            detail="Show not found"
        )

    db.delete(show)
    db.commit()

    return {
        "message": "Show deleted successfully"
    }