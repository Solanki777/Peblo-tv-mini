from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import require_editor
from app.models.user import User
from app.services.validation import build_validation_report

router = APIRouter(prefix="/admin", tags=["Publishing"])


@router.get("/validation-report")
def get_validation_report(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_editor),
):
    """Everything currently blocking a clean publish, grouped so an editor
    can act on it without an engineer's help.

    FIXED: this used to require an admin role. But the brief frames this
    endpoint explicitly as something an *editor* reads to fix problems
    themselves ("grouped so an editor can fix it without asking an
    engineer") - admin-only publishing makes sense (see require_admin on
    POST /admin/catalog/publish), admin-only *visibility into why publish
    is blocked* doesn't; it would force editors to ping an admin just to
    find out what's wrong, defeating the point of the report.
    """
    report = build_validation_report(db)
    return report.to_public_dict()