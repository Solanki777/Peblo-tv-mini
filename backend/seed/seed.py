"""Seeds the Peblo TV Mini API from seed/data/seed_shows.json.

Design choice: this goes through the *real* HTTP API (auth, CRUD,
artwork upload) rather than writing to the database directly, with one
deliberate exception - bootstrapping the first admin user. There's no API
endpoint that lets you create an admin (registration always creates
"editor" - see app/api/auth.py), and there shouldn't be one; that would
be a privilege-escalation hole. So the *one* place this script touches
the database directly is promoting a single bootstrap user to admin.
Everything else - shows, seasons, episodes, artwork uploads, and the
final publish - happens exactly the way an editor using the CMS would do
it, which means it also exercises the real validation rules.

The seed data (seed/data/seed_shows.json) is the brief's provided
seed_shows.json, deliberately imperfect. This script does NOT clean it
up before loading - it feeds it in as-is and lets the real API reject or
flag what it should, then prints a summary of what it found. That's the
point of the exercise: the API's validation is what's supposed to catch
this, not the seed script.

Known issues in the provided seed data, confirmed by inspection and left
for the API to catch:
  - ep_9001 ("The Lost Kite (v2)") claims (content_group, language) =
    (motis-many-lives-s01e02, hi), which ep_0004 already has. The unique
    constraint (and the API's pre-check) rejects the second one; this
    script logs it as a conflict and moves on rather than crashing.
  - ep_0036, ep_0093, ep_0094 are marked status="published" but their
    artwork_available list doesn't cover all three required types. This
    script uploads whatever artwork *is* listed, then tries to publish
    the episode same as any "published" row - the attempt is rejected by
    the publish-blocker check (missing artwork), so the episode is left
    as a draft with an artwork gap. It'll show up in
    GET /admin/validation-report and be excluded from the catalogue,
    exactly as it should be.
  - Every "Rhyme Rangers" episode has section=null on its show and is
    status="draft" in the source data. That's left exactly as given -
    the show is created with no section. If you flip one of its episodes
    to "published" from the CMS, you'll see the "show missing a section"
    check fire. Nothing to fix here; it's a live demo of that rule, not
    a bug.

Usage (inside the backend container / venv, with the API already
running and reachable):

    python -m seed.seed
    # or: python seed/seed.py

Environment variables:
    API_BASE_URL            default http://localhost:8000
    DATABASE_URL             required (same one the API uses) - for the
                              one-time admin bootstrap only
    SEED_ADMIN_USERNAME       default "admin"
    SEED_ADMIN_PASSWORD       default "admin12345"
    SEED_EDITOR_USERNAME      default "editor"
    SEED_EDITOR_PASSWORD      default "editor12345"

Idempotent-ish: safe to re-run. Users/shows/seasons/episodes that
already exist are detected (via the API's own 400s, or a lookup) and
skipped rather than duplicated. It does not attempt to reconcile drift
in existing rows - it just leaves them alone.
"""

from __future__ import annotations

import io
import json
import os
import sys
import time
from pathlib import Path

import requests
from PIL import Image, ImageDraw

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000").rstrip("/")

ADMIN_USERNAME = os.getenv("SEED_ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("SEED_ADMIN_PASSWORD", "admin12345")
EDITOR_USERNAME = os.getenv("SEED_EDITOR_USERNAME", "editor")
EDITOR_PASSWORD = os.getenv("SEED_EDITOR_PASSWORD", "editor12345")

DATA_DIR = Path(__file__).parent / "data"
SEED_SHOWS_PATH = DATA_DIR / "seed_shows.json"
REFERENCE_PATH = DATA_DIR / "reference.json"

REQUIRED_ARTWORK_TYPES = ["poster", "banner", "thumbnail"]


# --------------------------------------------------------------------------
# Small helpers
# --------------------------------------------------------------------------


def _log(msg: str) -> None:
    print(f"[seed] {msg}", flush=True)


def wait_for_api(timeout_seconds: int = 60) -> None:
    deadline = time.time() + timeout_seconds
    last_error = None
    while time.time() < deadline:
        try:
            resp = requests.get(f"{API_BASE_URL}/health", timeout=3)
            if resp.status_code == 200:
                _log(f"API is up at {API_BASE_URL}")
                return
        except requests.RequestException as exc:
            last_error = exc
        time.sleep(2)
    raise SystemExit(f"API never became healthy at {API_BASE_URL}: {last_error}")


def bootstrap_admin() -> None:
    """The one direct-DB step. See module docstring for why."""
    from sqlalchemy import text

    from app.database import SessionLocal
    from app.auth import hash_password
    from app.models.user import User

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == ADMIN_USERNAME).first()
        if user is None:
            _log(f"Creating admin user '{ADMIN_USERNAME}' directly (bootstrap)")
            user = User(
                username=ADMIN_USERNAME,
                password_hash=hash_password(ADMIN_PASSWORD),
                role="admin",
            )
            db.add(user)
            db.commit()
        elif user.role != "admin":
            _log(f"Promoting existing user '{ADMIN_USERNAME}' to admin")
            db.execute(
                text("UPDATE users SET role = 'admin' WHERE id = :id"),
                {"id": user.id},
            )
            db.commit()
        else:
            _log(f"Admin user '{ADMIN_USERNAME}' already present")
    finally:
        db.close()


def register_if_missing(username: str, password: str) -> None:
    resp = requests.post(
        f"{API_BASE_URL}/auth/register",
        json={"username": username, "password": password},
    )
    if resp.status_code == 200:
        _log(f"Registered user '{username}'")
    elif resp.status_code == 400:
        _log(f"User '{username}' already exists, skipping")
    else:
        resp.raise_for_status()


def login(username: str, password: str) -> str:
    resp = requests.post(
        f"{API_BASE_URL}/auth/login",
        json={"username": username, "password": password},
    )
    resp.raise_for_status()
    return resp.json()["access_token"]


def make_placeholder_image(artwork_type: str, spec: dict, label: str) -> bytes:
    """Generates a real, correctly-sized/aspect PNG for seeding artwork.

    We weren't given the brief's assets/ folder (the CMS-uploaded sample
    images), so this stands in for it - a solid-colour PNG at exactly
    spec['target_px'], labelled with the artwork type and episode/show
    name, comfortably under the 200KB ceiling. It's generated fresh per
    upload and sent through the real POST /artworks/upload endpoint, so
    it's validated by the same Pillow-based checks (aspect ratio,
    dimensions, size) as a real editor upload would be - nothing here
    bypasses that.
    """
    width, height = spec["target_px"]
    colors = {
        "poster": (196, 92, 71),
        "banner": (60, 110, 150),
        "thumbnail": (90, 140, 90),
    }
    img = Image.new("RGB", (width, height), colors.get(artwork_type, (120, 120, 120)))
    draw = ImageDraw.Draw(img)
    text = f"{artwork_type}\n{label}\n{width}x{height}"
    draw.multiline_text((20, 20), text, fill=(255, 255, 255))
    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return buf.getvalue()


class Api:
    def __init__(self, token: str):
        self.session = requests.Session()
        self.session.headers["Authorization"] = f"Bearer {token}"

    def get(self, path: str, **kw):
        return self.session.get(f"{API_BASE_URL}{path}", **kw)

    def post(self, path: str, **kw):
        return self.session.post(f"{API_BASE_URL}{path}", **kw)

    def put(self, path: str, **kw):
        return self.session.put(f"{API_BASE_URL}{path}", **kw)


# --------------------------------------------------------------------------
# Main seeding flow
# --------------------------------------------------------------------------


def run() -> None:
    if not SEED_SHOWS_PATH.exists():
        raise SystemExit(f"Missing {SEED_SHOWS_PATH} - nothing to seed.")

    rows = json.loads(SEED_SHOWS_PATH.read_text())
    reference = json.loads(REFERENCE_PATH.read_text()) if REFERENCE_PATH.exists() else {}
    artwork_specs = reference.get("artwork_specs", {
        "poster": {"target_px": [600, 900]},
        "banner": {"target_px": [1280, 720]},
        "thumbnail": {"target_px": [640, 360]},
    })

    wait_for_api()
    bootstrap_admin()
    register_if_missing(EDITOR_USERNAME, EDITOR_PASSWORD)

    admin_token = login(ADMIN_USERNAME, ADMIN_PASSWORD)
    api = Api(admin_token)

    conflicts: list[str] = []
    publish_blocked: list[str] = []
    created_shows = created_seasons = created_episodes = uploaded_artwork = 0

    # --- shows -------------------------------------------------------
    shows_seen: dict[str, dict] = {}
    for row in rows:
        shows_seen.setdefault(
            row["slug"],
            {
                "title": row["show_title"],
                "slug": row["slug"],
                "section": row["section"],
                "synopsis": row["synopsis"],
                "categories": ",".join(row["categories"]),
            },
        )

    existing_shows = {s["slug"]: s for s in api.get("/shows/").json()}
    for slug, payload in shows_seen.items():
        if slug in existing_shows:
            continue
        resp = api.post("/shows/", json=payload)
        if resp.status_code == 200:
            created_shows += 1
        else:
            _log(f"Could not create show '{slug}': {resp.text}")
    show_by_slug = {s["slug"]: s for s in api.get("/shows/").json()}

    # --- seasons -------------------------------------------------------
    seasons_seen: set[tuple[str, int]] = {
        (row["slug"], row["season_number"]) for row in rows
    }
    existing_seasons = api.get("/seasons/").json()
    existing_season_keys = {
        (s["show_id"], s["season_number"]) for s in existing_seasons
    }
    for slug, season_number in sorted(seasons_seen):
        show = show_by_slug.get(slug)
        if not show:
            continue
        if (show["id"], season_number) in existing_season_keys:
            continue
        resp = api.post(
            "/seasons/", json={"show_id": show["id"], "season_number": season_number}
        )
        if resp.status_code == 200:
            created_seasons += 1
        else:
            _log(f"Could not create season {season_number} for '{slug}': {resp.text}")

    season_by_key = {
        (s["show_id"], s["season_number"]): s for s in api.get("/seasons/").json()
    }

    # --- episodes + artwork ---------------------------------------------
    existing_episode_ids = {e["episode_id"] for e in api.get("/episodes/").json()}

    for row in sorted(rows, key=lambda r: r["episode_id"]):
        show = show_by_slug.get(row["slug"])
        season = season_by_key.get((show["id"], row["season_number"])) if show else None
        if not show or not season:
            _log(f"Skipping {row['episode_id']}: show/season not resolved")
            continue

        if row["episode_id"] in existing_episode_ids:
            continue  # already seeded on a previous run

        create_payload = {
            "episode_id": row["episode_id"],
            "season_id": season["id"],
            "episode_number": row["episode_number"],
            "title": row["episode_title"],
            "duration_seconds": row["duration_seconds"],
            "language": row["language"],
            "content_group": row["content_group"],
            # Always create as draft first - artwork can't exist before
            # the episode does, so a same-step "create as published" would
            # always fail the artwork check even for good rows.
            "status": "draft",
        }
        resp = api.post("/episodes/", json=create_payload)
        if resp.status_code != 200:
            detail = resp.json().get("detail", resp.text)
            conflicts.append(f"{row['episode_id']} ({row['episode_title']}): {detail}")
            continue

        episode = resp.json()
        created_episodes += 1

        for artwork_type in row.get("artwork_available", []):
            spec = artwork_specs.get(artwork_type)
            if not spec:
                continue
            image_bytes = make_placeholder_image(
                artwork_type, spec, f"{row['show_title']} - {row['episode_title']}"
            )
            resp = api.post(
                "/artworks/upload",
                data={"episode_id": episode["id"], "artwork_type": artwork_type},
                files={"file": (f"{artwork_type}.png", image_bytes, "image/png")},
            )
            if resp.status_code == 200:
                uploaded_artwork += 1
            else:
                _log(
                    f"Artwork upload failed for {row['episode_id']} "
                    f"({artwork_type}): {resp.text}"
                )

        if row["status"] == "published":
            update_payload = {**create_payload, "status": "published"}
            resp = api.put(f"/episodes/{episode['id']}", json=update_payload)
            if resp.status_code != 200:
                errors = resp.json().get("detail", resp.text)
                publish_blocked.append(f"{row['episode_id']} ({row['episode_title']}): {errors}")

    # --- summary ---------------------------------------------------------
    _log("")
    _log("=" * 70)
    _log("Seed complete.")
    _log(f"  Shows created:    {created_shows}")
    _log(f"  Seasons created:  {created_seasons}")
    _log(f"  Episodes created: {created_episodes}")
    _log(f"  Artwork uploaded: {uploaded_artwork}")
    _log(f"  Admin login:  {ADMIN_USERNAME} / {ADMIN_PASSWORD}")
    _log(f"  Editor login: {EDITOR_USERNAME} / {EDITOR_PASSWORD}")

    if conflicts:
        _log("")
        _log(f"Data conflicts found in seed_shows.json ({len(conflicts)}), skipped:")
        for c in conflicts:
            _log(f"  - {c}")

    if publish_blocked:
        _log("")
        _log(
            f"Rows marked published in seed_shows.json but blocked by "
            f"publish validation ({len(publish_blocked)}), left as draft:"
        )
        for b in publish_blocked:
            _log(f"  - {b}")

    _log("")
    _log(
        "Note: every 'Rhyme Rangers' episode has section=null on its show "
        "and status=draft in the seed data - left as-is on purpose. "
        "Publishing one from the CMS will trigger the 'show missing a "
        "section' validation check."
    )
    _log("=" * 70)


if __name__ == "__main__":
    try:
        run()
    except requests.HTTPError as exc:
        _log(f"HTTP error: {exc} - {getattr(exc.response, 'text', '')}")
        sys.exit(1)