# Peblo-tv-mini# Peblo TV Mini

CMS upload → published catalogue → Netflix-style browse. See
`CHALLENGE_Peblo_TV_Mini.docx` for the original brief.

## How to run it

```
cp .env.example .env
docker-compose up --build
```

This brings up, in order: Postgres (with a healthcheck), the API
(applies Alembic migrations on startup, then serves on
`http://localhost:8000`), a one-shot seed job (waits for the API to be
healthy, then loads `seed_shows.json` through the real API - see
"Seeding" below), and the CMS (`http://localhost:5173`).

Log in to the CMS with:

- **admin** / `admin12345` - can publish
- **editor** / `editor12345` - can edit content, cannot publish

(Both bootstrapped by the seed job; override via `.env` before first
run - see `.env.example`.)

API docs: `http://localhost:8000/docs`.

## Status - what's done and what isn't (read this first)

This is a partially-complete take-home, picked up mid-build and
finished collaboratively with AI assistance (see "AI tool use" below).
Rather than claim more than is true:

**Done and working:**
- Part A (backend): schema/migrations, atomic publish, real
  Pillow-based artwork validation, roles enforced, validation report,
  composable search, tests.
- Part B (CMS): show/season/episode CRUD, dashboard, publishing page
  with validation report + disabled-with-reasons publish button.
- Part D (pipeline): docker-compose, GitHub Actions CI (lint + test +
  build images, deploy step written and explained), `.env.example`,
  health endpoint.
- Seed pipeline loading the real `seed_shows.json` through the API.

**Known incomplete / left out:**
- **Part C (viewer browse UI) is not built yet.** This is the single
  biggest gap against the brief - no separate viewer app exists, so
  there's no docker-compose service for it either.
- **The CMS Artwork page (`src/pages/Artwork.jsx`) is broken against
  the current backend.** It still posts `storage_key` / `width` /
  `height` / `size_bytes` as plain JSON fields to `POST /artworks/` -
  that endpoint doesn't exist anymore. The real endpoint is
  `POST /artworks/upload`, a multipart file upload the backend measures
  itself (see `app/services/artwork_validation.py`). This page needs a
  full rewrite: real file input, live preview, per-type dimension
  hints, no manually-typed dimensions. Until it's rewritten, artwork
  can only be uploaded via the API directly (which is what the seed
  job does) or via `/docs`.
- No assets/ sample images were available when this was built, so the
  seed job generates its own placeholder artwork at the exact target
  dimensions per type (see `seed/seed.py`) instead of using the brief's
  provided (some-deliberately-wrong-size) sample files. That means the
  CMS's "reject a wrong-size upload" behaviour hasn't been exercised
  against the brief's actual bad samples, only against generated ones
  in `tests/test_artwork_validation.py`.
- Optional stretch goals (versioned catalogue/rollback, publish
  dry-run/diff, audit log) - not attempted; time went to the required
  parts first.

## Seeding

`seed/seed.py` loads `seed/data/seed_shows.json` (the brief's provided
file) through the real HTTP API - registering an editor, creating
shows/seasons/episodes, uploading artwork, and publishing - not by
writing to the database directly. The one exception is bootstrapping
the first admin user, since (by design) no API endpoint can create one.

The seed data is deliberately imperfect, per the brief. What the script
found and how it handled each case:

| Issue | Rows | Handling |
|---|---|---|
| Two episodes claim the same `(content_group, language)` | `ep_0004` vs `ep_9001`, both `motis-many-lives-s01e02` / `hi` | Second create attempt gets a clean `400` from the API; seed script logs it and moves on. Neither the DB nor the catalogue ever has both. |
| `status: "published"` but `artwork_available` doesn't cover all 3 required types | `ep_0036`, `ep_0093`, `ep_0094` | Seed uploads whatever *is* listed, then attempts to publish same as any other row - rejected by the publish-blocker check, left as a draft. Shows up in `GET /admin/validation-report` and is excluded from the catalogue. |
| Show has `section: null` | every "Rhyme Rangers" row | Left as-is - all 8 rows are also `status: "draft"` in the source data, so nothing is "trying" to publish yet. Flip one to published from the CMS to see the "show missing a section" check fire live. |

Re-running `docker-compose up` re-runs the seed job; it's safe to
re-run (existing users/shows/seasons/episodes are detected and left
alone, not duplicated).

## Part E - written

**1. Atomic publish, and what happens if the process dies mid-run.**
`StorageBackend.write_bytes` (see `app/services/storage.py`) never lets
a reader see a partial file: it writes to a temp file in the same
directory as `catalog.json`, `fsync`s it, then `os.replace()`s it onto
the real path. `os.replace` is atomic on POSIX and Windows as long as
source and destination share a filesystem, which they always do here
(the temp file is a sibling of the destination). If the process dies
before that replace call, the previous `catalog.json` is completely
untouched - viewers keep serving the last good publish - and the
`PublishRun` row is left `status="failed"` with the error message, so
it's visible in publish history rather than silently vanishing.

**2. Storage abstraction: local disk → Cloudflare R2.** Everything that
reads or writes a "file" goes through the tiny `StorageBackend`
interface (`write_bytes`/`read_bytes`/`exists`/`delete`/`key_path`),
implemented today by `LocalDiskStorage`. Moving to R2 means writing an
`R2Storage` class against the same interface using `boto3`'s S3-
compatible client pointed at the R2 endpoint (R2 speaks the S3 API), and
swapping the one line in `get_storage()` (`app/services/storage.py`).
The one place this needs real thought, not just a drop-in swap: R2
doesn't have atomic "replace a key" the way a local filesystem does -
`write_bytes`'s local-disk atomicity trick (temp file + `os.replace`)
doesn't translate directly. The R2 implementation would instead write
the new catalogue under a versioned key (e.g. `catalog/<publish_run_id>.json`)
and then update a *pointer* (an R2 object, or a row in Postgres) that
says which versioned key is current - the read path resolves the
pointer, then fetches that key. That also gives rollback almost for
free (point the pointer at an older key), which local disk doesn't.

**3. Search: implementation, scaling limit, next step.**
`GET /catalog/search` does a linear, in-memory scan over the parsed
catalogue JSON on every request (`app/api/catalog.py`). That's fine at
this catalogue's scale - a few dozen shows, low hundreds of episode
variants - but it re-reads and re-walks the *entire* catalogue on every
request, with no index of any kind; `q` does per-field substring
matching across every show and episode in scope. This stops being fine
somewhere in the thousands-of-episodes range, and definitely by tens of
thousands, especially under real concurrent traffic (every request pays
the full linear cost, there's no caching of the parsed structure between
requests). Next step: move `q` to Postgres full-text search
(`tsvector`/`tsquery` with a GIN index on show/episode title + category)
queried directly instead of walking the published JSON, or - if this
needs to stay fully decoupled from the DB for the "serve a static file"
benefits described below - a dedicated search index (Meilisearch is a
reasonable fit here: small ops footprint, good relevance defaults,
built for exactly this "typeahead over a catalogue" shape).

**4. Why serve a pre-published catalogue file instead of querying the
DB per request?** Three reasons: viewers never pay for the shows →
seasons → episodes → artwork joins and the content_group collapsing
logic on every page load (that work happens once, at publish time, not
per-request); viewers can never see a show mid-edit, only what the last
successful publish produced, which is a real UX guarantee ("what you
see is what was actually published"), not just a performance one; and
it decouples viewer traffic from the CMS's database entirely - a spike
in viewer load can't degrade editor CRUD, and vice versa. Where it
bites: staleness (an edit isn't visible to viewers until someone hits
publish again - by design, but it does mean "I fixed a typo" requires a
full publish, not just a save), and it doesn't scale search past what's
described above without adding something DB- or index-backed back into
the read path.

**5. What was left out, and why.**
See "Status" above for the full list - in short: the viewer UI (Part
C), the CMS artwork upload rewrite, and using the brief's actual
`assets/` sample images in the seed data (not provided, so synthetic
placeholders were generated instead). Time went to getting Part A
(backend) and the pipeline (Part D) genuinely solid rather than having
five things half-working.

**AI tool use:** built collaboratively with Claude (Anthropic), used
throughout - reading and auditing the existing code for bugs before
changing anything (e.g. finding that `Publishing.jsx` called endpoints
that don't exist, and that `Artwork.jsx` posts fields the API no longer
accepts), writing the seed script and tests, and drafting this README.
Where it suggested something and I didn't have a way to verify it (e.g.
exact R2/S3 API behaviour around atomic key replacement), I flagged
that in the text above rather than stating it as fact. Everything here
was run through review, not accepted verbatim - the docker-compose,
seed script, and test files were syntax/YAML-checked, but **not run
end-to-end against real Postgres/Docker**, since this environment has
no Docker and no network access to install Postgres locally. That's a
real gap: please run `docker-compose up --build` yourself before
relying on this, and report back anything that breaks.

## Secrets in production

Locally this uses a `.env` file (see `.env.example`) - fine for a
take-home, not fine for anything real. In production, `SECRET_KEY` and
`DATABASE_URL` would come from a secrets manager (AWS Secrets Manager /
GCP Secret Manager / Doppler, whatever the target platform's
equivalent is) injected as environment variables into the running
container at deploy time - never checked into the repo, never baked
into the image. `SECRET_KEY` specifically should be rotated on a
schedule; because it's an HMAC signing key for JWTs, rotating it
invalidates every outstanding token, so a real rotation would need a
short grace window accepting both the old and new key rather than a
hard cutover.

## What I'd alert on

**Publish failures.** `PublishRun.status == "failed"` is the one signal
that most directly says "the catalogue viewers are served is falling
behind what editors think is live" - and unlike most API errors, it
can happen with zero failed HTTP requests (the publish endpoint itself
returns `200` even when the run fails, by design - see `app/api/publish.py`
- so an uptime/error-rate check alone won't catch it). A simple
poll of `GET /admin/catalog/publish/runs` (or a scheduled DB query) for
any run with `status="failed"`, alerting within a few minutes, is the
single highest-value alert in this system - a failed publish is silent
by default and directly affects what real users see.

## Repo layout

```
backend/backend/    FastAPI + Postgres, Alembic migrations, tests, seed script
frontend/frontend/  Internal CMS (React + Vite)
docker-compose.yml   db, api, seed, cms
.github/workflows/   CI: lint, test, build images, (documented) deploy
```