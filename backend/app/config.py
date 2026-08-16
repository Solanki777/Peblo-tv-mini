import os

from dotenv import load_dotenv

load_dotenv()

# Root directory the storage abstraction writes to. In docker-compose this
# should be a mounted volume shared between the API container and (if you
# ever add one) a static file server. Locally it defaults to a `storage`
# folder at the repo root so it's easy to poke at while developing.
STORAGE_ROOT = os.getenv(
    "STORAGE_ROOT",
    os.path.join(os.path.dirname(__file__), "..", "..", "storage"),
)

# Key (path, relative to STORAGE_ROOT) the published catalogue is written to.
CATALOG_KEY = os.getenv("CATALOG_KEY", "catalog/catalog.json")

# --------------------------------------------------------------------------
# Auth
# --------------------------------------------------------------------------
# FIXED: this used to be hardcoded in app/auth.py. That means it shipped in
# source control and was identical across every environment (dev, CI, prod)
# - anyone with the repo could forge tokens for any user. It now comes from
# the environment, with a dev-only fallback so a fresh clone still boots
# without extra setup. Set a real SECRET_KEY in .env for anything other than
# local development.
SECRET_KEY = os.getenv("SECRET_KEY", "dev-only-insecure-secret-change-me")
ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))

# --------------------------------------------------------------------------
# Artwork specs
# --------------------------------------------------------------------------
# Mirrors seed/reference.json -> artwork_specs. Kept here (rather than read
# from the JSON file at request time) so upload validation doesn't depend on
# a file path being correct in every environment; if reference.json changes,
# update this alongside it. aspect_ratio is target width / target height,
# derived from target_px so the two can never drift apart.
ARTWORK_SPECS = {
    "poster": {"target_px": (600, 900), "max_kb": 200},
    "banner": {"target_px": (1280, 720), "max_kb": 200},
    "thumbnail": {"target_px": (640, 360), "max_kb": 200},
}

# How far an upload's dimensions may deviate from target_px and still be
# accepted, as a fraction of the target (e.g. 0.10 = +/-10%). Real editor
# uploads are rarely pixel-perfect (a slightly different export size,
# different DPI, etc.), so a small band avoids rejecting good images -
# while still catching the "wrong asset entirely" cases (an image at 2x or
# 0.25x the target, a different aspect ratio) that the brief calls out.
ARTWORK_DIMENSION_TOLERANCE = 0.10

# Independent aspect-ratio tolerance (fraction). Checked separately from
# dimension tolerance because an image can be "close enough" in raw pixel
# size while still having a visibly wrong aspect ratio (e.g. a slightly
# cropped upload) - the two errors are reported differently to the editor.
ARTWORK_ASPECT_TOLERANCE = 0.02

ARTWORK_ALLOWED_FORMATS = {"JPEG", "PNG"}