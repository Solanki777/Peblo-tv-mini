"""Unit tests for app/services/artwork_validation.py.

This is the module standing between "editor uploads a file" and "we
trust its dimensions" - it's the direct fix for the brief's explicit
warning against "artwork accepted at any size", so it gets tested in
isolation from the API/DB layer.
"""

from __future__ import annotations

import io

import pytest
from PIL import Image

from app.services.artwork_validation import ArtworkValidationError, validate_artwork_upload
from tests.conftest import make_image_bytes


def test_valid_poster_passes():
    data = make_image_bytes(600, 900)
    result = validate_artwork_upload("poster", data)
    assert result.width == 600
    assert result.height == 900
    assert result.extension == "png"


def test_valid_within_tolerance_passes():
    # 5% off target on both axes - inside the 10% dimension tolerance
    # and well inside the 2% aspect tolerance (scaling both dimensions
    # equally preserves aspect ratio exactly).
    data = make_image_bytes(630, 945)
    result = validate_artwork_upload("poster", data)
    assert result.width == 630


def test_wrong_aspect_ratio_rejected():
    # Square image submitted as a poster (should be 2:3).
    data = make_image_bytes(800, 800)
    with pytest.raises(ArtworkValidationError) as exc_info:
        validate_artwork_upload("poster", data)
    assert any("aspect ratio" in e.lower() for e in exc_info.value.errors)


def test_wrong_resolution_rejected_even_with_right_aspect():
    # Half-size banner: right aspect ratio (16:9), wrong resolution.
    data = make_image_bytes(640, 360)
    with pytest.raises(ArtworkValidationError) as exc_info:
        validate_artwork_upload("banner", data)
    assert any("wrong size" in e.lower() for e in exc_info.value.errors)


def test_file_too_large_rejected():
    data = make_image_bytes(600, 900, noisy=True)
    assert len(data) > 200 * 1024
    with pytest.raises(ArtworkValidationError) as exc_info:
        validate_artwork_upload("poster", data)
    assert any("kb" in e.lower() for e in exc_info.value.errors)


def test_corrupt_file_rejected():
    with pytest.raises(ArtworkValidationError) as exc_info:
        validate_artwork_upload("poster", b"this is not an image")
    assert any("valid image" in e.lower() for e in exc_info.value.errors)


def test_unknown_artwork_type_rejected():
    data = make_image_bytes(600, 900)
    with pytest.raises(ArtworkValidationError):
        validate_artwork_upload("background", data)


def test_multiple_problems_all_reported_at_once():
    # Wrong aspect AND (for thumbnail) wrong resolution in one file -
    # an editor should see both problems in a single round trip, not
    # fix-and-resubmit one at a time.
    data = make_image_bytes(100, 100)
    with pytest.raises(ArtworkValidationError) as exc_info:
        validate_artwork_upload("thumbnail", data)
    assert len(exc_info.value.errors) >= 2


def test_jpeg_is_allowed():
    img = Image.new("RGB", (1280, 720), (10, 20, 30))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    result = validate_artwork_upload("banner", buf.getvalue())
    assert result.extension == "jpg"
