from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.artwork import Artwork
from app.models.episode import Episode
from app.schemas.artwork import ArtworkCreate, ArtworkResponse


router = APIRouter(
    prefix="/artworks",
    tags=["Artwork"],
)


@router.post("/", response_model=ArtworkResponse)
def create_artwork(
    data: ArtworkCreate,
    db: Session = Depends(get_db),
):
    # Check that the episode exists
    episode = db.query(Episode).filter(
        Episode.id == data.episode_id
    ).first()

    if not episode:
        raise HTTPException(
            status_code=404,
            detail="Episode not found",
        )

    # One artwork of each type per episode
    existing_artwork = db.query(Artwork).filter(
        Artwork.episode_id == data.episode_id,
        Artwork.artwork_type == data.artwork_type,
    ).first()

    if existing_artwork:
        raise HTTPException(
            status_code=400,
            detail="This artwork type already exists for this episode",
        )

    artwork = Artwork(
        episode_id=data.episode_id,
        artwork_type=data.artwork_type,
        storage_key=data.storage_key,
        width=data.width,
        height=data.height,
        size_bytes=data.size_bytes,
    )

    db.add(artwork)
    db.commit()
    db.refresh(artwork)

    return artwork


@router.get("/", response_model=list[ArtworkResponse])
def list_artworks(db: Session = Depends(get_db)):
    return db.query(Artwork).all()


@router.get("/{artwork_id}", response_model=ArtworkResponse)
def get_artwork(
    artwork_id: int,
    db: Session = Depends(get_db),
):
    artwork = db.query(Artwork).filter(
        Artwork.id == artwork_id
    ).first()

    if not artwork:
        raise HTTPException(
            status_code=404,
            detail="Artwork not found",
        )

    return artwork

@router.put("/{artwork_id}")
def update_artwork(
    artwork_id: int,
    data: ArtworkCreate,
    db: Session = Depends(get_db)
):
    artwork = db.query(Artwork).filter(
        Artwork.id == artwork_id
    ).first()

    if not artwork:
        raise HTTPException(
            status_code=404,
            detail="Artwork not found"
        )

    artwork.episode_id = data.episode_id
    artwork.artwork_type = data.artwork_type
    artwork.storage_key = data.storage_key
    artwork.width = data.width
    artwork.height = data.height
    artwork.size_bytes = data.size_bytes

    db.commit()
    db.refresh(artwork)

    return artwork


@router.delete("/{artwork_id}")
def delete_artwork(
    artwork_id: int,
    db: Session = Depends(get_db)
):
    artwork = db.query(Artwork).filter(
        Artwork.id == artwork_id
    ).first()

    if not artwork:
        raise HTTPException(
            status_code=404,
            detail="Artwork not found"
        )

    db.delete(artwork)
    db.commit()

    return {
        "message": "Artwork deleted successfully"
    }