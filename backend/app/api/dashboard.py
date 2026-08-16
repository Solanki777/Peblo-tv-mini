from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.show import Show
from app.models.season import Season
from app.models.episode import Episode
from app.models.artwork import Artwork
from app.models.publish import PublishRun


router = APIRouter(
    prefix="/dashboard",
    tags=["Dashboard"],
)


@router.get("/")
def get_dashboard(
    db: Session = Depends(get_db),
):
    shows_count = db.query(Show).count()

    seasons_count = db.query(Season).count()

    episodes_count = db.query(Episode).count()

    artworks_count = db.query(Artwork).count()

    publish_runs_count = db.query(
        PublishRun
    ).count()

    recent_publish_runs = (
        db.query(PublishRun)
        .order_by(PublishRun.id.desc())
        .limit(5)
        .all()
    )

    return {
        "shows_count": shows_count,
        "seasons_count": seasons_count,
        "episodes_count": episodes_count,
        "artworks_count": artworks_count,
        "publish_runs_count": publish_runs_count,
        "recent_publish_runs": [
            {
                "id": run.id,
                "started_at": run.started_at,
                "completed_at": run.completed_at,
                "status": run.status,
                "shows_count": run.shows_count,
                "episodes_count": run.episodes_count,
                "error_message": run.error_message,
            }
            for run in recent_publish_runs
        ],
    }