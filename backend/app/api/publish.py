from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.publish import PublishRun
from app.models.show import Show
from app.models.episode import Episode
from app.schemas.publish import PublishResponse


router = APIRouter(
    prefix="/publish",
    tags=["Publishing"],
)


@router.post("/", response_model=PublishResponse)
def publish(db: Session = Depends(get_db)):
    run = PublishRun(
        started_at=datetime.utcnow(),
        status="running",
    )

    db.add(run)
    db.commit()
    db.refresh(run)

    try:
        shows_count = db.query(func.count(Show.id)).scalar() or 0
        episodes_count = db.query(func.count(Episode.id)).scalar() or 0

        run.shows_count = shows_count
        run.episodes_count = episodes_count
        run.status = "completed"
        run.completed_at = datetime.utcnow()

        db.commit()
        db.refresh(run)

        return run

    except Exception as e:
        run.status = "failed"
        run.completed_at = datetime.utcnow()
        run.error_message = str(e)

        db.commit()
        db.refresh(run)

        return run


@router.get("/", response_model=list[PublishResponse])
def list_publish_runs(db: Session = Depends(get_db)):
    return (
        db.query(PublishRun)
        .order_by(PublishRun.id.desc())
        .all()
    )


@router.get("/{publish_id}", response_model=PublishResponse)
def get_publish_run(
    publish_id: int,
    db: Session = Depends(get_db),
):
    run = (
        db.query(PublishRun)
        .filter(PublishRun.id == publish_id)
        .first()
    )

    if not run:
        from fastapi import HTTPException

        raise HTTPException(
            status_code=404,
            detail="Publish run not found",
        )

    return run