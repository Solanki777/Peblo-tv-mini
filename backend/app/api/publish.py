from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.config import CATALOG_KEY
from app.database import get_db
from app.deps import require_admin
from app.models.publish import PublishRun
from app.models.user import User
from app.schemas.publish import PublishResponse
from app.services.catalog import build_catalog
from app.services.storage import get_storage
from app.services.validation import build_validation_report

router = APIRouter(
    prefix="/admin/catalog",
    tags=["Publishing"],
)


@router.post("/publish", response_model=PublishResponse)
def publish(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Build the published catalogue and write it atomically to storage.

    - Only admins can publish (enforced via require_admin).
    - Validation runs first; anything that fails it (see
      services/validation.py) is excluded from the catalogue rather than
      blocking the whole run - the run is still recorded as completed, with
      issues_count > 0, so an editor can see what got left out and why via
      GET /admin/validation-report.
    - The catalogue is written with StorageBackend.write_bytes, which
      writes to a temp file and os.replace()s it into place - a reader can
      never observe a half-written file (see services/storage.py).
    - If the process dies before the replace happens, the previous
      catalog.json is untouched and still served correctly; the failed
      PublishRun is left with status="failed" so it's visible in history.
    """
    report = build_validation_report(db)
    catalog = build_catalog(db, report=report)

    run = PublishRun(
        started_at=datetime.now(timezone.utc),
        status="running",
        triggered_by=current_user.id,
    )
    db.add(run)
    db.commit()
    db.refresh(run)

    try:
        storage = get_storage()
        storage.write_json(CATALOG_KEY, catalog)

        run.status = "completed" if report.issue_count == 0 else "completed_with_issues"
        run.completed_at = datetime.now(timezone.utc)
        run.shows_count = catalog["counts"]["shows"]
        run.episodes_count = catalog["counts"]["episode_variants"]
        run.issues_count = report.issue_count
        run.catalog_key = CATALOG_KEY

        db.commit()
        db.refresh(run)

        return run

    except Exception as e:
        run.status = "failed"
        run.completed_at = datetime.now(timezone.utc)
        run.error_message = str(e)

        db.commit()
        db.refresh(run)

        return run


@router.get("/publish/runs", response_model=list[PublishResponse])
def list_publish_runs(db: Session = Depends(get_db)):
    return db.query(PublishRun).order_by(PublishRun.id.desc()).all()


@router.get("/publish/runs/{publish_id}", response_model=PublishResponse)
def get_publish_run(publish_id: int, db: Session = Depends(get_db)):
    run = db.query(PublishRun).filter(PublishRun.id == publish_id).first()

    if not run:
        raise HTTPException(status_code=404, detail="Publish run not found")

    return run
