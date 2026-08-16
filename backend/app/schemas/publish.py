from datetime import datetime

from pydantic import BaseModel


class PublishResponse(BaseModel):
    id: int
    started_at: datetime
    completed_at: datetime | None
    triggered_by: int | None
    status: str
    shows_count: int
    episodes_count: int
    error_message: str | None

    class Config:
        from_attributes = True