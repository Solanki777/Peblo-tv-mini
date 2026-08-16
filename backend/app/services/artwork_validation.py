"""Validates an uploaded artwork file against reference.json's specs.

This didn't exist before. app/api/artworks.py used to accept
`width`/`height`/`size_bytes` as plain JSON fields the client supplied
directly - there was no actual file, no image ever opened, and no check
that an image at any given "size" was really that size. That's the
"artwork accepted at any size" failure mode the brief explicitly warns
against.

This module opens the real uploaded bytes with Pillow and checks:
  - it's a real, readable image, in an allowed format (JPEG/PNG)
  - its aspect ratio matches the spec for that artwork_type, within a
    small tolerance
  - its pixel dimensions are close to the spec's target_px, within a
    small tolerance (catches "right aspect ratio, wildly wrong
    resolution" - e.g. a 2x banner, a thumbnail exported at 1/4 size)
  - its byte size is under the spec's max_kb ceiling

Every failure is collected (not just the first one) and returned as a
list of plain-English strings, so an editor sees everything wrong with
one upload in one pass instead of fixing issues one at a time.
"""

from __future__ import annotations

import io
from dataclasses import dataclass

from PIL import Image, UnidentifiedImageError

from app.config import (
    ARTWORK_ASPECT_TOLERANCE,
    ARTWORK_ALLOWED_FORMATS,
    ARTWORK_DIMENSION_TOLERANCE,
    ARTWORK_SPECS,
)


class ArtworkValidationError(Exception):
    """Raised with one or more human-readable, editor-facing messages."""

    def __init__(self, errors: list[str]):
        self.errors = errors
        super().__init__("; ".join(errors))


@dataclass
class ValidatedImage:
    width: int
    height: int
    size_bytes: int
    format: str
    extension: str  # normalized, dot-free (e.g. "jpg", "png")


_EXT_BY_FORMAT = {"JPEG": "jpg", "PNG": "png"}


def validate_artwork_upload(artwork_type: str, data: bytes) -> ValidatedImage:
    """Validate raw upload bytes for the given artwork_type.

    Raises ArtworkValidationError (with one message per problem found) if
    anything is wrong; otherwise returns the measured width/height/size so
    the caller doesn't have to re-derive them from possibly-stale client
    input.
    """
    errors: list[str] = []

    spec = ARTWORK_SPECS.get(artwork_type)
    if spec is None:
        # Caller should have already checked this, but fail loudly rather
        # than silently accepting an unknown type if it slips through.
        raise ArtworkValidationError(
            [f"Unknown artwork type '{artwork_type}'. "
             f"Allowed types: {', '.join(sorted(ARTWORK_SPECS))}."]
        )

    size_bytes = len(data)
    max_bytes = spec["max_kb"] * 1024
    if size_bytes > max_bytes:
        errors.append(
            f"File is {size_bytes / 1024:.0f} KB, which is over the "
            f"{spec['max_kb']} KB limit for {artwork_type} images. "
            f"Try a more compressed export."
        )

    try:
        image = Image.open(io.BytesIO(data))
        image.verify()  # raises if the file is truncated/corrupt
        # verify() leaves the file object unusable for further reads, so
        # re-open it to actually inspect dimensions/format below.
        image = Image.open(io.BytesIO(data))
        width, height = image.size
        img_format = (image.format or "").upper()
    except (UnidentifiedImageError, OSError):
        raise ArtworkValidationError(
            [f"This doesn't look like a valid image file. "
             f"Please upload a JPEG or PNG."]
        )

    if img_format not in ARTWORK_ALLOWED_FORMATS:
        errors.append(
            f"Image format '{img_format or 'unknown'}' isn't supported. "
            f"Please upload a JPEG or PNG."
        )

    target_w, target_h = spec["target_px"]
    target_aspect = target_w / target_h

    if height > 0:
        actual_aspect = width / height
        aspect_diff = abs(actual_aspect - target_aspect) / target_aspect
        if aspect_diff > ARTWORK_ASPECT_TOLERANCE:
            errors.append(
                f"Wrong aspect ratio for {artwork_type}: got {width}x{height} "
                f"(~{actual_aspect:.2f}:1), expected close to "
                f"{target_w}x{target_h} (~{target_aspect:.2f}:1)."
            )

    width_diff = abs(width - target_w) / target_w
    height_diff = abs(height - target_h) / target_h
    if width_diff > ARTWORK_DIMENSION_TOLERANCE or height_diff > ARTWORK_DIMENSION_TOLERANCE:
        errors.append(
            f"Wrong size for {artwork_type}: got {width}x{height}px, expected "
            f"close to {target_w}x{target_h}px (within "
            f"{int(ARTWORK_DIMENSION_TOLERANCE * 100)}%). "
            f"Re-export at the target resolution and try again."
        )

    if errors:
        raise ArtworkValidationError(errors)

    return ValidatedImage(
        width=width,
        height=height,
        size_bytes=size_bytes,
        format=img_format,
        extension=_EXT_BY_FORMAT.get(img_format, "bin"),
    )