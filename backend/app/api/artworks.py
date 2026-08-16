"""Artwork upload + CRUD.

FIXED (see README "what was wrong" for the full list): this router used to
have a `POST /artworks/` that took `width`, `height`, and `size_bytes` as
plain JSON fields typed by the client - no file, no image ever opened, no
check that those numbers were true. That's the exact failure mode the
brief calls out ("artwork accepted at any size"). It also had no auth on
any route, so anyone with network access to the API - not just editors -
could create/edit/delete artwork records.

What changed:
  - POST /artworks/upload is the only way to create or replace an artwork
    now. It's a real multipart upload (episode_id + artwork_type as form
    fields, file as a file field). The bytes are opened with Pillow,
    checked against reference.json's per-type spec (aspect ratio,
    dimensions, max_kb - see services/artwork_validation.py), and only
    written to storage if they pass. width/height/size_bytes on the
    resulting record are always what was measured, never what the client
    claimed.
  - Uploading again for the same (episode_id, artwork_type) replaces the
    existing artwork (upsert) rather than erroring - that's the natural
    "editor picked the wrong file, re-uploads the right one" flow, and
    matches the CMS's edit-in-place artwork slots.
  - All mutating routes require an authenticated user (editor or admin).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.config import ARTWORK_SPECS
from app.database import get_db
from app.deps import require_editor
from app.models.artwork import Artwork
from app.models.episode import Episode
from app.models.user import User
from app.schemas.artwork import ArtworkResponse
from app.services.artwork_validation import ArtworkValidationError, validate_artwork_upload
from app.services.storage import get_storage

router = APIRouter(
    prefix="/artworks",
    tags=["Artwork"],
)


def _storage_key(episode_pk: int, artwork_type: str, extension: str) -> str:
    return f"artworks/{episode_pk}/{artwork_type}.{extension}"


@router.post("/upload", response_model=ArtworkResponse)
async def upload_artwork(
    episode_id: int = Form(..., description="Internal episode id (Episode.id)"),
    artwork_type: str = Form(..., description="poster | banner | thumbnail"),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_editor),
):
    episode = db.query(Episode).filter(Episode.id == episode_id).first()
    if not episode:
        raise HTTPException(status_code=404, detail="Episode not found")

    if artwork_type not in ARTWORK_SPECS:
        raise HTTPException(
            status_code=422,
            detail=(
                f"'{artwork_type}' isn't a valid artwork type. "
                f"Allowed: {', '.join(sorted(ARTWORK_SPECS))}."
            ),
        )

    data = await file.read()
    if not data:
        raise HTTPException(status_code=422, detail="Uploaded file is empty.")

    try:
        validated = validate_artwork_upload(artwork_type, data)
    except ArtworkValidationError as exc:
        # 422 (not 400): the request is well-formed, the *content* fails
        # validation. errors is a list so the CMS can show every problem
        # at once rather than making the editor fix-and-resubmit repeatedly.
        raise HTTPException(status_code=422, detail={"errors": exc.errors})

    new_key = _storage_key(episode.id, artwork_type, validated.extension)
    storage = get_storage()
    storage.write_bytes(new_key, data)

    existing = (
        db.query(Artwork)
        .filter(Artwork.episode_id == episode.id, Artwork.artwork_type == artwork_type)
        .first()
    )

    if existing:
        old_key = existing.storage_key
        existing.storage_key = new_key
        existing.width = validated.width
        existing.height = validated.height
        existing.size_bytes = validated.size_bytes
        artwork = existing
        if old_key != new_key:
            # e.g. replacing a .png with a .jpg - don't leave the old file
            # behind under a key nothing references anymore.
            storage.delete(old_key)
    else:
        artwork = Artwork(
            episode_id=episode.id,
            artwork_type=artwork_type,
            storage_key=new_key,
            width=validated.width,
            height=validated.height,
            size_bytes=validated.size_bytes,
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
    artwork = db.query(Artwork).filter(Artwork.id == artwork_id).first()

    if not artwork:
        raise HTTPException(
            status_code=404,
            detail="Artwork not found",
        )

    return artwork


@router.delete("/{artwork_id}")
def delete_artwork(
    artwork_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_editor),
):
    artwork = db.query(Artwork).filter(Artwork.id == artwork_id).first()

    if not artwork:
        raise HTTPException(
            status_code=404,
            detail="Artwork not found",
        )

    storage = get_storage()
    storage.delete(artwork.storage_key)

    db.delete(artwork)
    db.commit()

    return {
        "message": "Artwork deleted successfully",
    }