
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import require_admin
from app.models.user import User
from app.services.validation import build_validation_report

router = APIRouter(prefix="/admin", tags=["Publishing"])


@router.get("/validation-report")
def get_validation_report(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Everything currently blocking a clean publish, grouped so an editor
    can act on it without an engineer's help. `issue_count == 0` is what the
    CMS publish button uses to decide whether to show "publish anyway,
    N items will be skipped" vs. "publish"."""
    report = build_validation_report(db)
    return report.to_public_dict()
